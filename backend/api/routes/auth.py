"""
Auth routes: login, me, TOTP setup.
POST /auth/login  -> access_token
GET  /auth/me     -> current user info
POST /auth/totp/setup -> generate TOTP secret + QR URI
"""

from fastapi import APIRouter, Depends
from models.schemas import LoginRequest, LoginResponse, User, TokenPayload
from core.security import (
    verify_password, create_access_token,
    generate_totp_secret, get_totp_uri, verify_totp,
)
from core.exceptions import InvalidCredentials, InvalidTOTP
from core import database as db
from api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """
    Authenticate with username + password (+ optional TOTP code).
    Returns a JWT access token valid for 8 hours.
    """
    user = await db.fetch_one(
        "SELECT * FROM users WHERE username = ?", (body.username,)
    )
    if not user:
        raise InvalidCredentials()

    if not verify_password(body.password, user["password_hash"]):
        raise InvalidCredentials()

    # TOTP check (if enabled for this user)
    if user["totp_enabled"]:
        if not body.totp_code:
            raise InvalidCredentials()
        if not verify_totp(user["totp_secret"], body.totp_code):
            raise InvalidTOTP()

    token = create_access_token(user["username"], user["role"])
    return LoginResponse(
        access_token = token,
        role         = user["role"],
        username     = user["username"],
    )


@router.get("/me", response_model=dict)
async def get_me(user: TokenPayload = Depends(get_current_user)):
    """Return the currently authenticated user's info."""
    return {"username": user.sub, "role": user.role}


@router.post("/totp/setup", response_model=dict)
async def setup_totp(user: TokenPayload = Depends(get_current_user)):
    """
    Generate a new TOTP secret for the current user.
    Returns the secret + an otpauth:// URI for QR scanning.
    Admin can call this on behalf of users; user can also self-enroll.
    """
    secret = generate_totp_secret()
    uri    = get_totp_uri(secret, user.sub)

    # Save secret (not yet enabled -- user must verify a code first)
    await db.execute(
        "UPDATE users SET totp_secret = ? WHERE username = ?",
        (secret, user.sub)
    )
    return {"totp_secret": secret, "totp_uri": uri}


@router.post("/totp/verify", response_model=dict)
async def verify_totp_setup(
    body: dict,
    user: TokenPayload = Depends(get_current_user),
):
    """
    Verify the user's TOTP code and enable TOTP for their account.
    Body: {"code": "123456"}
    """
    db_user = await db.fetch_one("SELECT totp_secret FROM users WHERE username=?", (user.sub,))
    if not db_user or not db_user["totp_secret"]:
        return {"error": "TOTP secret not set up yet. Call /auth/totp/setup first."}

    if not verify_totp(db_user["totp_secret"], body.get("code", "")):
        raise InvalidTOTP()

    await db.execute(
        "UPDATE users SET totp_enabled = 1 WHERE username = ?", (user.sub,)
    )
    return {"message": "TOTP enabled successfully"}
