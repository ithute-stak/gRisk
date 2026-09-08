from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.claims import router as claims_router
from app.api.routes.customers import router as customers_router
from app.api.routes.finance import router as finance_router
from app.api.routes.guarantees import router as guarantees_router
from app.api.routes.health import router as health_router
from app.api.routes.insurance import router as insurance_router
from app.api.routes.medical import router as medical_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.portal import router as portal_router
from app.api.routes.reports import router as reports_router
from app.api.routes.risk import router as risk_router
from app.core.config import get_settings
from app.core.redis import redis_client
from app.realtime.manager import manager

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await redis_client.aclose()


app = FastAPI(
    title=settings.app_name,
    version="0.9.0",
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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
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
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(portal_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")


@app.get("/api/v1")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.9.0",
        "environment": settings.environment,
    }


@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str) -> None:
    await manager.connect(channel, websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            await manager.broadcast(
                channel,
                {
                    "channel": channel,
                    "event": "message",
                    "data": payload,
                },
            )
    except WebSocketDisconnect:
        manager.disconnect(channel, websocket)
