"""API Gateway (порт 8000) — REST + WebSocket + JWT (Фаза 9).

Единая точка входа для фронтенда: REST ``/api/v1/*`` (исторические данные из
TimescaleDB и баланс из Redis), WebSocket ``/ws`` (real-time), JWT-аутентификация,
CORS, rate limiting, Prometheus метрики.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

import websocket as ws_module
from auth import ensure_default_user
from rate_limiter import rest_limiter
from redis_client import close_redis, get_redis
from routers import auth as auth_router
from routers import (
    analytics, balance, exchanges, killswitch, opportunities, prices, stats, trades,
)
from shared.config import settings
from shared.db import close_db_pool, get_db_pool

log = structlog.get_logger()
SERVICE = "api-gateway"

_requests_counter = Counter("http_requests_total", "Всего HTTP-запросов", ["path"])
_ws_clients_gauge = Gauge("ws_clients_active", "Активные WebSocket-клиенты")

_state: dict = {"redis": None, "tasks": []}


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await get_db_pool()
    await ensure_default_user(pool)
    _state["redis"] = await get_redis()
    _state["tasks"] = [
        asyncio.create_task(ws_module.events_broadcaster(), name="ws_events"),
        asyncio.create_task(ws_module.prices_broadcaster(), name="ws_prices"),
    ]
    log.info("api_gateway_up")
    try:
        yield
    finally:
        for task in _state["tasks"]:
            task.cancel()
        await asyncio.gather(*_state["tasks"], return_exceptions=True)
        await close_redis()
        await close_db_pool()
        log.info("api_gateway_down")


app = FastAPI(title="Crypto Arbitrage API Gateway", version="1.0", lifespan=lifespan)

ALLOWED_ORIGINS = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _with_cors(request: Request, response: JSONResponse) -> JSONResponse:
    """Проставить CORS-заголовки на ответ, сформированный внешним middleware
    (CORSMiddleware его не увидит — он внутри стека)."""
    origin = request.headers.get("origin")
    if origin and (origin in ALLOWED_ORIGINS or "*" in ALLOWED_ORIGINS):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        client_ip = request.client.host if request.client else "unknown"
        if not rest_limiter.check(client_ip):
            return _with_cors(request, JSONResponse({"detail": "Rate limit exceeded"}, status_code=429))
    _requests_counter.labels(path=request.url.path).inc()
    try:
        return await call_next(request)
    except Exception as err:  # noqa: BLE001 — единый JSON-ответ на 500 (+ CORS)
        log.error("unhandled_error", path=request.url.path, error=str(err))
        return _with_cors(request, JSONResponse({"detail": "internal server error"}, status_code=500))


for r in (auth_router.router, prices.router, opportunities.router,
          trades.router, balance.router, exchanges.router, stats.router,
          analytics.router, killswitch.router):
    app.include_router(r)
app.include_router(ws_module.router)


@app.get("/health")
async def health() -> dict:
    db_ok = redis_ok = False
    try:
        pool = await get_db_pool()
        db_ok = (await pool.fetchval("SELECT 1")) == 1
    except Exception:  # noqa: BLE001
        pass
    try:
        redis_ok = bool(await _state["redis"].ping())
    except Exception:  # noqa: BLE001
        pass
    return {
        "status": "healthy",
        "service": SERVICE,
        "db_connected": db_ok,
        "redis_connected": redis_ok,
        "ws_clients_active": ws_module.manager.count,
    }


@app.get("/metrics")
async def metrics() -> Response:
    _ws_clients_gauge.set(ws_module.manager.count)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
