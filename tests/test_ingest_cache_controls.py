from src.db import get_connection, init_db
from src.ingest import ingest_country


def test_ingest_demo_mode_ignores_live_sources(monkeypatch):
    conn = get_connection(':memory:')
    init_db(conn)

    def _boom(*args, **kwargs):
        raise AssertionError('live source should not be called in demo mode')

    monkeypatch.setattr('src.ingest.fetch_world_bank', _boom)
    monkeypatch.setattr('src.ingest.fetch_food_source', _boom)

    mode = ingest_country(conn, 'KEN', demo_mode=True, ttl_hours=1)
    assert mode == 'demo'


def test_ingest_passes_ttl_to_sources(monkeypatch):
    conn = get_connection(':memory:')
    init_db(conn)
    calls = []

    def fake_wb(country, ttl_seconds):
        calls.append(('wb', ttl_seconds))
        return []

    def fake_food(country, ttl_seconds):
        calls.append(('food', ttl_seconds))
        return []

    monkeypatch.setattr('src.ingest.fetch_world_bank', fake_wb)
    monkeypatch.setattr('src.ingest.fetch_food_source', fake_food)

    mode = ingest_country(conn, 'KEN', demo_mode=False, ttl_hours=6)
    assert mode == 'live'
    assert ('wb', 21600) in calls
    assert ('food', 21600) in calls
