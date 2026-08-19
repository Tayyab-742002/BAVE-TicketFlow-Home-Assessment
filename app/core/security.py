import uuid
from datetime import timedelta
from enum import Enum

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.time import utcnow

settings = get_settings()
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def _create_token(
    subject: uuid.UUID, role: str, token_type: TokenType, expires_delta: timedelta
) -> str:
    now = utcnow()
    payload = {
        "sub": str(subject),
        "role": role,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    return _create_token(
        user_id, role, TokenType.ACCESS, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(user_id: uuid.UUID, role: str) -> str:
    return _create_token(
        user_id, role, TokenType.REFRESH, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


def decode_token(token: str) -> dict:
    """Raises jwt.ExpiredSignatureError / jwt.InvalidTokenError on failure."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
