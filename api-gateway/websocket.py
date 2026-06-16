"""WebSocket /ws — real-time push цен, спредов и сделок (Фаза 9).

ConnectionManager хранит активные подключения. Два фоновых броадкастера:
- события (opportunities, trades) — XREAD от текущего конца стрима;
- снимок цен — раз в секунду последний bid/ask по каждой (бирже, паре).
"""
from __future__ import annotations

import asyncio
import json

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from auth import decode_token
from redis_client import get_redis

log = structlog.get_logger()
router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.active.discard(ws)

    async def broadcast(self, message: dict) -> None:
        dead = []
        for ws in list(self.active):
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001 — клиент отвалился
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def count(self) -> int:
        return len(self.active)


manager = ConnectionManager()


async def events_broadcaster() -> None:
    r = await get_redis()
    last = {"opportunities": "$", "trades": "$"}
    while True:
        try:
            resp = await r.xread(last, block=2000, count=20)
            for stream_name, entries in resp or []:
                for msg_id, fields in entries:
                    last[stream_name] = msg_id
                    if manager.count:
                        await manager.broadcast({"channel": stream_name, "data": fields})
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            log.error("ws_events_error", error=str(err))
            await asyncio.sleep(1)


async def prices_broadcaster() -> None:
    r = await get_redis()
    while True:
        try:
            await asyncio.sleep(1)
            if not manager.count:
                continue
            entries = await r.xrevrange("prices", count=80)
            latest: dict[tuple, dict] = {}
            for _msg_id, f in entries:
                key = (f.get("exchange"), f.get("symbol"))
                if key not in latest:
                    latest[key] = {
                        "exchange": f.get("exchange"),
                        "symbol": f.get("symbol"),
                        "bid": float(f["bid"]),
                        "ask": float(f["ask"]),
                    }
            if latest:
                await manager.broadcast({"channel": "prices", "data": list(latest.values())})
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            log.error("ws_prices_error", error=str(err))
            await asyncio.sleep(1)


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, token: str | None = Query(None)) -> None:
    # JWT через query-параметр (необязателен для подключения, но проверяется если передан)
    if token:
        try:
            decode_token(token)
        except Exception:  # noqa: BLE001
            await websocket.close(code=1008)
            return

    await manager.connect(websocket)
    try:
        await websocket.send_json({"channel": "system", "data": {"message": "connected"}})
        while True:
            raw = await websocket.receive_text()  # держим соединение + heartbeat
            # Клиентский ping → отвечаем pong (liveness-проверка на стороне фронта).
            try:
                if raw and json.loads(raw).get("type") == "ping":
                    await websocket.send_json({"channel": "system", "data": {"type": "pong"}})
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:  # noqa: BLE001
        manager.disconnect(websocket)
