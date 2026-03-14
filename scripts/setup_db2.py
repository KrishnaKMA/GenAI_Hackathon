"""
setup_db2.py — Create tables in IBM Db2 for Teammate B.

Usage (after setting DB2_DSN in .env):
  cd backend
  python scripts/setup_db2.py

What it does:
  Creates the same schema that SQLite uses, but in IBM Db2.
  Run this ONCE before switching USE_DB2=True.

← TEAMMATE B: run this script after getting your DB2_DSN from IBM Cloud.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DB2_DSN = os.getenv("DB2_DSN")

if not DB2_DSN:
    print("❌ DB2_DSN not set in .env")
    print("   Get it from: IBM Cloud → Db2 → Service Credentials → dsn")
    sys.exit(1)

print(f"🔌 Connecting to Db2...")

try:
    import ibm_db
    import ibm_db_dbi
except ImportError:
    print("❌ ibm_db not installed. Run: pip install ibm_db")
    sys.exit(1)

CREATE_TABLES = [
    """CREATE TABLE IF NOT EXISTS USERS (
        USER_ID      VARCHAR(36) NOT NULL PRIMARY KEY,
        USERNAME     VARCHAR(64) UNIQUE NOT NULL,
        PASSWORD_HASH VARCHAR(128) NOT NULL,
        ROLE         VARCHAR(20) NOT NULL DEFAULT 'adjuster',
        TOTP_ENABLED SMALLINT DEFAULT 0,
        TOTP_SECRET  VARCHAR(64),
        CREATED_AT   VARCHAR(30)
    )""",
    """CREATE TABLE IF NOT EXISTS CLAIMS (
        CLAIM_TOKEN           VARCHAR(64) NOT NULL PRIMARY KEY,
        CLAIM_AMOUNT          DECIMAL(12,2),
        CLAIM_TYPE            VARCHAR(32),
        INCIDENT_DATE         VARCHAR(12),
        FILING_DATE           VARCHAR(12),
        PRIOR_CLAIM_COUNT     SMALLINT DEFAULT 0,
        DAYS_SINCE_LAST_CLAIM SMALLINT,
        CLAIMANT_TOKEN        VARCHAR(64),
        PROVIDER_TOKEN        VARCHAR(64),
        REPAIR_SHOP_TOKEN     VARCHAR(64),
        ADJUSTER_ID           VARCHAR(64),
        STATUS                VARCHAR(20) DEFAULT 'pending',
        COMBINED_SCORE        DECIMAL(5,2),
        RISK_LEVEL            VARCHAR(10),
        CREATED_AT            VARCHAR(30)
    )""",
    """CREATE TABLE IF NOT EXISTS ENTITIES (
        ENTITY_TOKEN VARCHAR(64) NOT NULL PRIMARY KEY,
        ENTITY_TYPE  VARCHAR(20),
        CLAIM_COUNT  SMALLINT DEFAULT 0,
        FRAUD_SCORE  DECIMAL(5,2) DEFAULT 0.00,
        IS_FLAGGED   SMALLINT DEFAULT 0,
        LAST_SEEN    VARCHAR(12)
    )""",
    """CREATE TABLE IF NOT EXISTS GRAPH_EDGES (
        ID         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        SOURCE     VARCHAR(64),
        TARGET     VARCHAR(64),
        EDGE_TYPE  VARCHAR(32),
        WEIGHT     SMALLINT DEFAULT 1,
        TIMESTAMP  VARCHAR(12)
    )""",
    """CREATE TABLE IF NOT EXISTS INFERENCE_LOG (
        ID              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        CLAIM_TOKEN     VARCHAR(64),
        GNN_SCORE       DECIMAL(5,2),
        ISOLATION_SCORE DECIMAL(5,2),
        COMBINED_SCORE  DECIMAL(5,2),
        RISK_LEVEL      VARCHAR(10),
        ADJUSTER_ID     VARCHAR(64),
        FACTSHEET_ID    VARCHAR(64),
        CREATED_AT      VARCHAR(30)
    )""",
    """CREATE TABLE IF NOT EXISTS TASKS (
        ID          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        CLAIM_TOKEN VARCHAR(64),
        ASSIGNED_TO VARCHAR(64),
        DUE_AT      VARCHAR(30),
        STATUS      VARCHAR(20) DEFAULT 'open',
        CREATED_AT  VARCHAR(30)
    )""",
]

try:
    conn = ibm_db_dbi.connect(DB2_DSN, "", "")
    cursor = conn.cursor()

    for sql in CREATE_TABLES:
        table_name = sql.split("TABLE IF NOT EXISTS")[1].split("(")[0].strip()
        try:
            cursor.execute(sql)
            print(f"  ✓ Table {table_name} created/verified")
        except Exception as e:
            print(f"  ⚠️  {table_name}: {e}")

    conn.commit()
    cursor.close()
    conn.close()

    print("\n✅ Db2 tables ready!")
    print("   Update DB2_DSN in .env and restart the backend.")

except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)
