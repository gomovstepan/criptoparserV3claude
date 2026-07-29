"""Утилиты для работы с Redis."""
from __future__ import annotations

import asyncio

import redis.asyncio as redis
import structlog

log = structlog.get_logger()

# Единственное имя ключа kill switch: его пишут gateway/бот/rebalance и читает
# executor. Копия литерала в каждом сервисе — это риск молчаливого рассинхрона
# при опечатке, тестов на равенство констант между сервисами нет.
KILL_SWITCH_KEY = "executor:kill_switch"


def kill_switch_engaged(value: str | None) -> bool:
    """Fail-closed семантика kill switch: торговля разрешена ТОЛЬКО при явном "0".

    Отсутствие ключа (eviction, flush, пустой Redis) означает СТОП, а не
    «разрешено»: раньше `value == "1"` превращала потерю ключа в молчаливое
    возобновление торговли. Ключ сидится executor'ом при старте.
    """
    return value != "0"


async def wait_until_ready(client: redis.Redis, timeout: float = 60.0, interval: float = 1.0) -> None:
    """Ждать, пока Redis закончит загрузку датасета (AOF/RDB).

    После старта контейнера Redis принимает соединения, но возвращает
    ``BusyLoadingError`` на любые команды, пока загружает данные с диска.
    Healthcheck ``redis-cli ping`` этот момент не ловит.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    attempt = 0
    while True:
        try:
            await client.ping()
            return
        except redis.BusyLoadingError:
            attempt += 1
            if asyncio.get_event_loop().time() >= deadline:
                raise
            log.info("redis_loading_dataset", attempt=attempt)
            await asyncio.sleep(interval)
