import os

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.identity import Role, User

LOCAL_ADMIN_EMAIL = "thekoetlisi@ithute.co.ls"
LOCAL_ADMIN_NAME = "Local gRisk Administrator"
# Local-development-only Argon2id hash for the requested test password.
# The plaintext password is intentionally not committed to the repository.
LOCAL_ADMIN_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$2L8dJYF4YQjtMF2m2ueVKg$"
    "tmdvmSV0QaOWtH4yNdpxR6AHz5mavTVOonD0u7se7fs"
)


def _local_bootstrap_enabled() -> bool:
    return os.getenv("GRISK_ALLOW_LOCAL_DEFAULT_ADMIN", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


async def bootstrap_local_admin() -> None:
    settings = get_settings()
    if settings.environment.lower() == "production":
        raise SystemExit("Local default administrator bootstrap is disabled in production.")
    if not _local_bootstrap_enabled():
        raise SystemExit(
            "Set GRISK_ALLOW_LOCAL_DEFAULT_ADMIN=true to run the local default administrator bootstrap."
        )

    async with AsyncSessionLocal() as session:
        superadmin_role = await session.scalar(select(Role).where(Role.name == "superadmin"))
        if superadmin_role is None:
            raise SystemExit("Role seed is missing. Run `alembic upgrade head` first.")

        user = await session.scalar(
            select(User)
            .options(selectinload(User.roles))
            .where(func.lower(User.email) == LOCAL_ADMIN_EMAIL)
        )

        if user is None:
            user = User(
                email=LOCAL_ADMIN_EMAIL,
                full_name=LOCAL_ADMIN_NAME,
                password_hash=LOCAL_ADMIN_PASSWORD_HASH,
                is_active=True,
                is_superuser=True,
                roles=[superadmin_role],
            )
            session.add(user)
            action = "Created"
        else:
            user.is_active = True
            user.is_superuser = True
            user.password_hash = LOCAL_ADMIN_PASSWORD_HASH
            if superadmin_role not in user.roles:
                user.roles.append(superadmin_role)
            action = "Refreshed"

        await session.commit()
        print(f"{action} local gRisk administrator: {LOCAL_ADMIN_EMAIL}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(bootstrap_local_admin())
