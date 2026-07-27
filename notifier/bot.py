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

from shared.config import EXCHANGES, settings
from shared.models import Trade

log = structlog.get_logger()
router = Router()


def _authorized(message: Message) -> bool:
    """Пускать только чат оператора (TELEGRAM_CHAT_ID).

    Бот работает в polling и публично находим по имени, а команды раскрывают
    балансы/сделки и двигают kill switch (включая ВОЗОБНОВЛЕНИЕ торговли после
    аварийной остановки). Пустой TELEGRAM_CHAT_ID = запрет всех команд —
    fail-safe, а не открытый доступ. Чужие чаты игнорируются молча.
    """
    allowed = str(settings.telegram_chat_id or "").strip()
    if not allowed:
        return False
    if str(message.chat.id) != allowed:
        log.warning("tg_unauthorized_command", chat_id=message.chat.id,
                    text=(message.text or "")[:64])
        return False
    return True


router.message.filter(_authorized)

TRADES_STREAM = "trades"

# Адреса сервисов внутри docker-сети
SERVICE_URLS = {
    "collector": "http://collector:8001/health",
    "scanner": "http://scanner:8002/health",
    "executor": "http://executor:8003/health",
    "api-gateway": "http://api-gateway:8000/health",
}
EXECUTOR_KILLSWITCH_URL = "http://executor:8003/killswitch"
KILL_SWITCH_KEY = "executor:kill_switch"
HTTP_TIMEOUT = aiohttp.ClientTimeout(total=4)
MAX_TRADES_LIMIT = 50  # /trades N: потолок, как у REST-пагинации (le=100)


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
        "/killswitch — переключить аварийную остановку торговли"
    )


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    lines = ["📊 Статус сервисов:"]
    for name, url in SERVICE_URLS.items():
        try:
            async with _deps.http.get(url, timeout=HTTP_TIMEOUT) as resp:
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
    limit = min(int(parts[1]), MAX_TRADES_LIMIT) if len(parts) > 1 and parts[1].isdigit() else 5
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
    """Переключить kill switch.

    Раньше команда слала запрос без поля ``active``, а на стороне executor'а оно
    по умолчанию ``True`` — то есть торговлю можно было только остановить, но не
    возобновить. Текущее состояние читаем из того же ключа Redis, что и executor,
    и посылаем противоположное.
    """
    try:
        current = (await _deps.redis.get(KILL_SWITCH_KEY)) == "1"
        async with _deps.http.post(
            EXECUTOR_KILLSWITCH_URL,
            json={"reason": "telegram", "active": not current},
            timeout=HTTP_TIMEOUT,
        ) as resp:
            data = await resp.json()
        active = data.get("kill_switch_active")
        icon = "🛑" if active else "✅"
        state = "торговля остановлена" if active else "торговля возобновлена"
        await message.answer(f"{icon} Kill switch: {data.get('status')} — {state}")
    except Exception as err:  # noqa: BLE001
        await message.answer(f"❌ Не удалось вызвать killswitch: {err}")
