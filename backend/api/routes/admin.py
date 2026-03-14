"""
Admin routes (ADMIN role only).
GET  /admin/users          -> list all users
POST /admin/users          -> create user
DELETE /admin/users/{uid}  -> delete user
GET  /admin/stats          -> system statistics
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends
from models.schemas import TokenPayload
from core.security import hash_password
from core import database as db
from core.exceptions import Forbidden
from api.deps import require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list)
async def list_users(user: TokenPayload = Depends(require_admin)):
    """List all users (passwords redacted)."""
    rows = await db.fetch_all(
        "SELECT user_id, username, role, totp_enabled, created_at FROM users ORDER BY created_at"
    )
    return rows


@router.post("/users", response_model=dict)
async def create_user(
    body: dict,
    user: TokenPayload = Depends(require_admin),
):
    """
    Create a new user.
    Body: {"username": "...", "password": "...", "role": "adjuster|investigator|admin"}
    """
    username = body.get("username", "").strip()
    password = body.get("password", "")
    role     = body.get("role", "adjuster")

    if not username or not password:
        return {"error": "username and password required"}
    if role not in ("adjuster", "investigator", "admin"):
        return {"error": "role must be adjuster, investigator, or admin"}

    existing = await db.fetch_one("SELECT user_id FROM users WHERE username=?", (username,))
    if existing:
        return {"error": f"Username '{username}' already exists"}

    user_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO users (user_id, username, password_hash, role, totp_enabled, created_at) VALUES (?,?,?,?,0,?)",
        (user_id, username, hash_password(password), role, datetime.utcnow().isoformat()),
    )
    return {"user_id": user_id, "username": username, "role": role}


@router.delete("/users/{username}", response_model=dict)
async def delete_user(
    username: str,
    user: TokenPayload = Depends(require_admin),
):
    """Delete a user. Cannot delete yourself."""
    if username == user.sub:
        return {"error": "Cannot delete your own account"}
    await db.execute("DELETE FROM users WHERE username=?", (username,))
    return {"message": f"User '{username}' deleted"}


@router.get("/stats", response_model=dict)
async def get_stats(user: TokenPayload = Depends(require_admin)):
    """System statistics for the admin dashboard."""
    total_claims = await db.fetch_one("SELECT COUNT(*) as cnt FROM claims")
    flagged      = await db.fetch_one("SELECT COUNT(*) as cnt FROM claims WHERE status='flagged'")
    approved     = await db.fetch_one("SELECT COUNT(*) as cnt FROM claims WHERE status='approved'")
    pending      = await db.fetch_one("SELECT COUNT(*) as cnt FROM claims WHERE status='pending'")
    entities     = await db.fetch_one("SELECT COUNT(*) as cnt FROM entities")
    inferences   = await db.fetch_one("SELECT COUNT(*) as cnt FROM inference_log")
    critical     = await db.fetch_one("SELECT COUNT(*) as cnt FROM claims WHERE risk_level='CRITICAL'")

    return {
        "total_claims": total_claims["cnt"] if total_claims else 0,
        "flagged":      flagged["cnt"]      if flagged else 0,
        "approved":     approved["cnt"]     if approved else 0,
        "pending":      pending["cnt"]      if pending else 0,
        "entities":     entities["cnt"]     if entities else 0,
        "inferences":   inferences["cnt"]   if inferences else 0,
        "critical":     critical["cnt"]     if critical else 0,
    }
