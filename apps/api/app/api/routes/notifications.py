import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, SuperUser
from app.models.identity import User
from app.models.notification import Notification
from app.realtime.manager import manager
from app.schemas.notification import (
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
)
from app.services.notifications import notify_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    user: CurrentUser,
    session: DbSession,
    notification_status: str | None = Query(default=None, max_length=20),
    category: str | None = Query(default=None, max_length=50),
    customer_id: uuid.UUID | None = None,
):
    filters = [Notification.user_id == user.id]
    if notification_status:
        filters.append(Notification.status == notification_status)
    if category:
        filters.append(Notification.category == category)
    if customer_id:
        filters.append(Notification.customer_id == customer_id)
    result = await session.execute(
        select(Notification).where(*filters).order_by(Notification.created_at.desc()).limit(200)
    )
    items = list(result.scalars().all())
    total = await session.scalar(select(func.count(Notification.id)).where(*filters)) or 0
    unread = await session.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.status == "unread",
        )
    ) or 0
    return NotificationListResponse(items=items, total=total, unread=unread)


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(payload: NotificationCreate, _: SuperUser, session: DbSession):
    target = await session.get(User, payload.user_id)
    if target is None or not target.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active target user not found")
    notification = await notify_user(
        session,
        user_id=payload.user_id,
        customer_id=payload.customer_id,
        category=payload.category,
        title=payload.title,
        message=payload.message,
        action_url=payload.action_url,
    )
    await session.commit()
    await session.refresh(notification)
    await manager.broadcast(
        f"notifications:{notification.user_id}",
        {
            "channel": f"notifications:{notification.user_id}",
            "event": "notification.created",
            "data": {"id": str(notification.id), "title": notification.title},
        },
    )
    return notification


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
):
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.status = "read"
    notification.read_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(notification)
    return notification


@router.patch("/{notification_id}/archive", response_model=NotificationResponse)
async def archive_notification(
    notification_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
):
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.status = "archived"
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(notification)
    return notification


@router.patch("/read-all", response_model=NotificationListResponse)
async def mark_all_read(user: CurrentUser, session: DbSession):
    result = await session.execute(
        select(Notification).where(
            Notification.user_id == user.id,
            Notification.status == "unread",
        )
    )
    now = datetime.now(UTC)
    for notification in result.scalars().all():
        notification.status = "read"
        notification.read_at = now
    await session.commit()
    return await list_notifications(user, session, None, None, None)
