"""Команды Telegram-бота (Фаза 8): /start, /status, /balance, /trades, /killswitch.

Зависимости (Redis, HTTP-сессия, адреса сервисов) кладутся в модульный ``_deps``
при старте — хендлеры обращаются к ним напрямую.
"""
from __future__ import annotations

from dataclasses import dataclass

import aiohttp
import redis.asyncio as redis
import structlog
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from shared.config import EXCHANGES
from shared.models import Trade

log = structlog.get_logger()
router = Router()

TRADES_STREAM = "trades"

# Адреса сервисов внутри docker-сети
SERVICE_URLS = {
    "collector": "http://collector:8001/health",
    "scanner": "http://scanner:8002/health",
    "executor": "http://executor:8003/health",
    "api-gateway": "http://api-gateway:8000/health",
}
EXECUTOR_KILLSWITCH_URL = "http://executor:8003/killswitch"


@dataclass
class Deps:
    redis: redis.Redis
    http: aiohttp.ClientSession


_deps: Deps | None = None


def set_deps(deps: Deps) -> None:
    global _deps
    _deps = deps


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Crypto Arbitrage Bot\n\n"
        "Команды:\n"
        "/status — статус сервисов\n"
        "/balance — виртуальный баланс по биржам\n"
        "/trades [N] — последние N сделок (default 5)\n"
        "/killswitch — аварийная остановка торговли"
    )


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    lines = ["📊 Статус сервисов:"]
    for name, url in SERVICE_URLS.items():
        try:
            async with _deps.http.get(url, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                data = await resp.json()
                lines.append(f"• {name}: {data.get('status', '?')}")
        except Exception:  # noqa: BLE001
            lines.append(f"• {name}: ❌ unreachable")
    await message.answer("\n".join(lines))


@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    lines = ["💰 Виртуальный баланс (USDT):"]
    total = 0.0
    for exchange in EXCHANGES:
        value = await _deps.redis.hget(f"balance:{exchange}", "USDT")
        amount = float(value) if value is not None else 0.0
        total += amount
        lines.append(f"• {exchange}: {amount:,.2f}")
    lines.append(f"\nИтого: {total:,.2f}")
    await message.answer("\n".join(lines))


@router.message(Command("trades"))
async def cmd_trades(message: Message) -> None:
    parts = (message.text or "").split()
    limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 5
    entries = await _deps.redis.xrevrange(TRADES_STREAM, count=limit)
    if not entries:
        await message.answer("Сделок пока нет.")
        return
    lines = [f"📈 Последние {len(entries)} сделок:"]
    for _msg_id, fields in entries:
        try:
            t = Trade.from_redis(fields)
            sign = "🟢" if t.net_pnl >= 0 else "🔴"
            lines.append(f"{sign} {t.symbol} {t.buy_exchange}→{t.sell_exchange}  net ${t.net_pnl:,.2f}")
        except Exception:  # noqa: BLE001
            continue
    await message.answer("\n".join(lines))


@router.message(Command("killswitch"))
async def cmd_killswitch(message: Message) -> None:
    try:
        async with _deps.http.post(
            EXECUTOR_KILLSWITCH_URL,
            json={"reason": "telegram"},
            timeout=aiohttp.ClientTimeout(total=4),
        ) as resp:
            data = await resp.json()
        await message.answer(f"🛑 Kill switch: {data.get('status')} (активен: {data.get('kill_switch_active')})")
    except Exception as err:  # noqa: BLE001
        await message.answer(f"❌ Не удалось вызвать killswitch: {err}")
