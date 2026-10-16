"""Build compact, workspace-scoped evidence for natural-language analysis."""

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .marketing import association_rules
from .models import Product, Sale, Store


def build_chat_context(db: Session, workspace_id: int, store_id: int | None, facts: dict) -> dict:
    """Summarize every sale in scope before passing evidence to the language model."""
    period_start = date.fromisoformat(facts["period"]["start"])
    period_end = date.fromisoformat(facts["period"]["end"])
    previous = facts["comparison"]["previous_period"]
    previous_start = date.fromisoformat(previous["start"])
    previous_end = date.fromisoformat(previous["end"])

    product_query = select(Product).where(
        Product.workspace_id == workspace_id,
        Product.archived.is_(False),
    )
    current_sales_query = select(Sale).where(
        Sale.workspace_id == workspace_id,
        Sale.sale_date >= period_start,
        Sale.sale_date <= period_end,
    )
    previous_sales_query = select(Sale).where(
        Sale.workspace_id == workspace_id,
        Sale.sale_date >= previous_start,
        Sale.sale_date <= previous_end,
    )
    if store_id is not None:
        product_query = product_query.where(Product.store_id == store_id)
        current_sales_query = current_sales_query.where(Sale.store_id == store_id)
        previous_sales_query = previous_sales_query.where(Sale.store_id == store_id)

    catalog = db.scalars(product_query).all()
    current_sales = db.scalars(current_sales_query).all()
    previous_sales = db.scalars(previous_sales_query).all()
    store = db.get(Store, store_id) if store_id is not None else None

    by_sku = {product.sku: product for product in catalog}
    by_id = {product.id: product for product in catalog}
    product_names = {product.id: product.name for product in catalog}
    product_facts = facts["products"]
    top_by_units = sorted(product_facts, key=lambda product: product["units"], reverse=True)
    top_by_sales = sorted(product_facts, key=lambda product: product["net_sales"], reverse=True)
    top_by_profit = sorted(
        (product for product in product_facts if product["gross_profit"] is not None),
        key=lambda product: product["gross_profit"],
        reverse=True,
    )

    category_totals: dict[str, dict] = defaultdict(
        lambda: {"units": 0, "net_sales": 0, "gross_profit": 0, "costs_complete": True, "products": 0}
    )
    for product in product_facts:
        total = category_totals[product["category"]]
        total["units"] += int(product["units"])
        total["net_sales"] += product["net_sales"]
        total["products"] += 1
        if product["gross_profit"] is None:
            total["costs_complete"] = False
        else:
            total["gross_profit"] += product["gross_profit"]
    categories = []
    for category, total in category_totals.items():
        categories.append({
            "category": category,
            "products": total["products"],
            "net_units": total["units"],
            "net_sales": total["net_sales"],
            "gross_profit": total["gross_profit"] if total["costs_complete"] else None,
        })
    categories.sort(key=lambda category: category["net_sales"], reverse=True)

    previous_units: dict[str, int] = defaultdict(int)
    for sale in previous_sales:
        product = by_id.get(sale.product_id)
        if product:
            previous_units[product.sku] += -sale.quantity if sale.is_return else sale.quantity
    changes = []
    for item in product_facts:
        product = by_sku.get(item["sku"])
        if not product:
            continue
        prior_units = previous_units.get(item["sku"], 0)
        delta = int(item["units"]) - prior_units
        changes.append({"sku": item["sku"], "name": item["name"], "units_now": int(item["units"]), "units_previous": prior_units, "change_units": delta})
    changes.sort(key=lambda item: item["change_units"], reverse=True)
    selected_changes = []
    seen_skus = set()
    for item in changes[:5] + sorted(changes, key=lambda item: item["change_units"])[:5]:
        if item["sku"] not in seen_skus:
            selected_changes.append(item)
            seen_skus.add(item["sku"])

    trend: dict[str, dict] = defaultdict(lambda: {"net_sales": 0, "gross_profit": 0, "gross_profit_complete": True})
    trend_grain = "week"
    if (period_end - period_start).days > 112:
        trend_grain = "month"
    for day in facts["trend"]:
        sale_day = date.fromisoformat(day["date"])
        if trend_grain == "month":
            period_key = sale_day.strftime("%Y-%m")
        else:
            period_key = (sale_day - timedelta(days=sale_day.weekday())).isoformat()
        bucket = trend[period_key]
        bucket["net_sales"] += day["revenue"]
        if day["gross_profit"] is None:
            bucket["gross_profit_complete"] = False
        else:
            bucket["gross_profit"] += day["gross_profit"]
    trend_series = [
        {"period": key, "net_sales": value["net_sales"], "gross_profit": value["gross_profit"] if value["gross_profit_complete"] else None}
        for key, value in sorted(trend.items())
    ]

    baskets: dict[tuple[int, date, str], set[int]] = defaultdict(set)
    for sale in current_sales:
        if not sale.is_return:
            baskets[(sale.store_id, sale.sale_date, sale.transaction_id)].add(sale.product_id)
    basket_patterns = association_rules(list(baskets.values()), product_names)[:8]

    def brief(item: dict) -> dict:
        return {
            "sku": item["sku"],
            "name": item["name"],
            "category": item["category"],
            "net_units": int(item["units"]),
            "net_sales": item["net_sales"],
            "gross_profit": item["gross_profit"],
            "gross_margin_pct": item["gross_margin_pct"],
        }

    return {
        "scope": {
            "period": facts["period"],
            "store": store.name if store else "All stores",
            "sales_lines_analyzed": len(current_sales),
            "transactions_analyzed": facts["metrics"]["transactions"],
            "active_products_in_scope": len(catalog),
        },
        "performance": {
            "current_period": facts["metrics"],
            "previous_equal_length_period": facts["comparison"],
            "trend_grain": trend_grain,
            "sales_trend": trend_series,
        },
        "products": {
            "top_by_net_units": [brief(item) for item in top_by_units[:8]],
            "top_by_net_sales": [brief(item) for item in top_by_sales[:8]],
            "top_by_gross_profit": [brief(item) for item in top_by_profit[:8]],
            "unit_change_vs_previous_period": selected_changes,
        },
        "categories_by_net_sales": categories[:10],
        "inventory_signals": {
            "low_stock": facts["low_stock"][:10],
            "reorder_suggestions": facts["reorder_suggestions"][:10],
        },
        "basket_patterns": {
            "transactions_with_basket_ids": len(baskets),
            "frequent_pairs": basket_patterns,
        },
        "data_gaps": [
            "Promotion identifiers, historical prices, customer segments, and campaign outcomes are not recorded; price elasticity and promotion lift cannot be established.",
            "Stock is a current snapshot, not a historical inventory ledger.",
            *facts["limitations"],
        ],
    }
