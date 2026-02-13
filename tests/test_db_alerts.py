from src.alerts import add_alert_rule, evaluate_alerts
from src.db import get_connection, init_db, upsert_meta, upsert_values
from src.ingest import ingest_country
from src.scenarios import record_scenario


def setup_conn():
    conn = get_connection(':memory:')
    init_db(conn)
    upsert_meta(
        conn,
        [
            {
                'indicator_id': 'inflation',
                'indicator_name': 'Inflation',
                'category': 'macro',
                'unit': '%',
                'source': 'x',
                'source_url': 'x',
            }
        ],
    )
    upsert_values(
        conn,
        [
            {
                'country_iso3': 'KEN',
                'date': '2024-01-01',
                'indicator_id': 'inflation',
                'value': 12.0,
                'unit': '%',
                'source': 'x',
                'last_updated': 'now',
            }
        ],
    )
    return conn


def test_add_alert_rule_returns_id():
    conn = setup_conn()
    aid = add_alert_rule(conn, 'KEN', 'inflation', 'above', 10)
    assert aid > 0


def test_evaluate_alerts_triggers():
    conn = setup_conn()
    add_alert_rule(conn, 'KEN', 'inflation', 'above', 10)
    hits = evaluate_alerts(conn, 'KEN')
    assert len(hits) == 1


def test_evaluate_alerts_not_triggered():
    conn = setup_conn()
    add_alert_rule(conn, 'KEN', 'inflation', 'above', 20)
    hits = evaluate_alerts(conn, 'KEN')
    assert len(hits) == 0


def test_ingest_country_demo_mode():
    conn = get_connection(':memory:')
    init_db(conn)
    mode = ingest_country(conn, 'KEN', demo_mode=True)
    assert mode == 'demo'


def test_record_scenario_table_exists():
    conn = get_connection(':memory:')
    init_db(conn)
    sid = record_scenario(conn, 'KEN', 'currency_depreciation', 50.0, 6)
    assert sid > 0
