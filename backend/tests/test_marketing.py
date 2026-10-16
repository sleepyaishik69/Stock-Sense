from app.marketing import association_rules


def test_association_rules_report_support_confidence_lift():
    rules=association_rules([{1,2},{1,2},{1,2},{3}],{1:"Tea",2:"Biscuits",3:"Milk"})
    rule=next(r for r in rules if r["product"]=="Tea" and r["often_with"]=="Biscuits")
    assert rule["transactions"]==3
    assert rule["support"]==0.75
    assert rule["confidence"]==1.0
    assert rule["lift"]==1.3333


def test_single_basket_does_not_create_weak_bundling_claim():
    assert association_rules([{1,2}],{1:"Tea",2:"Biscuits"})==[]
