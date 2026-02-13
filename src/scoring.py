from __future__ import annotations

from collections import defaultdict

CATEGORY_WEIGHTS = {"food": 0.4, "conflict": 0.35, "macro": 0.25}
INDICATOR_CATEGORY = {
    "inflation": "macro",
    "gdp_growth": "macro",
    "unemployment": "macro",
    "undernourishment": "food",
    "food_price_stress": "food",
    "conflict_events": "conflict",
    "currency_pressure": "macro",
}
INVERT_FOR_RISK = {"gdp_growth"}


def _minmax(value: float, min_value: float, max_value: float, invert: bool = False) -> float:
    if max_value <= min_value:
        score = 50.0
    else:
        score = (value - min_value) / (max_value - min_value) * 100
    score = max(0.0, min(100.0, score))
    return 100.0 - score if invert else score


def compute_scores(window_rows: list[dict], latest_rows: list[dict]) -> dict:
    by_indicator: dict[str, list[float]] = defaultdict(list)
    for row in window_rows:
        by_indicator[row["indicator_id"]].append(float(row["value"]))

    indicator_scores: dict[str, float] = {}
    normalized_inputs: dict[str, float] = {}
    category_buckets: dict[str, list[float]] = defaultdict(list)

    for row in latest_rows:
        iid = row["indicator_id"]
        value = float(row["value"])
        values = by_indicator.get(iid, [value])
        norm = _minmax(value, min(values), max(values), invert=iid in INVERT_FOR_RISK)
        category = row["category"]
        indicator_scores[iid] = norm
        normalized_inputs[iid] = round(norm, 2)
        category_buckets[category].append(norm)

    category_scores = {k: round(sum(v) / len(v), 2) if v else 0.0 for k, v in category_buckets.items()}
    overall = 0.0
    for cat, weight in CATEGORY_WEIGHTS.items():
        overall += category_scores.get(cat, 0.0) * weight

    contributors = sorted(indicator_scores.items(), key=lambda x: x[1], reverse=True)
    return {
        "overall_risk": round(overall, 2),
        "category_scores": category_scores,
        "weights": CATEGORY_WEIGHTS,
        "normalized_inputs": normalized_inputs,
        "contributors": [(k, round(v, 2)) for k, v in contributors],
    }
