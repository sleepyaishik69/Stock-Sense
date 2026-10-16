from collections import Counter


def association_rules(baskets: list[set[int]], product_names: dict[int, str], min_transactions: int = 2) -> list[dict]:
    """Compute directional support, confidence and lift from distinct-item baskets."""
    baskets = [b for b in baskets if b]
    total = len(baskets)
    if not total:
        return []
    singles: Counter[int] = Counter()
    pairs: Counter[tuple[int, int]] = Counter()
    for basket in baskets:
        singles.update(basket)
        for a in basket:
            for b in basket:
                if a < b:
                    pairs[(a, b)] += 1
    results = []
    for (a, b), count in pairs.items():
        if count < min_transactions or not singles[a] or not singles[b]:
            continue
        support = count / total
        for left, right in ((a, b), (b, a)):
            confidence = count / singles[left]
            consequent_probability = singles[right] / total
            lift = confidence / consequent_probability if consequent_probability else 0
            results.append({"product": product_names.get(left, str(left)), "often_with": product_names.get(right, str(right)), "support": round(support, 4), "confidence": round(confidence, 4), "lift": round(lift, 4), "transactions": count})
    return sorted(results, key=lambda x: (x["lift"], x["transactions"], x["confidence"]), reverse=True)
