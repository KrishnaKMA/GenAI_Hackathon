"""
One-time setup script — creates all tables in IBM Db2.
 
Run this ONCE before starting the app:
    cd backend
    python scripts/setup_db2.py
 
Requires DB2_DSN to be set in .env
Safe to re-run — existing tables are left alone.
"""
 
import asyncio
import os
import sys
from pathlib import Path
 
# Make sure backend modules are importable when run from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
 
from dotenv import load_dotenv
load_dotenv()
 
from database import USE_DB2, DB2_DSN, create_tables
 
 
async def main():
    if not USE_DB2:
        print("[setup_db2] ERROR: DB2_DSN is not set in .env")
        print("[setup_db2] Add DB2_DSN=... to your .env and try again")
        sys.exit(1)
 
    print("[setup_db2] Connecting to Db2...")
    print(f"[setup_db2] DSN: {DB2_DSN[:40]}...")  # truncated for safety
 
    try:
        await create_tables()
        print("[setup_db2] Done — all tables are ready in Db2")
    except Exception as e:
        print(f"[setup_db2] FAILED: {e}")
        sys.exit(1)
 
 
if __name__ == "__main__":
    asyncio.run(main())