import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from redis.exceptions import RedisError
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.redis import redis_client
from app.core.security import create_access_token, verify_password
from app.models.identity import User
from app.schemas.auth import TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])
OAuth2Form = Annotated[OAuth2PasswordRequestForm, Depends()]
settings = get_settings()


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        roles=sorted(role.name for role in user.roles),
    )


def _login_rate_key(request: Request, email: str) -> str:
    client_ip = request.client.host if request.client else "unknown"
    email_hash = hashlib.sha256(email.encode("utf-8")).hexdigest()[:20]
    return f"grisk:auth:login:{client_ip}:{email_hash}"


async def _enforce_login_rate_limit(request: Request, email: str) -> str:
    key = _login_rate_key(request, email)
    try:
        attempts = int(await redis_client.incr(key))
        if attempts == 1:
            await redis_client.expire(key, settings.login_rate_limit_window_seconds)
        if attempts > settings.login_rate_limit_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again later.",
            )
    except RedisError:
        # Authentication remains available if Redis is temporarily unavailable.
        pass
    return key


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, form: OAuth2Form, session: DbSession) -> TokenResponse:
    email = form.username.strip().lower()
    rate_key = await _enforce_login_rate_limit(request, email)
    result = await session.execute(
        select(User).options(selectinload(User.roles)).where(func.lower(User.email) == email)
    )
    user = result.scalar_one_or_none()

    if user is None or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        await redis_client.delete(rate_key)
    except RedisError:
        pass

    roles = sorted(role.name for role in user.roles)
    token = create_access_token(
        str(user.id),
        claims={
            "email": user.email,
            "name": user.full_name,
            "roles": roles,
            "is_superuser": user.is_superuser,
        },
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return _to_user_response(user)
