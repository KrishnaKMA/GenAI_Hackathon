"""
Database abstraction layer.
• SQLite (default) -- auto-created at data/local.db, no setup needed
• IBM Db2 -- activates automatically when DB2_DSN env var is set

# TEAMMATE B: Set DB2_DSN in .env to activate Db2.
  Run `python scripts/setup_db2.py` to create tables in Db2 first.
  The same SQL table schema works for both SQLite and Db2.

All other code uses fetch_one(), fetch_all(), execute() -- no changes needed.
"""

import os
import sqlite3
import asyncio
from pathlib import Path
from typing import Any, Optional, Union
from contextlib import asynccontextmanager

# ─────────────────────────────────────────────────────────
# AUTO-DETECTION
# ─────────────────────────────────────────────────────────
DB2_DSN = os.getenv("DB2_DSN")
USE_DB2  = bool(DB2_DSN)

SQLITE_PATH = Path("data/local.db")
SQLITE_PATH.parent.mkdir(exist_ok=True)

if USE_DB2:
    print("[DB] OK: DB2_DSN found -- using IBM Db2")
    # # TEAMMATE B: initialize your ibm_db2 connection pool here
    # import ibm_db
    # import ibm_db_dbi
    # _db2_conn = ibm_db_dbi.connect(DB2_DSN, "", "")
else:
    print("[DB] WARNING:  DB2_DSN not set -- using SQLite at", SQLITE_PATH)


# ─────────────────────────────────────────────────────────
# TABLE SCHEMA (same DDL for SQLite and Db2)
# ─────────────────────────────────────────────────────────

CREATE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id     TEXT PRIMARY KEY,
        username    TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role        TEXT NOT NULL DEFAULT 'adjuster',
        totp_enabled INTEGER DEFAULT 0,
        totp_secret TEXT,
        created_at  TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS claims (
        claim_token      TEXT PRIMARY KEY,
        claim_amount     REAL,
        claim_type       TEXT,
        incident_date    TEXT,
        filing_date      TEXT,
        prior_claim_count INTEGER DEFAULT 0,
        days_since_last_claim INTEGER,
        claimant_token   TEXT,
        provider_token   TEXT,
        repair_shop_token TEXT,
        adjuster_id      TEXT,
        status           TEXT DEFAULT 'pending',
        combined_score   REAL,
        risk_level       TEXT,
        created_at       TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS entities (
        entity_token TEXT PRIMARY KEY,
        entity_type  TEXT,
        claim_count  INTEGER DEFAULT 0,
        fraud_score  REAL DEFAULT 0.0,
        is_flagged   INTEGER DEFAULT 0,
        last_seen    TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS graph_edges (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        source      TEXT,
        target      TEXT,
        edge_type   TEXT,
        weight      INTEGER DEFAULT 1,
        timestamp   TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS inference_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_token     TEXT,
        gnn_score       REAL,
        isolation_score REAL,
        combined_score  REAL,
        risk_level      TEXT,
        adjuster_id     TEXT,
        factsheet_id    TEXT,
        created_at      TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_token TEXT,
        assigned_to TEXT,
        due_at      TEXT,
        status      TEXT DEFAULT 'open',
        created_at  TEXT
    )
    """,
]


# ─────────────────────────────────────────────────────────
# SQLITE HELPERS (used when Db2 not connected)
# ─────────────────────────────────────────────────────────

def _get_sqlite_conn():
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


async def create_tables():
    """Create all tables on startup if they don't exist."""
    if USE_DB2:
        # # TEAMMATE B: run CREATE TABLE IF NOT EXISTS for Db2 here
        print("[DB] Skipping SQLite table creation -- Db2 active")
        return

    loop = asyncio.get_event_loop()
    def _create():
        conn = _get_sqlite_conn()
        for sql in CREATE_TABLES_SQL:
            conn.execute(sql)
        conn.commit()
        conn.close()
    await loop.run_in_executor(None, _create)
    print("[DB] SQLite tables ready")


async def fetch_one(sql: str, params: tuple = ()) -> Optional[dict]:
    """Execute a SELECT and return the first row as a dict, or None."""
    if USE_DB2:
        raise NotImplementedError("Teammate B: implement Db2 fetch_one()")

    loop = asyncio.get_event_loop()
    def _fetch():
        conn = _get_sqlite_conn()
        row = conn.execute(sql, params).fetchone()
        conn.close()
        return dict(row) if row else None
    return await loop.run_in_executor(None, _fetch)


async def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a SELECT and return all rows as a list of dicts."""
    if USE_DB2:
        raise NotImplementedError("Teammate B: implement Db2 fetch_all()")

    loop = asyncio.get_event_loop()
    def _fetch():
        conn = _get_sqlite_conn()
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    return await loop.run_in_executor(None, _fetch)


async def execute(sql: str, params: tuple = ()) -> None:
    """Execute an INSERT / UPDATE / DELETE statement."""
    if USE_DB2:
        raise NotImplementedError("Teammate B: implement Db2 execute()")

    loop = asyncio.get_event_loop()
    def _exec():
        conn = _get_sqlite_conn()
        conn.execute(sql, params)
        conn.commit()
        conn.close()
    await loop.run_in_executor(None, _exec)


async def execute_many(sql: str, params_list: list[tuple]) -> None:
    """Execute a batch INSERT / UPDATE."""
    if USE_DB2:
        raise NotImplementedError("Teammate B: implement Db2 execute_many()")

    loop = asyncio.get_event_loop()
    def _exec():
        conn = _get_sqlite_conn()
        conn.executemany(sql, params_list)
        conn.commit()
        conn.close()
    await loop.run_in_executor(None, _exec)
