import sqlite3
import datetime

from . import config


def _connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nickel_daily (
                date TEXT PRIMARY KEY,
                spot REAL,
                lme REAL,
                currency TEXT,
                unit TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS monitor_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TEXT,
                status TEXT,
                detail TEXT
            )
            """
        )


def get_daily_by_date(date_str):
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM nickel_daily WHERE date = ?", (date_str,)
        ).fetchone()
        return dict(row) if row else None


def upsert_daily(record):
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO nickel_daily (date, spot, lme, currency, unit, created_at)
            VALUES (:date, :spot, :lme, :currency, :unit, :created_at)
            ON CONFLICT(date) DO UPDATE SET
                spot = excluded.spot,
                lme = excluded.lme,
                currency = excluded.currency,
                unit = excluded.unit,
                created_at = excluded.created_at
            """,
            record,
        )


def list_daily():
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM nickel_daily ORDER BY date ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def add_monitor_log(status, detail=""):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO monitor_log (run_at, status, detail) VALUES (?, ?, ?)",
            (datetime.datetime.now().isoformat(timespec="seconds"), status, detail),
        )


def last_monitor_log():
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM monitor_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
