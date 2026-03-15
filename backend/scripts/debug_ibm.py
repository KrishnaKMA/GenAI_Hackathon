"""
╔══════════════════════════════════════════════════════════╗
║         IBM DEBUG TOOL — ClaimShield                    ║
║                                                          ║
║  Run this to diagnose any IBM integration issue:         ║
║    cd backend                                            ║
║    python scripts/debug_ibm.py                          ║
║                                                          ║
║  Tests all three IBM components in order:                ║
║    1. Environment / credentials                          ║
║    2. IBM Db2 connection + tables                        ║
║    3. Watsonx / Granite LLM                              ║
║    4. Cross-component flow (write → read)                ║
╚══════════════════════════════════════════════════════════╝
"""

import asyncio
import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path

# Make backend importable when run from scripts/ 
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Colour helpers 
OK   = lambda s: print(f"  ✅ {s}")
FAIL = lambda s: print(f"  ❌ {s}")
WARN = lambda s: print(f"  ⚠️  {s}")
INFO = lambda s: print(f"     {s}")
HEAD = lambda s: print(f"\n{'─'*55}\n  {s}\n{'─'*55}")

PASS_COUNT = 0
FAIL_COUNT = 0

def record(passed: bool, msg: str):
    global PASS_COUNT, FAIL_COUNT
    if passed:
        PASS_COUNT += 1
        OK(msg)
    else:
        FAIL_COUNT += 1
        FAIL(msg)


# CHECK 1: Env Variables
def check_env():
    HEAD("CHECK 1 — Environment Variables")

    required = {
        "WATSONX_API_KEY":    "IBM Cloud → IAM → API Keys",
        "WATSONX_PROJECT_ID": "watsonx.ai → Your Project → Manage → General",
        "WATSONX_URL":        "should be https://us-south.ml.cloud.ibm.com",
        "DB2_DSN":            "IBM Cloud → Db2 → Service Credentials → dsn",
    }
    optional = {
        "WATSONX_SPACE_ID": "watsonx.ai → Spaces (needed for governance client)",
    }

    all_present = True
    for key, hint in required.items():
        val = os.getenv(key)
        if val:
            # Show truncated value so you can confirm it's reading the right thing
            display = val[:12] + "..." if len(val) > 12 else val
            record(True, f"{key} = {display}")
        else:
            record(False, f"{key} is MISSING  ← {hint}")
            all_present = False

    for key, hint in optional.items():
        val = os.getenv(key)
        if val:
            display = val[:12] + "..."
            OK(f"{key} = {display}  (optional — governance client)")
        else:
            WARN(f"{key} not set  ← {hint}")
            INFO("Without this, governance client falls back to project ID")

    # Common mistakes
    url = os.getenv("WATSONX_URL", "")
    if url and not url.startswith("https://"):
        record(False, "WATSONX_URL must start with https://")
    if url and url.endswith("/"):
        record(False, "WATSONX_URL must NOT end with a trailing slash")

    dsn = os.getenv("DB2_DSN", "")
    if dsn and "DATABASE=" not in dsn.upper() and "DSN=" not in dsn.upper():
        WARN("DB2_DSN looks unusual — expected format: DATABASE=xxx;HOSTNAME=xxx;PORT=xxx;...")

    return all_present


