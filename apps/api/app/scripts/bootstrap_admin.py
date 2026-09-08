import asyncio

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.identity import Role, User


async def bootstrap_admin() -> None:
    settings = get_settings()
    email = (settings.bootstrap_admin_email or "").strip().lower()
    password = settings.bootstrap_admin_password or ""

    if not email or not password:
        raise SystemExit(
            "Set GRISK_BOOTSTRAP_ADMIN_EMAIL and GRISK_BOOTSTRAP_ADMIN_PASSWORD before running this command."
        )
    if len(password) < 12:
        raise SystemExit("Bootstrap administrator password must be at least 12 characters long.")

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(User).options(selectinload(User.roles)).where(func.lower(User.email) == email)
        )
        if existing is not None:
            print(f"Administrator user already exists: {email}")
            return

        superadmin_role = await session.scalar(select(Role).where(Role.name == "superadmin"))
        if superadmin_role is None:
            raise SystemExit("Role seed is missing. Run `alembic upgrade head` first.")

        user = User(
            email=email,
            full_name=settings.bootstrap_admin_name.strip() or "gRisk Administrator",
            password_hash=hash_password(password),
            is_active=True,
            is_superuser=True,
            roles=[superadmin_role],
        )
        session.add(user)
        await session.commit()
        print(f"Created gRisk bootstrap administrator: {email}")


if __name__ == "__main__":
    asyncio.run(bootstrap_admin())
