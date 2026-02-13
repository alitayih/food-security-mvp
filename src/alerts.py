from __future__ import annotations

from datetime import datetime, timezone
import sqlite3


def add_alert_rule(
    conn: sqlite3.Connection,
    country_iso3: str,
    indicator_id: str,
    direction: str,
    threshold: float,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO alerts(country_iso3, indicator_id, direction, threshold, created_at)
        VALUES (?,?,?,?,?)
        """,
        (country_iso3, indicator_id, direction, threshold, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return int(cur.lastrowid)


def evaluate_alerts(conn: sqlite3.Connection, country_iso3: str) -> list[dict]:
    rules = conn.execute("SELECT * FROM alerts WHERE country_iso3=?", (country_iso3,)).fetchall()
    hits: list[dict] = []
    for rule in rules:
        latest = conn.execute(
            """
            SELECT value, date FROM indicators_values
            WHERE country_iso3=? AND indicator_id=?
            ORDER BY date DESC LIMIT 1
            """,
            (country_iso3, rule["indicator_id"]),
        ).fetchone()
        if not latest:
            continue
        triggered = (
            latest["value"] >= rule["threshold"]
            if rule["direction"] == "above"
            else latest["value"] <= rule["threshold"]
        )
        if triggered:
            conn.execute(
                """
                INSERT INTO alert_events(alert_id, triggered_at, observed_value, date)
                VALUES (?,?,?,?)
                """,
                (
                    rule["alert_id"],
                    datetime.now(timezone.utc).isoformat(),
                    latest["value"],
                    latest["date"],
                ),
            )
            hits.append(
                {
                    "alert_id": rule["alert_id"],
                    "indicator_id": rule["indicator_id"],
                    "observed_value": latest["value"],
                    "date": latest["date"],
                }
            )
    conn.commit()
    return hits


def list_alert_events(conn: sqlite3.Connection, country_iso3: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT ae.event_id, ae.triggered_at, ae.observed_value, ae.date, a.indicator_id
        FROM alert_events ae
        JOIN alerts a ON a.alert_id = ae.alert_id
        WHERE a.country_iso3 = ?
        ORDER BY ae.triggered_at DESC
        """,
        (country_iso3,),
    ).fetchall()
    return [dict(r) for r in rows]
