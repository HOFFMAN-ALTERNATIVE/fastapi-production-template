import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

TokenType = Literal["access", "refresh"]
_hasher = PasswordHash.recommended()  # Argon2id


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _hasher.verify(password, hashed)


def create_token(subject: str, token_type: TokenType) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    ttl = (
        timedelta(minutes=s.access_token_ttl_minutes)
        if token_type == "access"
        else timedelta(days=s.refresh_token_ttl_days)
    )
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + ttl,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, s.jwt_secret.get_secret_value(), algorithm=s.jwt_algorithm)


class InvalidTokenError(Exception):
    pass


def decode_token(token: str, expected: TokenType) -> dict[str, Any]:
    s = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            s.jwt_secret.get_secret_value(),
            algorithms=[s.jwt_algorithm],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.PyJWTError as e:
        raise InvalidTokenError(str(e)) from e
    if payload.get("type") != expected:
        raise InvalidTokenError("wrong token type")
    return payload
