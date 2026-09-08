from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.redis import redis_client
from app.db.session import AsyncSessionLocal

router = APIRouter(prefix="/health", tags=["health"])


async def _service_status() -> tuple[bool, bool]:
    db_ok = False
    redis_ok = False

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except SQLAlchemyError:
        db_ok = False

    try:
        redis_ok = bool(await redis_client.ping())
    except RedisError:
        redis_ok = False

    return db_ok, redis_ok


def _payload(db_ok: bool, redis_ok: bool) -> dict:
    return {
        "status": "ok" if db_ok and redis_ok else "degraded",
        "services": {
            "api": True,
            "postgres": db_ok,
            "redis": redis_ok,
        },
    }


@router.get("")
async def health() -> dict:
    db_ok, redis_ok = await _service_status()
    return _payload(db_ok, redis_ok)


@router.get("/live")
async def liveness() -> dict:
    return {"status": "ok", "service": "api"}


@router.get("/ready")
async def readiness():
    db_ok, redis_ok = await _service_status()
    payload = _payload(db_ok, redis_ok)
    return JSONResponse(
        content=payload,
        status_code=(
            status.HTTP_200_OK
            if db_ok and redis_ok
            else status.HTTP_503_SERVICE_UNAVAILABLE
        ),
    )
