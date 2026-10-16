from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Product, Sale

ZERO = Decimal("0.00")


def money(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def period_growth(current: Decimal | None, prior: Decimal | None) -> Decimal | None:
    if current is None or prior is None or prior == 0:
        return None
    return ((current - prior) / abs(prior) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_sales(rows: list[dict]) -> dict:
    gross_sales = ZERO
    discounts = ZERO
    refunds = ZERO
    cogs = ZERO
    gross_units = 0
    net_units = 0
    transactions: set[str] = set()
    costs_complete = True
    for r in rows:
        q = int(r["quantity"])
        amount = money(Decimal(q) * money(r["unit_price"]))
        discount = money(r.get("discount", 0))
        if r.get("is_return"):
            refunds += max(ZERO, amount - discount)
            net_units -= q
            if r.get("unit_cost") is None:
                costs_complete = False
            else:
                cogs -= money(Decimal(q) * money(r["unit_cost"]))
        else:
            gross_units += q
            gross_sales += amount
            discounts += discount
            net_units += q
            if r.get("unit_cost") is None:
                costs_complete = False
            else:
                cogs += money(Decimal(q) * money(r["unit_cost"]))
            transactions.add(str(r["transaction_id"]))
    net_sales = money(gross_sales - discounts - refunds)
    gross_profit = money(net_sales - cogs) if costs_complete else None
    margin = (gross_profit / net_sales * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if gross_profit is not None and net_sales else None
    atv = (net_sales / len(transactions)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if transactions else None
    return {"gross_units": gross_units, "net_units": net_units, "gross_sales": gross_sales, "discounts": discounts, "refunds": refunds, "net_sales": net_sales, "cogs": cogs if costs_complete else None, "gross_profit": gross_profit, "gross_margin_pct": margin, "transactions": len(transactions), "average_transaction_value": atv, "costs_complete": costs_complete}


def overview(db: Session, workspace_id: int, store_id: int | None = None, start: date | None = None, end: date | None = None) -> dict:
    today = date.today()
    end = end or today
    start = start or end - timedelta(days=29)
    stmt = select(Sale).where(Sale.workspace_id == workspace_id, Sale.sale_date >= start, Sale.sale_date <= end)
    if store_id:
        stmt = stmt.where(Sale.store_id == store_id)
    sales = db.scalars(stmt).all()
    product_stmt = select(Product).where(Product.workspace_id == workspace_id, Product.archived.is_(False))
    if store_id:
        product_stmt = product_stmt.where(Product.store_id == store_id)
    products = db.scalars(product_stmt).all()
    metrics = calculate_sales([{"quantity": s.quantity, "unit_price": s.unit_price, "discount": s.discount, "unit_cost": s.unit_cost, "transaction_id": f"{s.store_id}:{s.transaction_id}", "is_return": s.is_return} for s in sales])
    period_days = max((end - start).days + 1, 1)
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_days - 1)
    previous_stmt = select(Sale).where(Sale.workspace_id == workspace_id, Sale.sale_date >= previous_start, Sale.sale_date <= previous_end)
    if store_id: previous_stmt = previous_stmt.where(Sale.store_id == store_id)
    previous_sales = db.scalars(previous_stmt).all()
    prior_metrics = calculate_sales([{"quantity": s.quantity, "unit_price": s.unit_price, "discount": s.discount, "unit_cost": s.unit_cost, "transaction_id": f"{s.store_id}:{s.transaction_id}", "is_return": s.is_return} for s in previous_sales])
    comparison = {"previous_period": {"start":previous_start.isoformat(),"end":previous_end.isoformat()}, "net_sales_growth_pct":period_growth(metrics["net_sales"],prior_metrics["net_sales"]), "gross_profit_growth_pct":period_growth(metrics["gross_profit"],prior_metrics["gross_profit"]), "previous_net_sales":prior_metrics["net_sales"], "previous_gross_profit":prior_metrics["gross_profit"]}
    grouped = defaultdict(lambda: {"units": 0, "sales": ZERO, "discounts": ZERO, "refunds": ZERO, "cogs": ZERO, "cost_complete": True, "category": "Uncategorized"})
    by_day = defaultdict(lambda: {"revenue": ZERO, "gross_profit": ZERO, "has_cost": True})
    lookup = {p.id: p for p in products}
    for sale in sales:
        p = lookup.get(sale.product_id)
        if not p:
            continue
        g = grouped[p.id]
        g["category"] = p.category
        amt = money(Decimal(sale.quantity) * money(sale.unit_price))
        cost = money(Decimal(sale.quantity) * money(sale.unit_cost)) if sale.unit_cost is not None else None
        if sale.is_return:
            g["units"] -= sale.quantity
            g["refunds"] += money(amt - money(sale.discount))
            if cost is None: g["cost_complete"] = False
            else: g["cogs"] -= cost
            by_day[sale.sale_date.isoformat()]["revenue"] -= money(amt - money(sale.discount))
            by_day[sale.sale_date.isoformat()]["gross_profit"] -= money(amt - money(sale.discount) - cost) if cost is not None else ZERO
            if cost is None: by_day[sale.sale_date.isoformat()]["has_cost"] = False
        else:
            g["units"] += sale.quantity
            g["sales"] += amt
            g["discounts"] += money(sale.discount)
            if cost is None: g["cost_complete"] = False
            else: g["cogs"] += cost
            by_day[sale.sale_date.isoformat()]["revenue"] += money(amt - money(sale.discount))
            if cost is not None: by_day[sale.sale_date.isoformat()]["gross_profit"] += money(amt - money(sale.discount) - cost)
            else: by_day[sale.sale_date.isoformat()]["has_cost"] = False
    rankings = []
    for p in products:
        g = grouped[p.id]
        revenue = money(g["sales"] - g["discounts"] - g["refunds"])
        profit = money(revenue - g["cogs"]) if g["cost_complete"] and g["units"] else (ZERO if g["cost_complete"] else None)
        rankings.append({"sku": p.sku, "name": p.name, "category": p.category, "units": g["units"], "net_sales": revenue, "gross_profit": profit, "gross_margin_pct": (profit / revenue * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if profit is not None and revenue else None})
    ranked_sales = sorted(rankings, key=lambda x: x["net_sales"], reverse=True)[:6]
    ranked_profit = sorted((x for x in rankings if x["gross_profit"] is not None), key=lambda x: x["gross_profit"], reverse=True)[:6]
    low_stock = [p for p in products if p.stock_on_hand is not None and p.stock_on_hand <= p.reorder_threshold]
    movers = []
    days = max((end - start).days + 1, 1)
    for p in products:
        units = grouped[p.id]["units"]
        if p.stock_on_hand is not None and units > 0:
            daily = Decimal(units) / Decimal(days)
            movers.append({"sku": p.sku, "name": p.name, "stock": p.stock_on_hand, "daily_demand": round(float(daily), 2), "days_remaining": round(float(Decimal(p.stock_on_hand) / daily), 1) if daily else None, "suggested_reorder": max(0, int((daily * Decimal(p.lead_time_days or 7) + p.reorder_threshold).to_integral_value(rounding=ROUND_CEILING)) - p.stock_on_hand), "lead_time_days": p.lead_time_days or 7, "assumption": f"Recent {days}-day average demand; safety stock uses the configured threshold; no confirmed purchase orders are modeled."})
    for p in products:
        if p.stock_on_hand is not None and grouped[p.id]["units"] == 0:
            movers.append({"sku": p.sku, "name": p.name, "stock": p.stock_on_hand, "daily_demand": None, "days_remaining": None, "suggested_reorder": 0, "lead_time_days": p.lead_time_days or 7, "assumption": "No sales in the selected period; no reorder quantity is inferred."})
    inv_cost = sum((money(p.unit_cost) * p.stock_on_hand for p in products if p.unit_cost is not None and p.stock_on_hand is not None), ZERO)
    reorder_suggestions = sorted(movers, key=lambda x: (x["days_remaining"] if x["days_remaining"] is not None else 100000))
    action_center = []
    for product in products:
        if product.stock_on_hand is None:
            action_center.append({"type": "count_stock", "priority": "medium", "sku": product.sku, "product": product.name, "title": f"Count stock for {product.name}", "detail": "On-hand quantity is unknown, so a safe reorder estimate cannot be made.", "action": "Record a shelf count"})
    for item in reorder_suggestions:
        if item["days_remaining"] is not None and item["days_remaining"] <= item["lead_time_days"]:
            action_center.append({"type": "stockout_risk", "priority": "high", "sku": item["sku"], "product": item["name"], "title": f"Review {item['name']} today", "detail": f"About {item['days_remaining']} days of stock remain against a {item['lead_time_days']}-day lead time.", "action": f"Review a suggested {item['suggested_reorder']}-unit reorder"})
        elif item["suggested_reorder"] > 0:
            action_center.append({"type": "reorder", "priority": "medium", "sku": item["sku"], "product": item["name"], "title": f"Plan a reorder for {item['name']}", "detail": f"Recent demand averages {item['daily_demand']} units per day; {item['days_remaining']} days of stock remain.", "action": f"Review a suggested {item['suggested_reorder']}-unit reorder"})
    missing_costs = [p for p in products if p.unit_cost is None]
    if missing_costs:
        action_center.append({"type": "complete_costs", "priority": "low", "sku": None, "product": None, "title": "Complete product costs", "detail": f"{len(missing_costs)} active products have no unit cost, limiting inventory valuation and budget-based reorder estimates. Gross profit still needs cost on each sale line.", "action": "Add product costs; include sale-line costs on future imports"})
    priority_order = {"high": 0, "medium": 1, "low": 2}
    action_center.sort(key=lambda action: priority_order[action["priority"]])
    return {"period": {"start": start.isoformat(), "end": end.isoformat(), "days": days}, "comparison":comparison, "definitions": {"net_sales": "Gross sales minus recorded line discounts and returns; tax is excluded.", "gross_profit": "Net sales less COGS, only when every relevant sale has a known unit cost.", "gross_margin_pct": "Gross profit divided by net sales × 100.", "inventory_cost_value": "Current on-hand units × current unit cost; a current-cost estimate, not historical valuation."}, "metrics": metrics, "inventory_cost_value": inv_cost, "products": rankings, "top_products_by_sales": ranked_sales, "top_products_by_profit": ranked_profit, "low_stock": [{"sku": p.sku, "name": p.name, "stock": p.stock_on_hand, "threshold": p.reorder_threshold} for p in low_stock], "reorder_suggestions": reorder_suggestions, "action_center": action_center[:20], "trend": [{"date": d, "revenue": val["revenue"], "gross_profit": val["gross_profit"] if val["has_cost"] else None} for d, val in sorted(by_day.items())], "limitations": ["Taxes are excluded from net sales.", "Gross profit and margin are unavailable where cost data is incomplete.", "Inventory value uses current costs and is not a historical inventory valuation.", "Reorder estimates use a simple selected-period daily average, configured lead time and reorder threshold; seasonality and confirmed incoming orders are not modeled."]}
