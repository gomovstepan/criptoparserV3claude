"""WebSocket-коллектор одной биржи через CCXT Pro.

``ExchangeCollector`` либо мультиплексирует все символы биржи через один WS
(``watch_order_book_for_symbols``, поддерживается binance/bybit/kucoin/bitget/
coinex), либо открывает отдельный таск на символ для бирж без поддержки
мультиплекса (gateio, bingx). В обоих случаях best bid/ask публикуется в
Redis Stream ``prices``.
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

# Параметры для бирж БЕЗ мультиплекса (per-symbol режим).
# Stagger 250 ms между символами — иначе биржи с жёстким лимитом
# (coinex 10 req/s, bingx) отбивают handshake'и с "Too many connections".
STAGGER_DELAY_SEC = 0.25

# Одновременные handshake'и в per-symbol режиме.
HANDSHAKE_CONCURRENCY = 2

# Лимит символов на ОДИН WS-subscribe для бирж в multiplex-режиме.
# Bybit (wss spot v5) молча игнорирует subscribe больше ~10 args:
# первый ответ не приходит, watch_order_book_for_symbols висит.
# Разбиваем список на чанки и запускаем по таску на чанк.
MULTIPLEX_CHUNK_SIZE = {
    "bybit": 10,
}
DEFAULT_MULTIPLEX_CHUNK_SIZE = 50  # эффективно «без чанкования»


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
        self._handshake_sem = asyncio.Semaphore(HANDSHAKE_CONCURRENCY)

    async def start(self) -> None:
        """Создать CCXT-инстанс и запустить watch-таски.

        Если биржа поддерживает ``watchOrderBookForSymbols`` — открываем
        ОДИН WS-сокет с подпиской на все символы (или несколько сокетов
        по чанкам, если биржа ограничивает кол-во символов на subscribe).
        Это устраняет корень "Too many connections": биржа физически
        получает 1-N коннектов вместо 36. Иначе fallback — отдельный
        таск на символ со staggered start.
        """
        self._running = True
        self.exchange = create_exchange(self.name)

        if self.exchange.has.get("watchOrderBookForSymbols"):
            chunk = MULTIPLEX_CHUNK_SIZE.get(self.name, DEFAULT_MULTIPLEX_CHUNK_SIZE)
            chunks = [
                self.symbols[i:i + chunk] for i in range(0, len(self.symbols), chunk)
            ]
            self._tasks = [
                asyncio.create_task(
                    self._watch_multiplexed(group),
                    name=f"{self.name}:multi:{idx}",
                )
                for idx, group in enumerate(chunks)
            ]
            log.info(
                "collector_started",
                exchange=self.name, symbols=self.symbols,
                mode="multiplexed", chunks=len(chunks),
            )
        else:
            self._tasks = [
                asyncio.create_task(
                    self._watch_symbol(sym, idx * STAGGER_DELAY_SEC),
                    name=f"{self.name}:{sym}",
                )
                for idx, sym in enumerate(self.symbols)
            ]
            log.info(
                "collector_started",
                exchange=self.name, symbols=self.symbols, mode="per_symbol",
            )

    async def _watch_multiplexed(self, symbols: list[str]) -> None:
        """Один WS-сокет на чанк символов: ``watch_order_book_for_symbols``.

        CCXT Pro подписывается на все символы через один коннект и
        возвращает обновление по очередному из них при каждом await.
        """
        attempt = 0
        while self._running:
            try:
                order_book = await self.exchange.watch_order_book_for_symbols(symbols)
                self.status = "connected"
                attempt = 0
                symbol = order_book.get("symbol")
                if symbol:
                    await self._handle_order_book(symbol, order_book)
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                self.status = "reconnecting"
                delay = backoff_delay(attempt)
                log.warning(
                    "ws_error", exchange=self.name,
                    symbol=f"<multi:{len(symbols)}>",
                    error=str(err), retry_in_sec=delay,
                )
                attempt += 1
                await asyncio.sleep(delay)

    async def _watch_symbol(self, symbol: str, initial_delay: float = 0.0) -> None:
        if initial_delay > 0:
            await asyncio.sleep(initial_delay)
        attempt = 0
        connected_once = False
        while self._running:
            try:
                if not connected_once:
                    async with self._handshake_sem:
                        order_book = await self.exchange.watch_order_book(symbol)
                else:
                    order_book = await self.exchange.watch_order_book(symbol)
                self.status = "connected"
                attempt = 0
                connected_once = True
                await self._handle_order_book(symbol, order_book)
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 — любой сбой WS → reconnect
                self.status = "reconnecting"
                connected_once = False
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
        await self.publisher.publish_depth(self.name, symbol, bids, asks, now)
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
