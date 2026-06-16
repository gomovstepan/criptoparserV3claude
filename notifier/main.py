"""Notifier (порт 8004) — Telegram-уведомления (Фаза 8).

- читает ``opportunities`` и ``trades`` (consumer group ``notifier-cg``);
- по спреду > notification_spread_threshold и по каждой сделке формирует сообщение;
- кладёт в очередь ``telegram_queue`` (rate limit 20 msg/sec);
- aiogram-бот в режиме polling обрабатывает команды.
"""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

import aiohttp
import redis.asyncio as redis
import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from pydantic import BaseModel

import bot as bot_module
from formatter import format_opportunity, format_trade
from tg_queue import TelegramQueue
from shared.config import settings
from shared.db import close_db_pool, get_db_pool
from shared.models import Opportunity, Trade

log = structlog.get_logger()
SERVICE = "notifier"

OPPORTUNITIES_STREAM = "opportunities"
TRADES_STREAM = "trades"
GROUP = "notifier-cg"
CONSUMER = "notifier-1"

# Пороги уведомлений (значения по умолчанию; перечитываются из таблицы settings).
DEFAULT_SPREAD_THRESHOLD_PCT = 0.50   # порог спреда для алерта об opportunity
DEFAULT_TRADE_MIN_PNL = 5.0           # минимум |net P&L| USDT, чтобы алертить сделку
THRESHOLDS_REFRESH_SEC = 10

_sent_gauge = Gauge("telegram_messages_sent_total", "Всего отправлено Telegram-сообщений")
_suppressed_gauge = Gauge("telegram_trades_suppressed_total", "Сделок не отправлено (ниже порога)")

_state: dict = {
    "redis": None, "pool": None, "bot": None, "dp": None, "queue": None, "http": None,
    "telegram_connected": False, "bot_username": None,
    "spread_threshold": DEFAULT_SPREAD_THRESHOLD_PCT,
    "trade_min_pnl": DEFAULT_TRADE_MIN_PNL,
    "trades_suppressed": 0,
    "running": False, "tasks": [],
}


def _setting_float(raw, fallback: float) -> float:
    """JSONB-значение из settings (например ``"0.50"`` или ``0.5``) → float."""
    try:
        return float(str(raw).strip('"'))
    except (TypeError, ValueError):
        return fallback


async def _refresh_thresholds() -> None:
    """Периодически перечитывать пороги уведомлений из таблицы settings."""
    while _state["running"]:
        try:
            rows = await _state["pool"].fetch(
                "SELECT key, value FROM settings "
                "WHERE key IN ('notification_spread_threshold', 'notification_trade_min_pnl')"
            )
            values = {r["key"]: r["value"] for r in rows}
            if "notification_spread_threshold" in values:
                _state["spread_threshold"] = _setting_float(
                    values["notification_spread_threshold"], DEFAULT_SPREAD_THRESHOLD_PCT
                )
            if "notification_trade_min_pnl" in values:
                _state["trade_min_pnl"] = _setting_float(
                    values["notification_trade_min_pnl"], DEFAULT_TRADE_MIN_PNL
                )
        except Exception as err:  # noqa: BLE001
            log.warning("thresholds_refresh_failed", error=str(err))
        await asyncio.sleep(THRESHOLDS_REFRESH_SEC)


async def _ensure_groups(r: redis.Redis) -> None:
    for stream in (OPPORTUNITIES_STREAM, TRADES_STREAM):
        try:
            await r.xgroup_create(stream, GROUP, id="$", mkstream=True)
        except redis.ResponseError as err:
            if "BUSYGROUP" not in str(err):
                raise


async def _consume_loop() -> None:
    r: redis.Redis = _state["redis"]
    queue: TelegramQueue = _state["queue"]
    while _state["running"]:
        try:
            resp = await r.xreadgroup(
                GROUP, CONSUMER,
                {OPPORTUNITIES_STREAM: ">", TRADES_STREAM: ">"},
                count=50, block=1000,
            )
            if not resp:
                continue
            for stream_name, entries in resp:
                ids = []
                for msg_id, fields in entries:
                    ids.append(msg_id)
                    await _handle_entry(stream_name, fields, queue)
                if ids:
                    await r.xack(stream_name, GROUP, *ids)
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            log.error("notifier_consume_error", error=str(err))
            await asyncio.sleep(1)