# CHECK 2 — DB2 CONNECTION + TABLES
def check_db2():
    HEAD("CHECK 2 — IBM Db2 Connection & Tables")

    DB2_DSN = os.getenv("DB2_DSN")
    if not DB2_DSN:
        record(False, "DB2_DSN not set — skipping Db2 checks")
        return False

    try:
        import ibm_db
    except ImportError:
        record(False, "ibm_db not installed  ← run: pip install ibm_db")
        return False

    # 2a — Raw connection
    conn = None
    try:
        conn = ibm_db.connect(DB2_DSN, "", "")
        record(True, "Connected to Db2 successfully")
    except Exception as e:
        record(False, f"Connection FAILED: {e}")
        INFO("Common causes:")
        INFO("  • Wrong DB2_DSN — copy it fresh from IBM Cloud → Db2 → Service Credentials")
        INFO("  • IBM Db2 service is stopped — check IBM Cloud dashboard")
        INFO("  • Network/firewall blocking port 50001")
        INFO("  • SSL certificate issue — try adding Security=SSL; to DSN")
        return False

    # 2b — Check each expected table exists
    expected_tables = ["USERS", "CLAIMS", "ENTITIES", "GRAPH_EDGES", "INFERENCE_LOG", "TASKS", "FACTSHEETS"]
    missing_tables  = []

    for table in expected_tables:
        try:
            stmt = ibm_db.exec_immediate(conn, f"SELECT 1 FROM {table} FETCH FIRST 1 ROWS ONLY")
            record(True, f"Table {table} exists")
        except Exception as e:
            msg = str(e).lower()
            if "sqlcode=-204" in msg or "undefined" in msg or "not found" in msg:
                record(False, f"Table {table} does not exist  ← run setup_db2.py")
                missing_tables.append(table)
            else:
                WARN(f"Table {table} check error: {e}")

    if missing_tables:
        INFO(f"Missing tables: {missing_tables}")
        INFO("Fix: cd backend && python scripts/setup_db2.py")

    # 2c — Write test to FACTSHEETS
    try:
        test_id = "TEST" + str(uuid.uuid4())[:4].upper()
        ibm_db.exec_immediate(conn, f"""
            INSERT INTO FACTSHEETS (
                FACTSHEET_ID, CLAIM_TOKEN, CREATED_AT,
                MODEL_VERSION, COMBINED_SCORE, RISK_LEVEL,
                ADJUSTER_ID, DECISION
            ) VALUES (
                '{test_id}', 'DEBUG_CLAIM', CURRENT_TIMESTAMP,
                'debug-v0', 0.0, 'LOW', 'debug_adj', 'APPROVED'
            )
        """)
        try:
            ibm_db.commit(conn)
        except Exception:
            pass
        record(True, f"Write to FACTSHEETS succeeded (test id: {test_id})")
    except Exception as e:
        record(False, f"Write to FACTSHEETS FAILED: {e}")
        INFO("Common causes:")
        INFO("  • Table schema mismatch — drop and re-run setup_db2.py")
        INFO("  • Db2 user has no INSERT permission")

    # 2d — Read test from FACTSHEETS
    try:
        stmt = ibm_db.exec_immediate(conn, "SELECT COUNT(*) AS CNT FROM FACTSHEETS")
        row  = ibm_db.fetch_assoc(stmt)
        count = row["CNT"] if row else "?"
        record(True, f"Read from FACTSHEETS succeeded ({count} rows total)")
    except Exception as e:
        record(False, f"Read from FACTSHEETS FAILED: {e}")

    # 2e — database.py integration check
    try:
        from core.database import USE_DB2, fetch_one
        if USE_DB2:
            record(True, "database.py is routing to Db2 (USE_DB2=True)")
        else:
            WARN("database.py is using SQLite — DB2_DSN not picked up by database.py")
            INFO("Check that database.py reads DB2_DSN from environment")
    except ImportError as e:
        WARN(f"Could not import database.py: {e}")

    try:
        ibm_db.close(conn)
    except Exception:
        pass

    return True


