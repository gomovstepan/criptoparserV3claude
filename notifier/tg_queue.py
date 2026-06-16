"""Очередь исходящих Telegram-сообщений с rate limiting (Фаза 8).

Сообщения буферизуются в Redis List ``telegram_queue`` (backpressure). Фоновый
sender достаёт их и отправляет с лимитом не более 20 msg/sec (требование N-005).

Прим.: файл назван ``tg_queue`` (а не ``queue``), чтобы не затенять стандартный
модуль ``queue`` — рабочая директория сервиса первой в sys.path.
"""
from __future__ import annotations

import asyncio
import json
import time

import redis.asyncio as redis
import structlog

log = structlog.get_logger()

QUEUE_KEY = "telegram_queue"
DEAD_LETTER_KEY = "telegram_dead_letter"
MAX_PER_SEC = 20
MAX_RETRIES = 3
MIN_INTERVAL = 1.0 / MAX_PER_SEC  # 50 ms между отправками


class TelegramQueue:
    def __init__(self, redis_client: redis.Redis, bot, default_chat_id: str) -> None:
        self._redis = redis_client
        self._bot = bot
        self._default_chat = default_chat_id
        self._running = False
        self._task: asyncio.Task | None = None
        self.messages_sent = 0

    async def enqueue(self, text: str, chat_id: str | None = None) -> str:
        message_id = f"msg_{int(time.time() * 1000)}"
        payload = json.dumps({"chat_id": chat_id or self._default_chat, "text": text, "id": message_id})
        await self._redis.lpush(QUEUE_KEY, payload)
        return message_id

    async def length(self) -> int:
        return int(await self._redis.llen(QUEUE_KEY))

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._sender_loop(), name="telegram_sender")

    async def _sender_loop(self) -> None:
        while self._running:
            try:
                item = await self._redis.brpop(QUEUE_KEY, timeout=1)
                if item is None:
                    continue
                _, payload = item
                data = json.loads(payload)
                retries = data.get("_retries", 0)
                try:
                    await self._bot.send_message(data["chat_id"], data["text"])
                    self.messages_sent += 1
                except asyncio.CancelledError:
                    raise
                except Exception as err:  # noqa: BLE001
                    if retries < MAX_RETRIES:
                        data["_retries"] = retries + 1
                        await self._redis.lpush(QUEUE_KEY, json.dumps(data))
                    else:
                        await self._redis.lpush(DEAD_LETTER_KEY, payload)
                        log.error("telegram_dead_letter", error=str(err), msg_id=data.get("id"))
                await asyncio.sleep(MIN_INTERVAL)
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                log.error("telegram_queue_error", error=str(err))
                await asyncio.sleep(1)

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
