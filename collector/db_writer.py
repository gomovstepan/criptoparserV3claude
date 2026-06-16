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
BATCH_SIZE = 100
BLOCK_MS = 1000  # максимум 1 секунда ожидания пачки

_COLUMNS = ["time", "exchange", "symbol", "bid", "ask", "bid_volume", "ask_volume", "latency_ms"]


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
            await self._pool.copy_records_to_table("prices", records=records, columns=_COLUMNS)
            self.rows_written += len(records)
        if ids:
            await self._redis.xack(PRICES_STREAM, GROUP, *ids)

    @staticmethod
    def _to_record(f: dict) -> tuple | None:
        """Преобразовать поля stream'а в кортеж для COPY (numeric → Decimal)."""
        try:
            ts = datetime.fromtimestamp(int(f["received_at"]) / 1000, tz=timezone.utc)
            return (
                ts,
                f["exchange"],
                f["symbol"],
                Decimal(f["bid"]),
                Decimal(f["ask"]),
                Decimal(f["bid_volume"]) if f.get("bid_volume") else None,
                Decimal(f["ask_volume"]) if f.get("ask_volume") else None,
                int(f["latency_ms"]) if f.get("latency_ms") else None,
            )
        except (KeyError, ValueError, InvalidOperation):
            return None

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        if self._redis is not None:
            await self._redis.aclose()
        log.info("db_writer_stopped", rows_written=self.rows_written)
