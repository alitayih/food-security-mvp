from __future__ import annotations

import csv
from datetime import datetime, timezone

from .cache import fetch_with_cache


def fetch_food_source(country_iso3: str, ttl_seconds: int = 60 * 60 * 24) -> list[dict]:
    url = "https://ourworldindata.org/grapher/prevalence-of-undernourishment.csv"
    text = fetch_with_cache(url, as_json=False, timeout=30, ttl_seconds=ttl_seconds)
    reader = csv.DictReader(text.splitlines())
    now = datetime.now(timezone.utc).isoformat()
    rows: list[dict] = []
    for row in reader:
        if row.get("Code") != country_iso3:
            continue
        val = row.get("Prevalence of undernourishment (% of population)")
        year = row.get("Year")
        if not val or not year:
            continue
        rows.append(
            {
                "country_iso3": country_iso3,
                "date": f"{year}-01-01",
                "indicator_id": "undernourishment",
                "value": float(val),
                "unit": "%",
                "source": "Our World in Data",
                "last_updated": now,
            }
        )
    return rows
