"""WebSocket-коллектор одной биржи через CCXT Pro.

``ExchangeCollector`` либо мультиплексирует все символы биржи через один WS
(``watch_order_book_for_symbols``, поддерживается binance/bybit/kucoin/bitget/
coinex), либо открывает отдельный таск на символ для бирж без поддержки
мультиплекса (gateio, bingx). В обоих случаях best bid/ask публикуется в
Redis Stream ``prices``.
"""
from __future__ import annotations

import asyncio
import os
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

# Вотчдог «тихого зависания»: WS жив на уровне TCP (VPN half-open), но данные
# не идут — исключения нет, и штатный reconnect не срабатывает. Триггер — тишина
# ЦЕЛОГО соединения (агрегатный поток биржи в норме 6–127 msg/s, вероятность
# честной тишины 3с ~ нулевая). Тишина ОТДЕЛЬНОГО символа триггером не является:
# тихие книги неликвидов молчат минутами, это нормальный рынок.
WATCHDOG_SILENCE_SEC = float(os.getenv("WATCHDOG_SILENCE_SEC", "3.0"))
# Бюджет ПЕРВОГО ответа после (пере)подключения: handshake + subscribe + снапшот
# через VPN занимают заметно больше 3с. Жёсткие 3с на этот участок устраивали
# шторм реконнектов на старте (25 срабатываний в первую секунду прогона).
WATCHDOG_HANDSHAKE_SEC = float(os.getenv("WATCHDOG_HANDSHAKE_SEC", "30.0"))


class ExchangeCollector:
    """Сбор best bid/ask с одной биржи по списку символов."""

    def __init__(self, name: str, symbols: list[str], publisher: RedisPublisher) -> None:
        self.name = name
        self.symbols = symbols
        self.publisher = publisher
        self.exchange = None
        self.status = "connecting"   # connecting | connected | reconnecting | disconnected
        self.message_count = 0
        self.forced_reconnects = 0   # срабатывания вотчдога (метрика /health)
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._handshake_sem = asyncio.Semaphore(HANDSHAKE_CONCURRENCY)
        self._last_message_ms = 0    # для вотчдога per-symbol режима

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
            # В per-symbol режиме wait_for на отдельный символ нельзя (тихая
            # книга — не сбой), поэтому тишину всей биржи следит отдельный таск.
            self._tasks.append(asyncio.create_task(
                self._watchdog_loop(), name=f"{self.name}:watchdog",
            ))
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
        streaming = False   # True после первого обновления на текущем соединении
        while self._running:
            try:
                # В steady state (streaming) пауза чанка > 3с — мёртвый сокет.
                # Сразу после (пере)подключения даём handshake-бюджет: первый
                # ответ включает рукопожатие, подписку и начальный снапшот.
                timeout = WATCHDOG_SILENCE_SEC if streaming else WATCHDOG_HANDSHAKE_SEC
                order_book = await asyncio.wait_for(
                    self.exchange.watch_order_book_for_symbols(symbols),
                    timeout=timeout,
                )
                self.status = "connected"
                streaming = True
                attempt = 0
                symbol = order_book.get("symbol")
                if symbol:
                    await self._handle_order_book(symbol, order_book)
            except asyncio.CancelledError:
                raise
            except asyncio.TimeoutError:
                # Тихое зависание: чанк на 10-50 символов не прислал НИ ОДНОГО
                # обновления. close() рвёт сокет (у bybit уронит и соседние
                # чанки — они переподключатся штатной веткой ws_error).
                delay = backoff_delay(attempt)
                log.warning(
                    "ws_watchdog_reconnect", exchange=self.name,
                    symbol=f"<multi:{len(symbols)}>", was_streaming=streaming,
                    silence_sec=timeout, retry_in_sec=round(delay, 1),
                )
                await self._force_reconnect()
                streaming = False
                attempt += 1
                await asyncio.sleep(delay)
            except Exception as err:  # noqa: BLE001
                self.status = "reconnecting"
                streaming = False
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
        self._last_message_ms = now
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
        # Глубина публикуется РАНЬШЕ тика: сканер разбужен тиком и тут же
        # читает depth-ключ — обратный порядок регулярно подсовывал ему
        # глубину старше собственного сигнала (гонка публикаций).
        # ts = min(now, биржевой): лаг биржа→коллектор (пики до 34с) должен
        # съедать бюджет свежести, иначе executor торгует по мёртвой книге,
        # считая её секундной.
        await self.publisher.publish_depth(
            self.name, symbol, bids, asks, min(now, int(exchange_ts)),
        )
        await self.publisher.publish_price(tick)
        self.message_count += 1

    async def _force_reconnect(self) -> None:
        """Принудительно разорвать WS после тишины.

        ``close()`` сбрасывает все клиенты ccxt — watch-циклы пересоздадут
        подписки. Depth-ключи биржи удаляются сразу: scanner/executor должны
        увидеть отсутствие книги, а не дотрагивать TTL по мёртвым данным.
        """
        self.status = "reconnecting"
        self.forced_reconnects += 1
        try:
            await self.exchange.close()
        except Exception as err:  # noqa: BLE001
            log.warning("ws_close_error", exchange=self.name, error=str(err))
        try:
            await self.publisher.delete_depth(self.name, self.symbols)
        except Exception as err:  # noqa: BLE001
            log.warning("depth_cleanup_error", exchange=self.name, error=str(err))

    async def _watchdog_loop(self) -> None:
        """Вотчдог per-symbol режима: тишина ВСЕЙ биржи > WATCHDOG_SILENCE_SEC.

        Ни одного сообщения ни по одному символу — это мёртвый фид, а не тихий
        рынок (агрегатный поток gateio/bingx в норме 11–127 msg/s).

        ``baseline_ms`` — точка отсчёта тишины, пока сообщений нет: на буте
        (фид, мёртвый с самого старта, ловится после handshake-грейса) и после
        каждого срабатывания (грейс на stagger 250мс × N символов, иначе
        вотчдог стрелял бы по ещё не поднявшимся соединениям). ``attempt``
        сбрасывается только по НАСТОЯЩЕМУ сообщению после срабатывания —
        иначе backoff никогда не эскалировал бы для стабильно мёртвого фида.
        """
        boot_grace = STAGGER_DELAY_SEC * len(self.symbols) + WATCHDOG_HANDSHAKE_SEC
        baseline_ms = int(time.time() * 1000) + int(boot_grace * 1000)
        last_fire_msg_ms = 0
        attempt = 0
        while self._running:
            await asyncio.sleep(1.0)
            if not self._running:
                break
            if attempt and self._last_message_ms > last_fire_msg_ms:
                attempt = 0  # после срабатывания пришли живые данные
            now = int(time.time() * 1000)
            silence_ms = now - max(self._last_message_ms, baseline_ms)
            if silence_ms <= WATCHDOG_SILENCE_SEC * 1000:
                continue
            delay = backoff_delay(attempt)
            log.warning(
                "ws_watchdog_reconnect", exchange=self.name, symbol="<all>",
                silence_ms=silence_ms, attempt=attempt, retry_in_sec=round(delay, 1),
            )
            await self._force_reconnect()
            last_fire_msg_ms = self._last_message_ms
            attempt += 1
            grace = max(delay, boot_grace)
            baseline_ms = int(time.time() * 1000) + int(grace * 1000)
            await asyncio.sleep(grace)

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