async def _handle_entry(stream_name: str, fields: dict, queue: TelegramQueue) -> None:
    try:
        if stream_name == OPPORTUNITIES_STREAM:
            opp = Opportunity.from_redis(fields)
            if opp.gross_spread_pct >= _state["spread_threshold"]:
                await queue.enqueue(format_opportunity(opp))
        elif stream_name == TRADES_STREAM:
            trade = Trade.from_redis(fields)
            # Шлём только значимые сделки: |net P&L| >= порога (остальное — шум).
            if abs(trade.net_pnl) >= _state["trade_min_pnl"]:
                await queue.enqueue(format_trade(trade))
            else:
                _state["trades_suppressed"] += 1
    except Exception as err:  # noqa: BLE001
        log.warning("notifier_format_error", stream=stream_name, error=str(err))


@asynccontextmanager
async def lifespan(app: FastAPI):
    r = redis.from_url(settings.redis_url, decode_responses=True)
    await r.ping()
    _state["redis"] = r
    _state["pool"] = await get_db_pool()
    _state["http"] = aiohttp.ClientSession()

    bot = Bot(token=settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=None))
    dp = Dispatcher()
    dp.include_router(bot_module.router)
    bot_module.set_deps(bot_module.Deps(redis=r, http=_state["http"]))
    _state["bot"], _state["dp"] = bot, dp

    # Проверка связи с Telegram
    try:
        me = await bot.get_me()
        _state["telegram_connected"] = True
        _state["bot_username"] = me.username
        log.info("telegram_connected", username=me.username)
    except Exception as err:  # noqa: BLE001
        log.error("telegram_connect_failed", error=str(err))

    queue = TelegramQueue(r, bot, settings.telegram_chat_id)
    await queue.start()
    _state["queue"] = queue

    await _ensure_groups(r)
    _state["running"] = True
    _state["tasks"] = [
        asyncio.create_task(_consume_loop(), name="notifier_consume"),
        asyncio.create_task(_refresh_thresholds(), name="thresholds_refresher"),
    ]

    # aiogram polling (только если бот доступен)
    if _state["telegram_connected"]:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception:  # noqa: BLE001
            pass
        _state["tasks"].append(
            asyncio.create_task(dp.start_polling(bot, handle_signals=False), name="telegram_polling")
        )

    log.info("notifier_up")
    try:
        yield
    finally:
        _state["running"] = False
        await queue.stop()
        for task in _state["tasks"]:
            task.cancel()
        await asyncio.gather(*_state["tasks"], return_exceptions=True)
        await _state["http"].close()
        await bot.session.close()
        await r.aclose()
        await close_db_pool()
        log.info("notifier_down")


app = FastAPI(title=f"{SERVICE} service", lifespan=lifespan)


class NotifyRequest(BaseModel):
    type: str = "test"
    message: str


@app.post("/notify")
async def notify(req: NotifyRequest) -> dict:
    message_id = await _state["queue"].enqueue(f"🔔 {req.message}")
    return {"status": "queued", "message_id": message_id}


@app.get("/health")
async def health() -> dict:
    queue: TelegramQueue = _state["queue"]
    return {
        "status": "healthy",
        "service": SERVICE,
        "telegram_connected": _state["telegram_connected"],
        "bot_username": _state["bot_username"],
        "messages_sent_today": queue.messages_sent if queue else 0,
        "trades_suppressed": _state["trades_suppressed"],
        "queue_length": await queue.length() if queue else 0,
        "spread_threshold_pct": _state["spread_threshold"],
        "trade_min_pnl_usdt": _state["trade_min_pnl"],
    }


@app.get("/metrics")
async def metrics() -> Response:
    if _state["queue"]:
        _sent_gauge.set(_state["queue"].messages_sent)
    _suppressed_gauge.set(_state["trades_suppressed"])
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
