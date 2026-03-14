"""
seed_demo.py — Load demo data into the local SQLite database.

Usage:
  cd backend
  python scripts/seed_demo.py

What it does:
  1. Creates all tables (if not exist)
  2. Creates demo users (admin, adjuster1, investigator1)
  3. Inserts sample claims + entities from data/seed_data/
  4. Inserts graph edges for the fraud ring

After running: uvicorn main:app --reload
Login at http://localhost:5173 with admin / admin123
"""

import sys
import os
import json
import uuid
import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH        = Path("data/local.db")
SEED_DIR       = Path("../data/seed_data")
DB_PATH.parent.mkdir(exist_ok=True)

# Import after path setup
from core.security import hash_password

CREATE_TABLES = [
    """CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'adjuster',
        totp_enabled INTEGER DEFAULT 0, totp_secret TEXT, created_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS claims (
        claim_token TEXT PRIMARY KEY, claim_amount REAL, claim_type TEXT,
        incident_date TEXT, filing_date TEXT, prior_claim_count INTEGER DEFAULT 0,
        days_since_last_claim INTEGER, claimant_token TEXT, provider_token TEXT,
        repair_shop_token TEXT, adjuster_id TEXT, status TEXT DEFAULT 'pending',
        combined_score REAL, risk_level TEXT, created_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS entities (
        entity_token TEXT PRIMARY KEY, entity_type TEXT, claim_count INTEGER DEFAULT 0,
        fraud_score REAL DEFAULT 0.0, is_flagged INTEGER DEFAULT 0, last_seen TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS graph_edges (
        id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, target TEXT,
        edge_type TEXT, weight INTEGER DEFAULT 1, timestamp TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS inference_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, claim_token TEXT, gnn_score REAL,
        isolation_score REAL, combined_score REAL, risk_level TEXT,
        adjuster_id TEXT, factsheet_id TEXT, created_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, claim_token TEXT, assigned_to TEXT,
        due_at TEXT, status TEXT DEFAULT 'open', created_at TEXT
    )""",
]


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def seed():
    conn = get_conn()

    print("📦 Creating tables...")
    for sql in CREATE_TABLES:
        conn.execute(sql)
    conn.commit()

    print("👤 Creating demo users...")
    demo_users = [
        (str(uuid.uuid4()), "admin",         hash_password("admin123"), "admin"),
        (str(uuid.uuid4()), "adjuster1",     hash_password("pass123"),  "adjuster"),
        (str(uuid.uuid4()), "investigator1", hash_password("pass123"),  "investigator"),
    ]
    for uid, username, pw_hash, role in demo_users:
        existing = conn.execute("SELECT user_id FROM users WHERE username=?", (username,)).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO users (user_id, username, password_hash, role, totp_enabled, created_at) VALUES (?,?,?,?,0,?)",
                (uid, username, pw_hash, role, datetime.utcnow().isoformat()),
            )
            print(f"  ✓ {username} / {'admin123' if username == 'admin' else 'pass123'} ({role})")
        else:
            print(f"  · {username} already exists")
    conn.commit()

    # Load seed claims
    claims_path = SEED_DIR / "claims.json"
    if claims_path.exists():
        print("📋 Loading demo claims...")
        with open(claims_path) as f:
            claims = json.load(f)
        for claim in claims:
            conn.execute(
                """INSERT OR IGNORE INTO claims
                   (claim_token, claim_amount, claim_type, incident_date, filing_date,
                    prior_claim_count, days_since_last_claim, claimant_token, provider_token,
                    repair_shop_token, adjuster_id, status, combined_score, risk_level, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    claim["claim_token"], claim["claim_amount"], claim["claim_type"],
                    claim["incident_date"], claim["filing_date"], claim["prior_claim_count"],
                    claim.get("days_since_last_claim"), claim["claimant_token"],
                    claim["provider_token"], claim.get("repair_shop_token"),
                    claim["adjuster_id"], claim["status"],
                    claim.get("combined_score"), claim.get("risk_level"), claim["created_at"],
                ),
            )
        conn.commit()
        print(f"  ✓ {len(claims)} claims loaded")

    # Load entities
    entities_path = SEED_DIR / "entities.json"
    if entities_path.exists():
        print("🏢 Loading entities...")
        with open(entities_path) as f:
            entities = json.load(f)
        for e in entities:
            conn.execute(
                "INSERT OR IGNORE INTO entities (entity_token, entity_type, claim_count, fraud_score, is_flagged, last_seen) VALUES (?,?,?,?,?,?)",
                (e["entity_token"], e["entity_type"], e["claim_count"], e["fraud_score"], e["is_flagged"], e["last_seen"]),
            )
        conn.commit()
        print(f"  ✓ {len(entities)} entities loaded")

    # Seed graph edges (fraud ring)
    print("🕸️  Seeding fraud ring graph edges...")
    ring_edges = [
        ("CLAIMANT_A3F9", "SHOP_F2Q7",     "repaired_by",   3, "2024-01-15"),
        ("CLAIMANT_B7K2", "SHOP_F2Q7",     "repaired_by",   2, "2024-02-03"),
        ("CLAIMANT_C1M8", "SHOP_F2Q7",     "repaired_by",   4, "2024-03-21"),
        ("CLAIMANT_A3F9", "PROVIDER_D4N1", "treated_by",    2, "2024-01-16"),
        ("CLAIMANT_B7K2", "PROVIDER_D4N1", "treated_by",    1, "2024-02-04"),
        ("CLAIMANT_C1M8", "PROVIDER_E9P3", "treated_by",    2, "2024-03-22"),
        ("PROVIDER_D4N1", "SHOP_F2Q7",     "referred_to",   5, "2024-01-10"),
        ("CLAIMANT_A3F9", "CLAIMANT_B7K2", "shared_incident",1,"2024-01-20"),
    ]
    for source, target, edge_type, weight, ts in ring_edges:
        conn.execute(
            "INSERT INTO graph_edges (source, target, edge_type, weight, timestamp) VALUES (?,?,?,?,?)",
            (source, target, edge_type, weight, ts),
        )
    conn.commit()
    print(f"  ✓ {len(ring_edges)} graph edges inserted")

    conn.close()

    print("\n══════════════════════════════════════════")
    print("  ✅ Demo data loaded successfully!")
    print("  Run: uvicorn main:app --reload --port 8000")
    print("  Login: http://localhost:5173")
    print("    admin / admin123")
    print("    adjuster1 / pass123")
    print("══════════════════════════════════════════\n")


if __name__ == "__main__":
    seed()
