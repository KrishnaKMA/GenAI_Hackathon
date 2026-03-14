"""
ClaimShield FastAPI Application Entry Point
==========================================

Run: uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs

Architecture:
  - All IBM calls -> services/ibm_interface.py  (Teammate B edits)
  - All ML calls  -> services/ml_interface.py   (Teammate A edits)
  - Everything else -> this file + api/routes/  (Krishna)
"""

import os
import uuid
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core import database as db
from core.security import hash_password
from services.ml_interface import USE_MOCK as USE_MOCK_ML
from services.ibm_interface import USE_MOCK as USE_MOCK_IBM

from api.routes import auth, claims, analysis, agent, admin


# ─────────────────────────────────────────────────────────
# STARTUP / SHUTDOWN
# ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables and seed demo users on startup."""
    await db.create_tables()
    await _seed_demo_users()
    print("\n==========================================")
    print("  ClaimShield API running at :8000")
    print(f"  ML  mode: {'MOCK' if USE_MOCK_ML  else 'REAL'}")
    print(f"  IBM mode: {'MOCK' if USE_MOCK_IBM else 'REAL'}")
    print("  Docs: http://localhost:8000/docs")
    print("==========================================\n")
    yield
    # Shutdown (nothing to clean up for SQLite)


async def _seed_demo_users():
    """Create demo users if they don't already exist."""
    demo_users = [
        ("admin",        "admin123", "admin"),
        ("adjuster1",    "pass123",  "adjuster"),
        ("investigator1","pass123",  "investigator"),
    ]
    for username, password, role in demo_users:
        existing = await db.fetch_one("SELECT user_id FROM users WHERE username=?", (username,))
        if not existing:
            await db.execute(
                "INSERT INTO users (user_id, username, password_hash, role, totp_enabled, created_at) "
                "VALUES (?,?,?,?,0,?)",
                (str(uuid.uuid4()), username, hash_password(password), role, datetime.utcnow().isoformat()),
            )
    print("[SEED] Demo users ready: admin/admin123, adjuster1/pass123, investigator1/pass123")


# ─────────────────────────────────────────────────────────
# APP FACTORY
# ─────────────────────────────────────────────────────────

app = FastAPI(
    title        = "ClaimShield API",
    description  = "AI-powered insurance fraud detection using GNN + IBM watsonx.ai",
    version      = "1.0.0",
    docs_url     = "/docs",
    redoc_url    = "/redoc",
    lifespan     = lifespan,
)

# ─────────────────────────────────────────────────────────
# CORS -- allow frontend dev server
# ─────────────────────────────────────────────────────────
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins     = [FRONTEND_URL, "http://localhost:3000", "http://localhost:5174"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ─────────────────────────────────────────────────────────
# ROUTERS
# ─────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(claims.router)
app.include_router(analysis.router)
app.include_router(agent.router)
app.include_router(admin.router)


# ─────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def health_check():
    """Health check -- always returns 200 OK."""
    return {
        "status":   "ok",
        "mock_ml":  USE_MOCK_ML,
        "mock_ibm": USE_MOCK_IBM,
        "version":  "1.0.0",
        "docs":     "http://localhost:8000/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
