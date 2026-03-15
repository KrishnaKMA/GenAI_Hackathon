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
    claim_stats = await db.fetch_one(
        """SELECT
               COUNT(*) AS total_claims,
               SUM(CASE WHEN status = 'flagged' THEN 1 ELSE 0 END) AS flagged,
               SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved,
               SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
               SUM(CASE WHEN risk_level = 'CRITICAL' THEN 1 ELSE 0 END) AS critical
           FROM claims"""
    )
    side_stats = await db.fetch_one(
        """SELECT
               (SELECT COUNT(*) FROM entities) AS entities,
               (SELECT COUNT(*) FROM inference_log) AS inferences
        FROM SYSIBM.SYSDUMMY1"""
        if db.USE_DB2 else
        """SELECT
               (SELECT COUNT(*) FROM entities) AS entities,
               (SELECT COUNT(*) FROM inference_log) AS inferences"""
    )

    return {
        "total_claims": claim_stats["total_claims"] if claim_stats else 0,
        "flagged":      (claim_stats["flagged"] or 0) if claim_stats else 0,
        "approved":     (claim_stats["approved"] or 0) if claim_stats else 0,
        "pending":      (claim_stats["pending"] or 0) if claim_stats else 0,
        "entities":     (side_stats["entities"] or 0) if side_stats else 0,
        "inferences":   (side_stats["inferences"] or 0) if side_stats else 0,
        "critical":     (claim_stats["critical"] or 0) if claim_stats else 0,
    }
