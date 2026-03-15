"""
Database abstraction layer.
• SQLite (default) -- auto-created at data/local.db, no setup needed
• IBM Db2 -- activates automatically when DB2_DSN env var is set
 
# TEAMMATE B: Set DB2_DSN in .env to activate Db2.
  Run `python scripts/setup_db2.py` to create tables in Db2 first.
 
All other code uses fetch_one(), fetch_all(), execute() -- no changes needed.
"""
 
import os
import sqlite3
import asyncio
from pathlib import Path
from typing import Optional
 
import ibm_db
 

# AUTO-DETECTION
# Essentially detects if DB2 is active if not defaults to SQLite
DB2_DSN = os.getenv("DB2_DSN")
USE_DB2  = bool(DB2_DSN)


# Detect database location of SQLITE
SQLITE_PATH = Path("data/local.db")
SQLITE_PATH.parent.mkdir(exist_ok=True)
 
if USE_DB2:
    print("[DB] OK: DB2_DSN found -- using IBM Db2")
else:
    print("[DB] WARNING: DB2_DSN not set -- using SQLite at", SQLITE_PATH)
 
 

# TABLE SCHEMA
# note: Two versions because Db2 and SQLite differ on:
#   - AUTOINCREMENT vs GENERATED ALWAYS AS IDENTITY
#   - TEXT vs VARCHAR
#   - No IF NOT EXISTS in Db2 (we catch the error instead)


