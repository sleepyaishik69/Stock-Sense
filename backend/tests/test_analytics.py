from decimal import Decimal
from app.analytics import calculate_sales, period_growth


def row(qty, price, cost, tid="T1", discount=0, returned=False):
    return {"quantity": qty, "unit_price": Decimal(str(price)), "unit_cost": None if cost is None else Decimal(str(cost)), "discount": Decimal(str(discount)), "transaction_id": tid, "is_return": returned}


def test_revenue_discount_cost_and_margin():
    result = calculate_sales([row(2, 100, 60, "A", 10), row(1, 50, 20, "B")])
    assert result["gross_sales"] == Decimal("250.00")
    assert result["discounts"] == Decimal("10.00")
    assert result["net_sales"] == Decimal("240.00")
    assert result["gross_units"] == 3
    assert result["cogs"] == Decimal("140.00")
    assert result["gross_profit"] == Decimal("100.00")
    assert result["gross_margin_pct"] == Decimal("41.67")
    assert result["transactions"] == 2


def test_returns_reduce_revenue_units_and_cost():
    result = calculate_sales([row(3, 20, 8, "sale"), row(1, 20, 8, "return", returned=True)])
    assert result["net_sales"] == Decimal("40.00")
    assert result["net_units"] == 2
    assert result["cogs"] == Decimal("16.00")
    assert result["gross_profit"] == Decimal("24.00")


def test_missing_cost_disables_profit_instead_of_guessing():
    result = calculate_sales([row(1, 99, None)])
    assert result["net_sales"] == Decimal("99.00")
    assert result["gross_profit"] is None
    assert result["gross_margin_pct"] is None


def test_zero_net_sales_has_no_margin():
    result = calculate_sales([row(1, 10, 4), row(1, 10, 4, "R", returned=True)])
    assert result["net_sales"] == Decimal("0.00")
    assert result["gross_margin_pct"] is None


def test_return_only_negative_sales_uses_signed_profit_and_margin():
    result = calculate_sales([row(1, 10, 4, "R", returned=True)])
    assert result["gross_units"] == 0
    assert result["net_units"] == -1
    assert result["net_sales"] == Decimal("-10.00")
    assert result["gross_profit"] == Decimal("-6.00")
    assert result["gross_margin_pct"] == Decimal("60.00")


def test_period_growth_uses_absolute_prior_denominator_and_guards_zero():
    assert period_growth(Decimal("110"), Decimal("100")) == Decimal("10.00")
    assert period_growth(Decimal("90"), Decimal("100")) == Decimal("-10.00")
    assert period_growth(Decimal("0"), Decimal("-50")) == Decimal("100.00")
    assert period_growth(Decimal("20"), Decimal("0")) is None
