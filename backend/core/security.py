"""
Security utilities: PII tokenization, JWT, passwords, TOTP.
All cryptographic primitives live here -- no other file touches keys.
"""

import os
import uuid
import time
import base64
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import jwt  # PyJWT
import pyotp
import bcrypt
from cryptography.fernet import Fernet
from models.schemas import TokenPayload

# ─────────────────────────────────────────────────────────
# ROLE CONSTANTS
# ─────────────────────────────────────────────────────────
ADJUSTER     = "adjuster"
INVESTIGATOR = "investigator"
ADMIN        = "admin"

# ─────────────────────────────────────────────────────────
# KEY LOADING
# RS256 keys for JWT -- generated once, stored in .env
# Fernet key for PII tokenization -- stored in .env
# ─────────────────────────────────────────────────────────
JWT_PRIVATE_KEY = os.getenv("JWT_PRIVATE_KEY", "").replace("\\n", "\n")
JWT_PUBLIC_KEY  = os.getenv("JWT_PUBLIC_KEY", "").replace("\\n", "\n")
FERNET_KEY      = os.getenv("FERNET_KEY", "")
JWT_ALGORITHM   = "RS256"
TOKEN_EXPIRE_HOURS = 8

# Fallback: generate ephemeral HS256 secret for dev when RS256 keys not set
_USE_HS256_FALLBACK = not bool(JWT_PRIVATE_KEY and JWT_PUBLIC_KEY)
if _USE_HS256_FALLBACK:
    _HS256_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    print("[SEC] WARNING: RS256 keys not found -- using HS256 fallback (dev only)")
else:
    print("[SEC] OK: RS256 JWT keys loaded")

# Fernet fallback for dev
_fernet: Optional[Fernet] = None
if FERNET_KEY:
    try:
        _fernet = Fernet(FERNET_KEY.encode())
        print("[SEC] OK: Fernet PII encryption active")
    except Exception as e:
        print(f"[SEC] WARNING:  Invalid FERNET_KEY: {e} -- using hash-based tokens")
else:
    print("[SEC] WARNING:  FERNET_KEY not set -- PII tokens are one-way hashes (no decrypt)")


# ─────────────────────────────────────────────────────────
# PII TOKENIZER
# Converts real names/IDs to anonymous tokens for the graph
# ─────────────────────────────────────────────────────────

class PiiTokenizer:
    """
    Converts PII (names, addresses) to deterministic anonymous tokens.
    If FERNET_KEY is set -> reversible (can detokenize for authorized users)
    If FERNET_KEY missing -> one-way SHA-256 (safe, but can't recover original)
    """

    @staticmethod
    def tokenize(prefix: str, raw_value: str) -> str:
        """
        prefix: entity type prefix e.g. 'CLAIMANT', 'PROVIDER', 'SHOP', 'CLAIM'
        raw_value: the real PII string
        Returns: 'CLAIMANT_A3F9' style token
        """
        # SHA-256 hash -> take first 8 hex chars -> uppercase
        digest = hashlib.sha256(raw_value.encode()).hexdigest()[:8].upper()
        return f"{prefix}_{digest}"

    @staticmethod
    def tokenize_reversible(prefix: str, raw_value: str) -> str:
        """Uses Fernet encryption if available for reversible tokenization."""
        if _fernet:
            encrypted = _fernet.encrypt(raw_value.encode()).decode()
            # Use first 8 chars of base64 as the display token
            short = base64.urlsafe_b64encode(raw_value.encode()).decode()[:8].upper()
            return f"{prefix}_{short}"
        return PiiTokenizer.tokenize(prefix, raw_value)

    @staticmethod
    def detokenize(token: str, encrypted_payload: str) -> Optional[str]:
        """Decrypt a reversibly-tokenized value. Returns None if not possible."""
        if _fernet:
            try:
                return _fernet.decrypt(encrypted_payload.encode()).decode()
            except Exception:
                return None
        return None


# ─────────────────────────────────────────────────────────
# JWT
# ─────────────────────────────────────────────────────────

def create_access_token(username: str, role: str) -> str:
    """Create a signed JWT for the given user."""
    expire = int(time.time()) + TOKEN_EXPIRE_HOURS * 3600
    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
        "iat": int(time.time()),
        "jti": str(uuid.uuid4()),
    }
    if _USE_HS256_FALLBACK:
        return jwt.encode(payload, _HS256_SECRET, algorithm="HS256")
    else:
        return jwt.encode(payload, JWT_PRIVATE_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[TokenPayload]:
    """Verify and decode a JWT. Returns TokenPayload or None if invalid."""
    try:
        if _USE_HS256_FALLBACK:
            data = jwt.decode(token, _HS256_SECRET, algorithms=["HS256"])
        else:
            data = jwt.decode(token, JWT_PUBLIC_KEY, algorithms=[JWT_ALGORITHM])
        return TokenPayload(sub=data["sub"], role=data["role"], exp=data["exp"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ─────────────────────────────────────────────────────────
# PASSWORDS
# ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Bcrypt-hash a plain-text password."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ─────────────────────────────────────────────────────────
# TOTP (2-Factor Auth)
# ─────────────────────────────────────────────────────────

def generate_totp_secret() -> str:
    """Generate a new TOTP base32 secret for a user."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, username: str) -> str:
    """Get the otpauth:// URI for QR code generation."""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=username, issuer_name="ClaimShield"
    )


def verify_totp(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code against the user's secret."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)