# SQLite version
SQLITE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id       TEXT PRIMARY KEY,
        username      TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role          TEXT NOT NULL DEFAULT 'adjuster',
        totp_enabled  INTEGER DEFAULT 0,
        totp_secret   TEXT,
        created_at    TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS claims (
        claim_token           TEXT PRIMARY KEY,
        claim_amount          REAL,
        claim_type            TEXT,
        incident_date         TEXT,
        filing_date           TEXT,
        prior_claim_count     INTEGER DEFAULT 0,
        days_since_last_claim INTEGER,
        claimant_token        TEXT,
        provider_token        TEXT,
        repair_shop_token     TEXT,
        adjuster_id           TEXT,
        status                TEXT DEFAULT 'pending',
        combined_score        REAL,
        risk_level            TEXT,
        created_at            TEXT
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
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        source    TEXT,
        target    TEXT,
        edge_type TEXT,
        weight    INTEGER DEFAULT 1,
        timestamp TEXT
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
 
# Db2 version — no IF NOT EXISTS, VARCHAR instead of TEXT,
# GENERATED ALWAYS AS IDENTITY instead of AUTOINCREMENT
DB2_TABLES_SQL = [
    """
    CREATE TABLE users (
        user_id       VARCHAR(64)  NOT NULL PRIMARY KEY,
        username      VARCHAR(128) NOT NULL,
        password_hash VARCHAR(256) NOT NULL,
        role          VARCHAR(32)  NOT NULL DEFAULT 'adjuster',
        totp_enabled  SMALLINT     DEFAULT 0,
        totp_secret   VARCHAR(128),
        created_at    VARCHAR(32)
    )
    """,
    """
    CREATE TABLE claims (
        claim_token           VARCHAR(128) NOT NULL PRIMARY KEY,
        claim_amount          DOUBLE,
        claim_type            VARCHAR(64),
        incident_date         VARCHAR(32),
        filing_date           VARCHAR(32),
        prior_claim_count     INTEGER      DEFAULT 0,
        days_since_last_claim INTEGER,
        claimant_token        VARCHAR(128),
        provider_token        VARCHAR(128),
        repair_shop_token     VARCHAR(128),
        adjuster_id           VARCHAR(64),
        status                VARCHAR(32)  DEFAULT 'pending',
        combined_score        DOUBLE,
        risk_level            VARCHAR(16),
        created_at            VARCHAR(32)
    )
    """,
    """
    CREATE TABLE entities (
        entity_token VARCHAR(128) NOT NULL PRIMARY KEY,
        entity_type  VARCHAR(64),
        claim_count  INTEGER      DEFAULT 0,
        fraud_score  DOUBLE       DEFAULT 0.0,
        is_flagged   SMALLINT     DEFAULT 0,
        last_seen    VARCHAR(32)
    )
    """,
    """
    CREATE TABLE graph_edges (
        id        INTEGER      NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        source    VARCHAR(128),
        target    VARCHAR(128),
        edge_type VARCHAR(64),
        weight    INTEGER      DEFAULT 1,
        timestamp VARCHAR(32)
    )
    """,
    """
    CREATE TABLE inference_log (
        id              INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        claim_token     VARCHAR(128),
        gnn_score       DOUBLE,
        isolation_score DOUBLE,
        combined_score  DOUBLE,
        risk_level      VARCHAR(16),
        adjuster_id     VARCHAR(64),
        factsheet_id    VARCHAR(32),
        created_at      VARCHAR(32)
    )
    """,
    """
    CREATE TABLE tasks (
        id          INTEGER     NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        claim_token VARCHAR(128),
        assigned_to VARCHAR(64),
        due_at      VARCHAR(32),
        status      VARCHAR(32) DEFAULT 'open',
        created_at  VARCHAR(32)
    )
    """,
]
 
 

# DB2 HELPERS


# Connection to IBM Cloudbase
def _db2_connect():
    return ibm_db.connect(DB2_DSN, "", "")
 

def _db2_close(conn):
    try:
        ibm_db.close(conn)
    except Exception:
        pass
 

# Conversion of db2 rows into dicts
def _db2_row_to_dict(stmt) -> Optional[dict]:
    """Fetch one row from a Db2 statement as a dict, or None."""
    row = ibm_db.fetch_assoc(stmt)
    return dict(row) if row else None
 
 
def _db2_all_rows(stmt) -> list[dict]:
    """Fetch all rows from a Db2 statement as a list of dicts."""
    rows = []
    row = ibm_db.fetch_assoc(stmt)
    while row:
        rows.append(dict(row))
        row = ibm_db.fetch_assoc(stmt)
    return rows
 

# Create db2 tables, ignoring "already exists" errors (Db2 doesn't support IF NOT EXISTS)
def _db2_create_table(conn, sql: str):
    """Run a CREATE TABLE, silently ignore 'already exists' errors."""
    try:
        ibm_db.exec_immediate(conn, sql)
    except Exception as e:
        msg = str(e).lower()
        if not any(code in msg for code in ["sqlcode=-601", "sqlstate=42710", "already exists"]):
            raise
 
 

# SQLITE HELPERS
def _get_sqlite_conn():
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    return conn
 
 
# PUBLIC API
async def create_tables():
    """Create all tables on startup if they don't exist."""
    if USE_DB2:
        def _create():
            conn = _db2_connect()
            try:
                for sql in DB2_TABLES_SQL:
                    _db2_create_table(conn, sql)
            finally:
                _db2_close(conn)
 
        await asyncio.to_thread(_create)
        print("[DB] Db2 tables ready")
        return
 
    def _create_sqlite():
        conn = _get_sqlite_conn()
        for sql in SQLITE_TABLES_SQL:
            conn.execute(sql)
        conn.commit()
        conn.close()
 
    await asyncio.to_thread(_create_sqlite)
    print("[DB] SQLite tables ready")
 
 
async def fetch_one(sql: str, params: tuple = ()) -> Optional[dict]:
    """Execute a SELECT and return the first row as a dict, or None."""
    if USE_DB2:
        def _fetch():
            conn = _db2_connect()
            try:
                stmt = ibm_db.prepare(conn, sql)
                ibm_db.execute(stmt, params) if params else ibm_db.execute(stmt)
                return _db2_row_to_dict(stmt)
            finally:
                _db2_close(conn)
 
        return await asyncio.to_thread(_fetch)
 
    def _fetch_sqlite():
        conn = _get_sqlite_conn()
        row = conn.execute(sql, params).fetchone()
        conn.close()
        return dict(row) if row else None
 
    return await asyncio.to_thread(_fetch_sqlite)
 
 
async def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a SELECT and return all rows as a list of dicts."""
    if USE_DB2:
        def _fetch():
            conn = _db2_connect()
            try:
                stmt = ibm_db.prepare(conn, sql)
                ibm_db.execute(stmt, params) if params else ibm_db.execute(stmt)
                return _db2_all_rows(stmt)
            finally:
                _db2_close(conn)
 
        return await asyncio.to_thread(_fetch)
 
    def _fetch_sqlite():
        conn = _get_sqlite_conn()
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]
 
    return await asyncio.to_thread(_fetch_sqlite)
 
 
async def execute(sql: str, params: tuple = ()) -> None:
    """Execute an INSERT / UPDATE / DELETE statement."""
    if USE_DB2:
        def _exec():
            conn = _db2_connect()
            try:
                stmt = ibm_db.prepare(conn, sql)
                ibm_db.execute(stmt, params) if params else ibm_db.execute(stmt)
                try:
                    ibm_db.commit(conn)
                except Exception:
                    pass  # Db2 auto-commits in some configurations
            finally:
                _db2_close(conn)
 
        return await asyncio.to_thread(_exec)
 
    def _exec_sqlite():
        conn = _get_sqlite_conn()
        conn.execute(sql, params)
        conn.commit()
        conn.close()
 
    await asyncio.to_thread(_exec_sqlite)
 
 
async def execute_many(sql: str, params_list: list[tuple]) -> None:
    """Execute a batch INSERT / UPDATE."""
    if USE_DB2:
        def _exec():
            conn = _db2_connect()
            try:
                stmt = ibm_db.prepare(conn, sql)
                for params in params_list:
                    ibm_db.execute(stmt, params)
                try:
                    ibm_db.commit(conn)
                except Exception:
                    pass
            finally:
                _db2_close(conn)
 
        return await asyncio.to_thread(_exec)
 
    def _exec_sqlite():
        conn = _get_sqlite_conn()
        conn.executemany(sql, params_list)
        conn.commit()
        conn.close()
 
    await asyncio.to_thread(_exec_sqlite)
 