from pathlib import Path

from src.cache import cache_get, cache_set
from src.scenarios import simulate
from src.scoring import compute_scores
from src.sources_conflict import load_demo_data
from src.utils import clamp, deterministic_summary, to_risk_scale


def test_clamp_low():
    assert clamp(-1) == 0


def test_clamp_high():
    assert clamp(999) == 100


def test_to_risk_scale_standard():
    assert to_risk_scale(20, 0, 40) == 50


def test_to_risk_scale_invert():
    assert to_risk_scale(10, 0, 20, invert=True) == 50


def test_compute_scores_range():
    window = [
        {"indicator_id": "inflation", "value": 5, "category": "macro"},
        {"indicator_id": "inflation", "value": 20, "category": "macro"},
        {"indicator_id": "food_price_stress", "value": 40, "category": "food"},
        {"indicator_id": "food_price_stress", "value": 80, "category": "food"},
        {"indicator_id": "conflict_events", "value": 50, "category": "conflict"},
        {"indicator_id": "conflict_events", "value": 100, "category": "conflict"},
    ]
    latest = [
        {"indicator_id": "inflation", "value": 20, "category": "macro"},
        {"indicator_id": "food_price_stress", "value": 80, "category": "food"},
        {"indicator_id": "conflict_events", "value": 100, "category": "conflict"},
    ]
    score = compute_scores(window, latest)
    assert 0 <= score["overall_risk"] <= 100


def test_compute_scores_has_explainability():
    rows = [{"indicator_id": "inflation", "value": 10, "category": "macro"}]
    out = compute_scores(rows, rows)
    assert "weights" in out and "normalized_inputs" in out and "contributors" in out


def test_simulate_shock_changes_values():
    rows = [{"indicator_id": "inflation", "value": 10.0, "category": "macro"}]
    out = simulate(rows, "currency_depreciation", severity=100, horizon=12)
    assert out[0]["value"] > 10


def test_deterministic_summary_contains_country():
    s = deterministic_summary("KEN", 62.5, ["inflation"], 2)
    assert "KEN" in s


def test_cache_roundtrip(tmp_path: Path):
    cache_set(tmp_path, "k", {"x": 1})
    assert cache_get(tmp_path, "k", ttl_seconds=3600) == {"x": 1}


def test_demo_loader_has_rows():
    meta, values = load_demo_data()
    assert len(meta) > 0 and len(values) > 0
