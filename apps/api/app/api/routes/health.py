from fastapi import APIRouter
from sqlalchemy import text

from app.core.redis import redis_client
from app.db.session import AsyncSessionLocal

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health() -> dict:
    db_ok = False
    redis_ok = False

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    try:
        redis_ok = bool(await redis_client.ping())
    except Exception:
        redis_ok = False

    status = "ok" if db_ok and redis_ok else "degraded"
    return {
        "status": status,
        "services": {
            "api": True,
            "postgres": db_ok,
            "redis": redis_ok,
        },
    }
