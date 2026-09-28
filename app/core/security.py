import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-development-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", "5"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(mobile_number: str, otp: str) -> str:
    return hashlib.sha256(f"{mobile_number}:{otp}:{SECRET_KEY}".encode()).hexdigest()


def create_access_token(user_id: int) -> str:
    return jwt.encode({"sub": str(user_id), "type": "access", "exp": utc_now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)}, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    token_id = str(uuid.uuid4())
    expires_at = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    token = jwt.encode({"sub": str(user_id), "jti": token_id, "type": "refresh", "exp": expires_at}, SECRET_KEY, algorithm=ALGORITHM)
    return token, token_id, expires_at
