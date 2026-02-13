from __future__ import annotations

from datetime import datetime, timezone

from .cache import fetch_with_cache

WB_INDICATORS = {
    "inflation": ("FP.CPI.TOTL.ZG", "%"),
    "gdp_growth": ("NY.GDP.MKTP.KD.ZG", "%"),
    "unemployment": ("SL.UEM.TOTL.ZS", "%"),
}


def fetch_world_bank(country_iso3: str, ttl_seconds: int = 60 * 60 * 24) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    rows: list[dict] = []
    for indicator_id, (code, unit) in WB_INDICATORS.items():
        url = f"https://api.worldbank.org/v2/country/{country_iso3}/indicator/{code}?format=json&per_page=80"
        payload = fetch_with_cache(url, as_json=True, timeout=20, ttl_seconds=ttl_seconds)
        if not isinstance(payload, list) or len(payload) < 2:
            continue
        for item in payload[1]:
            value = item.get("value")
            year = item.get("date")
            if value is None or not year:
                continue
            rows.append(
                {
                    "country_iso3": country_iso3,
                    "date": f"{year}-01-01",
                    "indicator_id": indicator_id,
                    "value": float(value),
                    "unit": unit,
                    "source": "World Bank",
                    "last_updated": now,
                }
            )
    return rows