# CHECK 3 — WATSONX / GRANITE
async def check_granite():
    HEAD("CHECK 3 — Watsonx / Granite LLM")

    api_key    = os.getenv("WATSONX_API_KEY")
    project_id = os.getenv("WATSONX_PROJECT_ID")
    url        = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    if not api_key:
        record(False, "WATSONX_API_KEY missing — skipping Granite checks")
        return False

    try:
        from ibm_watsonx_ai import APIClient, Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
    except ImportError:
        record(False, "ibm-watsonx-ai not installed  ← run: pip install ibm-watsonx-ai")
        return False

    # 3a — Client init
    try:
        credentials = Credentials(url=url, api_key=api_key)
        client      = APIClient(credentials)
        record(True, "Watsonx APIClient initialized")
    except Exception as e:
        record(False, f"APIClient init FAILED: {e}")
        INFO("Common causes:")
        INFO("  • Invalid WATSONX_API_KEY — regenerate from IBM Cloud → IAM")
        INFO("  • Wrong WATSONX_URL — should be https://us-south.ml.cloud.ibm.com")
        return False

    # 3b — Model init
    try:
        model = ModelInference(
            model_id="ibm/granite-3-8b-instruct",
            api_client=client,
            project_id=project_id,
            params={
                GenParams.MAX_NEW_TOKENS: 50,
                GenParams.TEMPERATURE:    0.2,
            },
            verify=False,
        )
        record(True, "Granite ModelInference initialized")
    except Exception as e:
        record(False, f"ModelInference init FAILED: {e}")
        INFO("Common causes:")
        INFO("  • WATSONX_PROJECT_ID is wrong — check watsonx.ai → Project → Manage")
        INFO("  • Project not enabled for foundation models")
        return False

    # 3c — Actual generation test
    try:
        def _generate():
            return model.generate_text(prompt="Say the word HELLO only.")

        result = await asyncio.to_thread(_generate)
        if result and len(str(result).strip()) > 0:
            record(True, f"Granite generation succeeded → '{str(result).strip()[:60]}'")
        else:
            record(False, "Granite returned empty response")
            INFO("Common causes:")
            INFO("  • Model quota exceeded on your IBM Cloud account")
            INFO("  • Project not linked to a WML instance")
    except Exception as e:
        record(False, f"Granite generation FAILED: {e}")
        INFO("Common causes:")
        INFO("  • 403 Forbidden → API key lacks WML permissions")
        INFO("  • 404 Not Found → model ID wrong or not available in your region")
        INFO("  • Timeout → IBM service slowness, retry in a few minutes")
        return False

    return True


# CHECK 4 — CROSS-COMPONENT FLOW
# Does ibm_interface.py wire correctly end-to-end?
async def check_integration():
    HEAD("CHECK 4 — Cross-Component Integration Flow")

    try:
        from services.ibm_interface import (
            USE_MOCK, generate_narrative, log_factsheet, get_factsheets
        )
    except ImportError as e:
        record(False, f"Could not import ibm_interface: {e}")
        return

    if USE_MOCK:
        WARN("ibm_interface is in MOCK mode — set WATSONX_API_KEY to test real flow")
        INFO("Mock flow will still be tested below")

    # Build a minimal fake FraudAnalysisResult
    try:
        from models.schemas import FraudAnalysisResult
        fake_analysis = FraudAnalysisResult(
            claim_token    = "DEBUG_CLAIM_001",
            gnn_score      = 75.0,
            isolation_score= 65.0,
            combined_score = 70.0,
            risk_level     = "HIGH",
            gnn_evidence   = [],
            shap_features  = [],
            graph_nodes    = [],
            graph_edges    = [],
        )
        record(True, "FraudAnalysisResult built successfully")
    except Exception as e:
        record(False, f"Could not build FraudAnalysisResult: {e}")
        INFO("This means schemas.py has changed — check field names match")
        return

    # 4a — Narrative generation
    try:
        narrative = await generate_narrative(fake_analysis)
        if narrative and len(narrative) > 50:
            record(True, f"generate_narrative() returned {len(narrative)} chars")
            mode = "MOCK" if USE_MOCK else "REAL Granite"
            INFO(f"Mode: {mode}")
            INFO(f"Preview: {narrative[:80]}...")
        else:
            record(False, "generate_narrative() returned too short / empty response")
    except Exception as e:
        record(False, f"generate_narrative() FAILED: {e}")
        INFO("Check WATSONX_API_KEY and WATSONX_PROJECT_ID")

    # 4b — Factsheet write
    factsheet_id = None
    try:
        factsheet_id = await log_factsheet("DEBUG_CLAIM_001", fake_analysis, "debug_adj")
        record(True, f"log_factsheet() succeeded → id: {factsheet_id}")
    except Exception as e:
        record(False, f"log_factsheet() FAILED: {e}")
        INFO("Check DB2_DSN is set and setup_db2.py has been run")

    # 4c — Factsheet read
    try:
        sheets = await get_factsheets(limit=5)
        if isinstance(sheets, list):
            record(True, f"get_factsheets() returned {len(sheets)} entries")
            if sheets:
                first = sheets[0]
                INFO(f"Latest entry: {first.claim_token} | {first.risk_level} | {first.decision}")
        else:
            record(False, "get_factsheets() did not return a list")
    except Exception as e:
        record(False, f"get_factsheets() FAILED: {e}")
        INFO("Check DB2_DSN and that FACTSHEETS table exists")

    # 4d — Confirm write appeared in read
    if factsheet_id:
        try:
            sheets     = await get_factsheets(limit=50)
            ids        = [s.factsheet_id for s in sheets]
            if factsheet_id in ids:
                record(True, f"Write→Read confirmed: {factsheet_id} found in get_factsheets()")
            else:
                WARN(f"Write→Read mismatch: {factsheet_id} not found in latest 50 entries")
                INFO("Could be timing, or governance client stores differently than expected")
        except Exception as e:
            WARN(f"Could not verify write→read loop: {e}")



