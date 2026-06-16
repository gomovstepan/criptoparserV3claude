"""WebSocket-коллектор одной биржи через CCXT Pro.

``ExchangeCollector`` для каждого символа держит отдельный asyncio-таск с циклом
``watch_order_book`` и автоматическим reconnect (exponential backoff). Лучший
bid/ask публикуется в Redis Stream ``prices``.
"""
from __future__ import annotations

import asyncio
import time

import structlog

from exchange_factory import create_exchange
from reconnect import backoff_delay
from redis_publisher import RedisPublisher
from shared.models import PriceTick

log = structlog.get_logger()


class ExchangeCollector:
    """Сбор best bid/ask с одной биржи по списку символов."""

    def __init__(self, name: str, symbols: list[str], publisher: RedisPublisher) -> None:
        self.name = name
        self.symbols = symbols
        self.publisher = publisher
        self.exchange = None
        self.status = "connecting"   # connecting | connected | reconnecting | disconnected
        self.message_count = 0
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Создать CCXT-инстанс и запустить watch-таски по каждому символу."""
        self._running = True
        self.exchange = create_exchange(self.name)
        self._tasks = [
            asyncio.create_task(self._watch_symbol(sym), name=f"{self.name}:{sym}")
            for sym in self.symbols
        ]
        log.info("collector_started", exchange=self.name, symbols=self.symbols)

    async def _watch_symbol(self, symbol: str) -> None:
        attempt = 0
        while self._running:
            try:
                order_book = await self.exchange.watch_order_book(symbol)
                self.status = "connected"
                attempt = 0
                await self._handle_order_book(symbol, order_book)
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 — любой сбой WS → reconnect
                self.status = "reconnecting"
                delay = backoff_delay(attempt)
                log.warning(
                    "ws_error", exchange=self.name, symbol=symbol,
                    error=str(err), retry_in_sec=delay,
                )
                attempt += 1
                await asyncio.sleep(delay)

    async def _handle_order_book(self, symbol: str, order_book: dict) -> None:
        bids = order_book.get("bids") or []
        asks = order_book.get("asks") or []
        if not bids or not asks:
            return
        now = int(time.time() * 1000)
        exchange_ts = order_book.get("timestamp") or now
        tick = PriceTick(
            exchange=self.name,
            symbol=symbol,
            bid=float(bids[0][0]),
            ask=float(asks[0][0]),
            bid_volume=float(bids[0][1]) if len(bids[0]) > 1 else None,
            ask_volume=float(asks[0][1]) if len(asks[0]) > 1 else None,
            timestamp=int(exchange_ts),
            received_at=now,
            latency_ms=max(0, now - int(exchange_ts)),
        )
        await self.publisher.publish_price(tick)
        self.message_count += 1

    async def stop(self) -> None:
        """Graceful shutdown: отменить таски и закрыть WS-соединение."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        if self.exchange is not None:
            try:
                await self.exchange.close()
            except Exception as err:  # noqa: BLE001
                log.warning("ws_close_error", exchange=self.name, error=str(err))
        self.status = "disconnected"
        log.info("collector_stopped", exchange=self.name)
