"""Batch-запись тиков из Redis Stream ``prices`` в hypertable ``prices``.

Читает stream через consumer group ``writer-cg`` (XREADGROUP), накапливает до
100 записей или 1 секунды и пишет пачкой через COPY (asyncpg). После записи —
XACK обработанных сообщений.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import redis.asyncio as redis
import structlog

from shared.config import settings
from shared.db import get_db_pool

log = structlog.get_logger()

PRICES_STREAM = "prices"
GROUP = "writer-cg"
CONSUMER = "writer-1"
# BATCH_SIZE 1000 даёт ~10× throughput vs 100 за счёт амортизации
# round-trip к Postgres. При темпе 100+ tick/sec и стриме на 100k
# меньшие пачки приводили к хроническому отставанию writer'а.
BATCH_SIZE = 1000
BLOCK_MS = 1000  # максимум 1 секунда ожидания пачки

_COLUMNS = ["time", "exchange", "symbol", "bid", "ask", "bid_volume", "ask_volume", "latency_ms"]

# Цены остаются NUMERIC(18,8) — реальная spot-цена не превышает 10^10.
# Объёмы в БД мигрированы на NUMERIC(28,8) (см. migrate-volume-precision.sql).
_PRICE_MAX = Decimal("9999999999.99999999")               # NUMERIC(18,8)
_VOLUME_MAX = Decimal("99999999999999999999.99999999")    # NUMERIC(28,8)


class BatchWriter:
    """Консьюмер stream'а ``prices`` → batch INSERT в TimescaleDB."""

    def __init__(self) -> None:
        self._redis: redis.Redis | None = None
        self._pool = None
        self._running = False
        self._task: asyncio.Task | None = None
        self.rows_written = 0

    async def start(self) -> None:
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        self._pool = await get_db_pool()
        await self._ensure_group()
        self._running = True
        self._task = asyncio.create_task(self._consume_loop(), name="db_writer")
        log.info("db_writer_started")

    async def _ensure_group(self) -> None:
        """Создать consumer group (idempotent)."""
        try:
            await self._redis.xgroup_create(PRICES_STREAM, GROUP, id="0", mkstream=True)
        except redis.ResponseError as err:
            if "BUSYGROUP" not in str(err):
                raise

    async def _consume_loop(self) -> None:
        while self._running:
            try:
                resp = await self._redis.xreadgroup(
                    GROUP, CONSUMER, {PRICES_STREAM: ">"},
                    count=BATCH_SIZE, block=BLOCK_MS,
                )
                if resp:
                    _, entries = resp[0]
                    await self._flush(entries)
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                log.error("db_writer_error", error=str(err))
                await asyncio.sleep(1)

    async def _flush(self, entries: list) -> None:
        records, ids = [], []
        for msg_id, fields in entries:
            ids.append(msg_id)
            record = self._to_record(fields)
            if record is not None:
                records.append(record)
        if records:
            try:
                await self._pool.copy_records_to_table(
                    "prices", records=records, columns=_COLUMNS,
                )
                self.rows_written += len(records)
            except Exception as err:  # noqa: BLE001
                # Один невалидный record (overflow / check constraint) валит
                # весь COPY — fallback на построчный INSERT, чтобы не терять
                # остальную пачку. Плохие записи логируются и пропускаются.
                log.warning("db_writer_batch_failed", error=str(err), batch_size=len(records))
                await self._insert_individually(records)
        if ids:
            await self._redis.xack(PRICES_STREAM, GROUP, *ids)

    async def _insert_individually(self, records: list[tuple]) -> None:
        """Fallback после провала COPY: INSERT по одной строке."""
        sql = (
            "INSERT INTO prices (time, exchange, symbol, bid, ask, "
            "bid_volume, ask_volume, latency_ms) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)"
        )
        ok = 0
        for rec in records:
            try:
                await self._pool.execute(sql, *rec)
                ok += 1
            except Exception as err:  # noqa: BLE001
                log.warning(
                    "price_record_rejected",
                    exchange=rec[1], symbol=rec[2],
                    bid=str(rec[3]), ask=str(rec[4]),
                    bid_volume=str(rec[5]) if rec[5] is not None else None,
                    ask_volume=str(rec[6]) if rec[6] is not None else None,
                    error=str(err),
                )
        self.rows_written += ok

    @staticmethod
    def _to_record(f: dict) -> tuple | None:
        """Преобразовать поля stream'а в кортеж для COPY (numeric → Decimal).

        Отсекает записи с явным переполнением precision БД, чтобы не валить
        весь batch. Цены сверяются с NUMERIC(18,8), объёмы — с NUMERIC(28,8).
        """
        try:
            ts = datetime.fromtimestamp(int(f["received_at"]) / 1000, tz=timezone.utc)
            bid = Decimal(f["bid"])
            ask = Decimal(f["ask"])
            bid_volume = Decimal(f["bid_volume"]) if f.get("bid_volume") else None
            ask_volume = Decimal(f["ask_volume"]) if f.get("ask_volume") else None
        except (KeyError, ValueError, InvalidOperation):
            return None

        if abs(bid) > _PRICE_MAX or abs(ask) > _PRICE_MAX:
            log.warning(
                "price_overflow_skipped",
                exchange=f.get("exchange"), symbol=f.get("symbol"),
                bid=str(bid), ask=str(ask),
            )
            return None
        if bid_volume is not None and abs(bid_volume) > _VOLUME_MAX:
            bid_volume = None
        if ask_volume is not None and abs(ask_volume) > _VOLUME_MAX:
            ask_volume = None

        try:
            latency_ms = int(f["latency_ms"]) if f.get("latency_ms") else None
        except (ValueError, TypeError):
            latency_ms = None

        return (
            ts,
            f["exchange"],
            f["symbol"],
            bid,
            ask,
            bid_volume,
            ask_volume,
            latency_ms,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        if self._redis is not None:
            await self._redis.aclose()
        log.info("db_writer_stopped", rows_written=self.rows_written)
