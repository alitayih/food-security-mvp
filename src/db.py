from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterable

DEFAULT_DB = Path("app_data/food_security.db")


def resolve_db_path() -> Path:
    preferred = Path(os.getenv("APP_DB_PATH", str(DEFAULT_DB)))
    preferred.parent.mkdir(parents=True, exist_ok=True)
    try:
        with preferred.parent.joinpath(".write_test").open("w", encoding="utf-8") as fp:
            fp.write("ok")
        preferred.parent.joinpath(".write_test").unlink(missing_ok=True)
        return preferred
    except Exception:
        fallback = Path("/tmp/app_data/food_security.db")
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return fallback


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else resolve_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_db_path(conn: sqlite3.Connection) -> str:
    row = conn.execute("PRAGMA database_list").fetchone()
    return row[2] if row and row[2] else ":memory:"


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS indicators_meta(
            indicator_id TEXT PRIMARY KEY,
            indicator_name TEXT NOT NULL,
            category TEXT NOT NULL,
            unit TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS indicators_values(
            country_iso3 TEXT NOT NULL,
            date TEXT NOT NULL,
            indicator_id TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            source TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            PRIMARY KEY(country_iso3, date, indicator_id),
            FOREIGN KEY(indicator_id) REFERENCES indicators_meta(indicator_id)
        );

        CREATE TABLE IF NOT EXISTS alerts(
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_iso3 TEXT NOT NULL,
            indicator_id TEXT NOT NULL,
            direction TEXT NOT NULL,
            threshold REAL NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS alert_events(
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id INTEGER NOT NULL,
            triggered_at TEXT NOT NULL,
            observed_value REAL NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY(alert_id) REFERENCES alerts(alert_id)
        );

        CREATE TABLE IF NOT EXISTS scenarios(
            scenario_id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_iso3 TEXT NOT NULL,
            shock_type TEXT NOT NULL,
            severity REAL NOT NULL,
            horizon INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ingestion_runs(
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_iso3 TEXT NOT NULL,
            mode TEXT NOT NULL,
            ingested_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def record_ingestion_run(conn: sqlite3.Connection, country_iso3: str, mode: str, ingested_at: str) -> None:
    conn.execute(
        "INSERT INTO ingestion_runs(country_iso3, mode, ingested_at) VALUES (?,?,?)",
        (country_iso3, mode, ingested_at),
    )
    conn.commit()


def get_latest_ingestion_run(conn: sqlite3.Connection, country_iso3: str) -> dict | None:
    row = conn.execute(
        """
        SELECT country_iso3, mode, ingested_at
        FROM ingestion_runs
        WHERE country_iso3=?
        ORDER BY ingested_at DESC
        LIMIT 1
        """,
        (country_iso3,),
    ).fetchone()
    return dict(row) if row else None


def upsert_meta(conn: sqlite3.Connection, rows: Iterable[dict]) -> None:
    conn.executemany(
        """
        INSERT INTO indicators_meta(indicator_id,indicator_name,category,unit,source,source_url)
        VALUES (:indicator_id,:indicator_name,:category,:unit,:source,:source_url)
        ON CONFLICT(indicator_id) DO UPDATE SET
          indicator_name=excluded.indicator_name,
          category=excluded.category,
          unit=excluded.unit,
          source=excluded.source,
          source_url=excluded.source_url
        """,
        rows,
    )
    conn.commit()


def upsert_values(conn: sqlite3.Connection, rows: Iterable[dict]) -> None:
    conn.executemany(
        """
        INSERT INTO indicators_values(country_iso3,date,indicator_id,value,unit,source,last_updated)
        VALUES (:country_iso3,:date,:indicator_id,:value,:unit,:source,:last_updated)
        ON CONFLICT(country_iso3,date,indicator_id) DO UPDATE SET
          value=excluded.value,
          unit=excluded.unit,
          source=excluded.source,
          last_updated=excluded.last_updated
        """,
        rows,
    )
    conn.commit()


def query_country_values(conn: sqlite3.Connection, country_iso3: str):
    return conn.execute(
        """
        SELECT v.country_iso3, v.date, v.indicator_id, v.value, v.unit, v.source, m.category
        FROM indicators_values v
        JOIN indicators_meta m ON m.indicator_id = v.indicator_id
        WHERE v.country_iso3 = ?
        ORDER BY v.date
        """,
        (country_iso3,),
    ).fetchall()
