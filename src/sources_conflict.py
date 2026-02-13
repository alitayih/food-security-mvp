from __future__ import annotations

import csv
from pathlib import Path


DEMO_META_PATH = Path("data/demo/indicators_meta.csv")
DEMO_VALUES_PATH = Path("data/demo/indicators_values.csv")


def load_demo_data() -> tuple[list[dict], list[dict]]:
    with DEMO_META_PATH.open(newline="", encoding="utf-8") as f:
        meta_rows = list(csv.DictReader(f))
    with DEMO_VALUES_PATH.open(newline="", encoding="utf-8") as f:
        value_rows = list(csv.DictReader(f))
    normalized_meta = [
        {
            "indicator_id": r["indicator_id"],
            "indicator_name": r["indicator_name"],
            "category": r["category"],
            "unit": r["unit"],
            "source": r["source"],
            "source_url": r["source_url"],
        }
        for r in meta_rows
    ]
    for row in value_rows:
        row["value"] = float(row["value"])
    return normalized_meta, value_rows
