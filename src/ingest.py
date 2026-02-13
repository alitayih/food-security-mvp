from __future__ import annotations

import os
from datetime import datetime, timezone

from .db import record_ingestion_run, upsert_meta, upsert_values
from .sources_conflict import load_demo_data
from .sources_food import fetch_food_source
from .sources_worldbank import fetch_world_bank


def ingest_country(conn, country_iso3: str, demo_mode: bool = False, ttl_hours: int = 24) -> str:
    force_demo = os.getenv("DEMO_MODE", "0") == "1"
    meta, demo_values = load_demo_data()
    upsert_meta(conn, meta)

    if demo_mode or force_demo:
        upsert_values(conn, [v for v in demo_values if v["country_iso3"] == country_iso3])
        mode = "demo"
        record_ingestion_run(conn, country_iso3, mode, datetime.now(timezone.utc).isoformat())
        return mode

    seed_demo = [
        v
        for v in demo_values
        if v["country_iso3"] == country_iso3
        and v["indicator_id"] in {"food_price_stress", "currency_pressure", "conflict_events"}
    ]
    try:
        ttl_seconds = max(1, ttl_hours) * 3600
        live_rows = []
        live_rows.extend(fetch_world_bank(country_iso3, ttl_seconds=ttl_seconds))
        live_rows.extend(fetch_food_source(country_iso3, ttl_seconds=ttl_seconds))
        values = seed_demo + live_rows
        if not values:
            raise RuntimeError("No live values")
        upsert_values(conn, values)
        mode = "live"
    except Exception:
        upsert_values(conn, [v for v in demo_values if v["country_iso3"] == country_iso3])
        mode = "fallback_demo"

    record_ingestion_run(conn, country_iso3, mode, datetime.now(timezone.utc).isoformat())
    return mode
