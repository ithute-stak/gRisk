import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, SuperUser
from app.core.security import hash_password
from app.models.audit import AuditEvent
from app.models.identity import Role, User
from app.schemas.admin import (
    AdminPasswordReset,
    AdminUserCreate,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdate,
    AuditEventListResponse,
    AuditEventResponse,
    RoleResponse,
)
from app.services.audit import record_audit_event

router = APIRouter(prefix="/admin", tags=["administration"])
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=200)]


def _user_response(user: User) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        roles=sorted(role.name for role in user.roles),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def _get_user_or_404(session: DbSession, user_id: uuid.UUID) -> User:
    result = await session.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def _resolve_roles(session: DbSession, role_names: list[str]) -> list[Role]:
    names = sorted({name.strip().lower() for name in role_names if name.strip()})
    if not names:
        return []
    result = await session.execute(select(Role).where(Role.name.in_(names)).order_by(Role.name))
    roles = list(result.scalars().all())
    found = {role.name for role in roles}
    missing = [name for name in names if name not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown roles: {', '.join(missing)}",
        )
    return roles


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(_: SuperUser, session: DbSession):
    result = await session.execute(select(Role).order_by(Role.name))
    return [
        RoleResponse(id=role.id, name=role.name, description=role.description)
        for role in result.scalars().all()
    ]


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    _: SuperUser,
    session: DbSession,
    page: Page = 1,
    page_size: PageSize = 25,
    q: Search = None,
    active: bool | None = None,
):
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append(or_(User.email.ilike(term), User.full_name.ilike(term)))
    if active is not None:
        filters.append(User.is_active.is_(active))

    total = await session.scalar(select(func.count(User.id)).where(*filters)) or 0
    result = await session.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(*filters)
        .order_by(User.full_name, User.email)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return AdminUserListResponse(
        items=[_user_response(user) for user in result.scalars().all()],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminUserCreate,
    request: Request,
    admin: SuperUser,
    session: DbSession,
):
    email = str(payload.email).strip().lower()
    existing = await session.scalar(select(User.id).where(func.lower(User.email) == email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    roles = await _resolve_roles(session, payload.role_names)
    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
        roles=roles,
    )
    session.add(user)
    await session.flush()
    await record_audit_event(
        session,
        action="admin.user_created",
        entity_type="user",
        entity_id=str(user.id),
        actor_user_id=admin.id,
        details={
            "email": user.email,
            "roles": sorted(role.name for role in roles),
            "is_superuser": user.is_superuser,
        },
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    return _user_response(await _get_user_or_404(session, user.id))


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdate,
    request: Request,
    admin: SuperUser,
    session: DbSession,
):
    user = await _get_user_or_404(session, user_id)
    changes = payload.model_dump(exclude_unset=True)

    if user.id == admin.id and changes.get("is_active") is False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot deactivate your own administrator account",
        )
    if user.id == admin.id and changes.get("is_superuser") is False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot remove your own superuser access",
        )

    if "role_names" in changes:
        user.roles = await _resolve_roles(session, changes.pop("role_names") or [])
    if "full_name" in changes and changes["full_name"] is not None:
        changes["full_name"] = changes["full_name"].strip()
    for field, value in changes.items():
        setattr(user, field, value)

    await record_audit_event(
        session,
        action="admin.user_updated",
        entity_type="user",
        entity_id=str(user.id),
        actor_user_id=admin.id,
        details={
            "changed_fields": sorted(payload.model_fields_set),
            "roles": sorted(role.name for role in user.roles),
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
        },
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    return _user_response(await _get_user_or_404(session, user.id))


@router.post("/users/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_user_password(
    user_id: uuid.UUID,
    payload: AdminPasswordReset,
    request: Request,
    admin: SuperUser,
    session: DbSession,
):
    user = await _get_user_or_404(session, user_id)
    user.password_hash = hash_password(payload.password)
    await record_audit_event(
        session,
        action="admin.password_reset",
        entity_type="user",
        entity_id=str(user.id),
        actor_user_id=admin.id,
        details={"email": user.email},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()


@router.get("/audit", response_model=AuditEventListResponse)
async def list_audit_events(
    _: SuperUser,
    session: DbSession,
    page: Page = 1,
    page_size: PageSize = 50,
    q: Search = None,
    action: str | None = Query(default=None, max_length=100),
    entity_type: str | None = Query(default=None, max_length=100),
    actor_user_id: uuid.UUID | None = None,
):
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append(
            or_(
                AuditEvent.action.ilike(term),
                AuditEvent.entity_type.ilike(term),
                AuditEvent.entity_id.ilike(term),
            )
        )
    if action:
        filters.append(AuditEvent.action == action)
    if entity_type:
        filters.append(AuditEvent.entity_type == entity_type)
    if actor_user_id:
        filters.append(AuditEvent.actor_user_id == actor_user_id)

    total = await session.scalar(select(func.count(AuditEvent.id)).where(*filters)) or 0
    result = await session.execute(
        select(AuditEvent)
        .where(*filters)
        .order_by(AuditEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return AuditEventListResponse(
        items=[
            AuditEventResponse(
                id=event.id,
                actor_user_id=event.actor_user_id,
                action=event.action,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                details=event.details,
                ip_address=event.ip_address,
                created_at=event.created_at,
            )
            for event in result.scalars().all()
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
