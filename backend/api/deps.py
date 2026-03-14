"""
FastAPI dependency injection helpers.
Use these in route function signatures for auth.
"""

from fastapi import Depends, Header
from core.security import verify_token
from core.exceptions import Unauthorized, Forbidden
from models.schemas import TokenPayload


async def get_current_user(authorization: str = Header(...)) -> TokenPayload:
    """Extract and verify JWT from Authorization: Bearer <token> header."""
    if not authorization.startswith("Bearer "):
        raise Unauthorized("Authorization header must start with 'Bearer '")
    token = authorization.removeprefix("Bearer ").strip()
    payload = verify_token(token)
    if not payload:
        raise Unauthorized()
    return payload


async def require_adjuster(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    if user.role not in ("adjuster", "investigator", "admin"):
        raise Forbidden()
    return user


async def require_investigator(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    if user.role not in ("investigator", "admin"):
        raise Forbidden("Investigator or Admin role required")
    return user


async def require_admin(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    if user.role != "admin":
        raise Forbidden("Admin role required")
    return user
