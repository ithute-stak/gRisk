import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models.identity import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]
AccessToken = Annotated[str, Depends(oauth2_scheme)]

STAFF_ROLE_NAMES = {
    "superadmin",
    "admin",
    "broker",
    "claims",
    "medical",
    "finance",
    "risk",
    "viewer",
}
PORTAL_SAFE_PREFIXES = (
    "/api/v1/auth/me",
    "/api/v1/portal",
    "/api/v1/notifications",
)


async def get_current_user(token: AccessToken, session: DbSession, request: Request) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id = uuid.UUID(decode_access_token(token))
    except (TokenError, ValueError) as exc:
        raise credentials_error from exc

    result = await session.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_error

    role_names = {role.name for role in user.roles}
    is_staff = user.is_superuser or bool(role_names & STAFF_ROLE_NAMES)
    if not is_staff and not request.url.path.startswith(PORTAL_SAFE_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer portal accounts cannot access internal operational APIs",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_superuser(user: CurrentUser) -> User:
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return user


SuperUser = Annotated[User, Depends(require_superuser)]
