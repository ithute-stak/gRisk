from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings

settings = get_settings()
password_hasher = PasswordHash.recommended()


class TokenError(ValueError):
    pass


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(
    subject: str,
    expires_minutes: int | None = None,
    claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expires,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    if claims:
        protected = {"sub", "iat", "exp", "iss", "aud"}
        payload.update({key: value for key, value in claims.items() if key not in protected})
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except InvalidTokenError as exc:
        raise TokenError("Invalid or expired access token") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise TokenError("Access token is missing a subject")
    return subject
