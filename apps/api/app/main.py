from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
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
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")


@app.get("/api/v1")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.1.0",
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
