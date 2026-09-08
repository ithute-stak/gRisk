import json
import logging
import uuid
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import STAFF_ROLE_NAMES
from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.claims import router as claims_router
from app.api.routes.customers import router as customers_router
from app.api.routes.document_studio import router as document_studio_router
from app.api.routes.documents import router as documents_router
from app.api.routes.finance import router as finance_router
from app.api.routes.guarantees import router as guarantees_router
from app.api.routes.health import router as health_router
from app.api.routes.insurance import router as insurance_router
from app.api.routes.medical import router as medical_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.partners import router as partners_router
from app.api.routes.portal import router as portal_router
from app.api.routes.reports import router as reports_router
from app.api.routes.risk import router as risk_router
from app.core.config import get_settings
from app.core.redis import redis_client
from app.core.security import TokenError, decode_access_token
from app.db.session import AsyncSessionLocal
from app.models.identity import User
from app.realtime.manager import manager

settings = get_settings()
request_logger = logging.getLogger("grisk.request")
request_logger.setLevel(logging.INFO)
SESSION_COOKIE_NAME = "grisk_session"


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await redis_client.aclose()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _request_log(event: str, request_id: str, request: Request, **values) -> str:
    return json.dumps(
        {
            "event": event,
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            **values,
        },
        separators=(",", ":"),
        default=str,
    )


@app.middleware("http")
async def operational_middleware(request: Request, call_next):
    request_id = uuid.uuid4().hex
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((perf_counter() - started) * 1000, 2)
        request_logger.exception(
            _request_log("request_failed", request_id, request, duration_ms=duration_ms)
        )
        raise

    duration_ms = round((perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    request_logger.info(
        _request_log(
            "request_completed",
            request_id,
            request,
            status=response.status_code,
            duration_ms=duration_ms,
        )
    )
    return response


app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(insurance_router, prefix="/api/v1")
app.include_router(claims_router, prefix="/api/v1")
app.include_router(medical_router, prefix="/api/v1")
app.include_router(guarantees_router, prefix="/api/v1")
app.include_router(risk_router, prefix="/api/v1")
app.include_router(finance_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(document_studio_router, prefix="/api/v1")
app.include_router(partners_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(portal_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/api/v1")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "environment": settings.environment,
    }


def _websocket_origin_allowed(websocket: WebSocket) -> bool:
    if settings.environment.lower() != "production":
        return True
    origin = websocket.headers.get("origin")
    return bool(origin and origin in settings.cors_origin_list)


async def _websocket_user(websocket: WebSocket) -> User | None:
    token = websocket.cookies.get(SESSION_COOKIE_NAME)
    if not token and settings.environment.lower() != "production":
        # Development-only compatibility for non-browser WebSocket clients.
        token = websocket.query_params.get("access_token")
    if not token:
        return None
    try:
        user_id = uuid.UUID(decode_access_token(token))
    except (TokenError, ValueError):
        return None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).options(selectinload(User.roles)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return None
        session.expunge(user)
        return user


def _websocket_channel_allowed(user: User, channel: str) -> bool:
    role_names = {role.name for role in user.roles}
    is_staff = user.is_superuser or bool(role_names & STAFF_ROLE_NAMES)
    if is_staff:
        return True
    return channel == f"notifications:{user.id}"


@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str) -> None:
    if not _websocket_origin_allowed(websocket):
        await websocket.close(code=4403, reason="Origin not allowed")
        return

    user = await _websocket_user(websocket)
    if user is None:
        await websocket.close(code=4401, reason="Authentication required")
        return
    if not _websocket_channel_allowed(user, channel):
        await websocket.close(code=4403, reason="Channel access denied")
        return

    await manager.connect(channel, websocket)
    try:
        while True:
            # Realtime channels are server-published. Client messages are only
            # consumed to detect disconnects and are never rebroadcast.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(channel, websocket)