# COMMON ISSUES REFERENCE
def print_common_issues():
    HEAD("COMMON ISSUES REFERENCE")
    issues = [
        ("Logs say MOCK after setting credentials",
         "Restart the server — env vars are read at startup, not per-request"),

        ("DB2 connect: [IBM][CLI Driver] SQL30082N",
         "Wrong username/password in DSN, or account locked"),

        ("DB2 connect: TCP/IP connection timeout",
         "Port 50001 is blocked — check firewall or IBM Cloud allowlist"),

        ("DB2 connect: SSL error / certificate verify failed",
         "Add Security=SSL;SSLServerCertificate=<path>; to DB2_DSN, or disable SSL for dev"),

        ("Granite 403 Forbidden",
         "API key exists but lacks WML service permissions — check IAM roles"),

        ("Granite 404 Not Found",
         "Wrong model ID or model not available in us-south — check region"),

        ("Granite returns empty string",
         "MIN_NEW_TOKENS=80 forces output — if still empty, quota may be exhausted"),

        ("setup_db2.py: module not found",
         "Run from backend/ directory: cd backend && python scripts/setup_db2.py"),

        ("ibm_db ImportError on Mac/Linux",
         "Needs IBM ODBC driver — see: https://github.com/ibmdb/python-ibmdb"),

        ("get_factsheets() returns empty list",
         "No entries yet, or FACTSHEETS table missing — run setup_db2.py then POST /analyze first"),

        ("Narrative is hardcoded, not AI-generated",
         "USE_MOCK=True — WATSONX_API_KEY is missing or blank in .env"),

        ("database.py still using SQLite with DB2_DSN set",
         "DB2_DSN is set in ibm_interface.py env but database.py reads it fresh — check .env is loaded"),
    ]

    for i, (symptom, fix) in enumerate(issues, 1):
        print(f"\n  [{i:02d}] SYMPTOM: {symptom}")
        print(f"       FIX:     {fix}")



# MAIN
async def main():
    print("\n" + "═"*55)
    print("  IBM DEBUG TOOL — ClaimShield")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═"*55)

    check_env()
    check_db2()
    await check_granite()
    await check_integration()
    print_common_issues()

    # Final summary
    HEAD("SUMMARY")
    total = PASS_COUNT + FAIL_COUNT
    print(f"  Passed: {PASS_COUNT}/{total}")
    print(f"  Failed: {FAIL_COUNT}/{total}")

    if FAIL_COUNT == 0:
        print("\n  All checks passed — IBM integration looks good!")
    else:
        print(f"\n  {FAIL_COUNT} issue(s) found — see above for fixes")

    print()


if __name__ == "__main__":
    asyncio.run(main())