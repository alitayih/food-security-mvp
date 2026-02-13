from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

SHOCK_FACTORS = {
    "currency_depreciation": {"inflation": 0.35, "food_price_stress": 0.25, "currency_pressure": 0.6},
    "commodity_price_spike": {"food_price_stress": 0.7, "inflation": 0.2},
    "conflict_spike": {"conflict_events": 0.8, "undernourishment": 0.25, "food_price_stress": 0.2},
}


def simulate(rows: list[dict], shock_type: str, severity: float, horizon: int) -> list[dict]:
    factors = SHOCK_FACTORS.get(shock_type, {})
    adjusted = []
    for r in rows:
        bump = factors.get(r["indicator_id"], 0.0) * (severity / 100.0) * (horizon / 12)
        adjusted.append({**r, "value": round(float(r["value"]) * (1 + bump), 2)})
    return adjusted


def record_scenario(conn: sqlite3.Connection, country_iso3: str, shock_type: str, severity: float, horizon: int) -> int:
    cur = conn.execute(
        "INSERT INTO scenarios(country_iso3, shock_type, severity, horizon, created_at) VALUES (?,?,?,?,?)",
        (country_iso3, shock_type, severity, horizon, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return int(cur.lastrowid)
