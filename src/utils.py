from __future__ import annotations


def clamp(v: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, v))


def to_risk_scale(value: float, min_v: float, max_v: float, invert: bool = False) -> float:
    if max_v == min_v:
        return 50.0
    scaled = (value - min_v) / (max_v - min_v) * 100
    scaled = clamp(scaled)
    return 100 - scaled if invert else scaled


def deterministic_summary(country: str, risk: float, top_contributors: list[str], alert_count: int) -> str:
    posture = "high" if risk >= 70 else "moderate" if risk >= 40 else "low"
    drivers = ", ".join(top_contributors[:3]) if top_contributors else "stable indicators"
    return (
        f"{country} shows a {posture} risk posture (score {risk:.1f}/100). "
        f"Primary contributors are {drivers}. "
        f"Triggered alerts in this view: {alert_count}."
    )
