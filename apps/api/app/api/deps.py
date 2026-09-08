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
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
WRITE_ROLE_BY_PREFIX: tuple[tuple[str, set[str]], ...] = (
    ("/api/v1/customers", {"admin", "broker"}),
    ("/api/v1/insurance", {"admin", "broker"}),
    ("/api/v1/claims", {"admin", "broker", "claims"}),
    ("/api/v1/medical", {"admin", "medical"}),
    ("/api/v1/guarantees", {"admin", "broker", "risk"}),
    ("/api/v1/risk", {"admin", "risk"}),
    ("/api/v1/finance", {"admin", "finance"}),
    ("/api/v1/documents", {"admin", "broker", "claims", "medical", "finance", "risk"}),
    ("/api/v1/partners", {"admin", "broker", "risk"}),
)


def _can_write_operational_path(path: str, role_names: set[str]) -> bool:
    for prefix, required_roles in WRITE_ROLE_BY_PREFIX:
        if path.startswith(prefix):
            return bool(role_names & required_roles)
    return True


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
    if not is_staff:
        if not request.url.path.startswith(PORTAL_SAFE_PREFIXES):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customer portal accounts cannot access internal operational APIs",
            )
        return user

    if user.is_superuser:
        return user

    if request.method not in SAFE_METHODS:
        if role_names == {"viewer"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewer accounts have read-only access",
            )
        if not _can_write_operational_path(request.url.path, role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role does not permit this operational change",
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
