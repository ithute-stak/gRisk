import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.portal import CustomerPortalAccess


async def notify_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    message: str,
    category: str = "general",
    customer_id: uuid.UUID | None = None,
    action_url: str | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        customer_id=customer_id,
        category=category,
        title=title,
        message=message,
        action_url=action_url,
    )
    session.add(notification)
    return notification


async def notify_customer_portal_users(
    session: AsyncSession,
    *,
    customer_id: uuid.UUID,
    title: str,
    message: str,
    category: str = "general",
    action_url: str | None = None,
) -> list[Notification]:
    result = await session.execute(
        select(CustomerPortalAccess.user_id).where(
            CustomerPortalAccess.customer_id == customer_id,
            CustomerPortalAccess.is_active.is_(True),
        )
    )
    notifications = []
    for user_id in result.scalars().all():
        notifications.append(
            await notify_user(
                session,
                user_id=user_id,
                customer_id=customer_id,
                title=title,
                message=message,
                category=category,
                action_url=action_url,
            )
        )
    return notifications
