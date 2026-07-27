"""WebSocket /ws — real-time push цен, спредов и сделок (Фаза 9).

ConnectionManager хранит активные подключения. Два фоновых броадкастера:
- события (opportunities, trades) — XREAD от текущего конца стрима;
- цены — XREAD накапливает карту последних bid/ask по (биржа, пара) и раз в
  секунду шлёт её целиком. После прогрева срез покрывает ВСЕ сочетания
  биржа×пара (раньше было окно XREVRANGE из 80 записей — только тикавшие
  последними). В каждой записи есть ``ts`` (received_at коллектора, unix ms):
  фронтенд по нему отличает живые цены от замолчавших бирж — сам факт
  присутствия в накопительном срезе живость больше не означает.
"""
from __future__ import annotations

import asyncio
import json
import time

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from auth import decode_token
from redis_client import get_redis

log = structlog.get_logger()
router = APIRouter()

# Как часто шлём накопленный срез цен подключённым клиентам.
PRICES_BROADCAST_SEC = 1.0
# Лимит на отправку одному клиенту: зависший не должен блокировать остальных.
WS_SEND_TIMEOUT_SEC = 2.0
# Пара без тиков дольше этого выселяется из накопительного среза цен.
PRICE_STALE_MS = 300_000


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
                # Таймаут на отправку: один зависший клиент (переполненный TCP-буфер)
                # иначе блокировал бы доставку цен/сделок ВСЕМ остальным.
                await asyncio.wait_for(ws.send_json(message), timeout=WS_SEND_TIMEOUT_SEC)
            except Exception:  # noqa: BLE001 — клиент отвалился или завис
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
    latest: dict[tuple, dict] = {}
    last_id = "$"
    last_broadcast = 0.0
    while True:
        try:
            # block=1000 — просыпаемся не реже раза в секунду даже без тиков,
            # чтобы отдать срез (например, сразу после подключения клиента).
            resp = await r.xread({"prices": last_id}, block=1000, count=500)
            for _stream, entries in resp or []:
                for msg_id, f in entries:
                    last_id = msg_id
                    try:
                        latest[(f["exchange"], f["symbol"])] = {
                            "exchange": f["exchange"],
                            "symbol": f["symbol"],
                            "bid": float(f["bid"]),
                            "ask": float(f["ask"]),
                            "ts": int(f["received_at"]),
                        }
                    except (KeyError, TypeError, ValueError):
                        continue  # битая запись не должна ронять весь срез
            # Выселение замолчавших: пара, не тикавшая 5 минут (деактивирована,
            # биржа отключена), не должна вечно сидеть в срезе и в памяти.
            cutoff = int(time.time() * 1000) - PRICE_STALE_MS
            for key in [k for k, v in latest.items() if v["ts"] < cutoff]:
                del latest[key]
            now = time.monotonic()
            if latest and manager.count and now - last_broadcast >= PRICES_BROADCAST_SEC:
                # ``now`` в сообщении — серверные часы: фронт считает возраст тика
                # как (now - ts) в ОДНИХ часах, не сравнивая их со своими
                # (дрейф часов браузера/контейнера иначе гасил бы «свежесть»).
                await manager.broadcast({
                    "channel": "prices",
                    "data": list(latest.values()),
                    "now": int(time.time() * 1000),
                })
                last_broadcast = now
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            log.error("ws_prices_error", error=str(err))
            await asyncio.sleep(1)


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, token: str | None = Query(None)) -> None:
    # JWT обязателен: /ws отдаёт те же цены/сделки, что REST прячет за auth.
    # Раньше токен был «проверяется, если передан» — аноним получал весь поток.
    # Фронт всегда шлёт ?token= (useWebSocket.ts), так что клиентских правок нет.
    if not token:
        await websocket.close(code=1008)
        return
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
