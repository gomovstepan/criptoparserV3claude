"""GET /api/v1/exchanges, /exchanges/status и GET/PUT /api/v1/settings (Фазы 9, 11)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from auth import get_current_user
from shared.config import EXCHANGES
from shared.db import get_db_pool

log = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["exchanges"])

CONNECTED_THRESHOLD_SEC = 15


@router.get("/exchanges")
async def get_exchanges(_user: str = Depends(get_current_user)) -> dict:
    """Список бирж: is_active из БД, комиссии — из shared/config.py.

    Вся математика (scanner, executor) читает константы ``EXCHANGES``; колонки
    комиссий в ``exchange_configs`` — лишь сид первого запуска, который никем
    не обновляется. Раньше страница показывала значения из БД: правка комиссии
    в ``shared/config.py`` меняла все спреды на Opportunities, а Exchanges вечно
    отображала старый сид. Теперь витрина и математика физически не могут
    разойтись. Из БД остаётся только ``is_active`` — единственная колонка,
    которой реально управляют (PATCH ниже).
    """
    pool = await get_db_pool()
    rows = await pool.fetch("SELECT exchange, is_active FROM exchange_configs ORDER BY id")
    items = []
    for r in rows:
        cfg = EXCHANGES.get(r["exchange"])
        if cfg is None:
            # Строка есть в БД, но системе биржа неизвестна (ручной INSERT):
            # торговать ей collector/scanner всё равно не могут — не показываем.
            log.warning("exchange_row_unknown", exchange=r["exchange"])
            continue
        items.append({
            "exchange": cfg.name,
            "is_active": r["is_active"],
            "maker_fee_pct": cfg.maker_fee_pct,
            "taker_fee_pct": cfg.taker_fee_pct,
            "withdrawal_btc": cfg.withdrawal_btc,
            "withdrawal_usdt": cfg.withdrawal_usdt,
            "rate_limit_req_per_sec": cfg.rate_limit_req_per_sec,
        })
    return {"items": items, "total": len(items)}


class ExchangeUpdate(BaseModel):
    is_active: bool


@router.patch("/exchanges/{exchange}")
async def update_exchange(
    exchange: str,
    payload: ExchangeUpdate,
    _user: str = Depends(get_current_user),
) -> dict:
    """Включить/выключить биржу (toggle is_active).

    Меняет флаг в `exchange_configs`. Коллектор читает `is_active` при старте,
    поэтому фактическое подключение/отключение применится после его рестарта —
    флаг же сохраняется сразу и виден в списке бирж.
    """
    pool = await get_db_pool()
    row = await pool.fetchrow(
        "UPDATE exchange_configs SET is_active = $1 WHERE exchange = $2 "
        "RETURNING exchange, is_active",
        payload.is_active, exchange,
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"exchange '{exchange}' not found")
    return {"exchange": row["exchange"], "is_active": row["is_active"]}


@router.get("/exchanges/status")
async def get_exchange_status(_user: str = Depends(get_current_user)) -> dict:
    """Статус бирж по свежести последнего тика в TimescaleDB (для дашборда)."""
    pool = await get_db_pool()
    rows = await pool.fetch(
        """
        SELECT DISTINCT ON (exchange) exchange, time, latency_ms
        FROM prices
        WHERE time > now() - interval '2 minutes'
        ORDER BY exchange, time DESC
        """
    )
    latest = {r["exchange"]: r for r in rows}
    now = datetime.now(timezone.utc)
    items = []
    for exchange in EXCHANGES:
        r = latest.get(exchange)
        if r is None:
            items.append({"exchange": exchange, "status": "disconnected", "latency_ms": None, "last_tick": None})
            continue
        age = (now - r["time"]).total_seconds()
        items.append({
            "exchange": exchange,
            "status": "connected" if age < CONNECTED_THRESHOLD_SEC else "stale",
            "latency_ms": r["latency_ms"],
            "last_tick": r["time"].isoformat(),
        })
    return {"items": items}


def _parse_setting(raw: str):
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


@router.get("/settings")
async def get_settings(_user: str = Depends(get_current_user)) -> dict:
    pool = await get_db_pool()
    rows = await pool.fetch("SELECT key, value FROM settings")
    return {r["key"]: _parse_setting(r["value"]) for r in rows}


class SettingsUpdate(BaseModel):
    """Допустимые ключи `settings` и их границы (ТЗ, раздел 6.3.4).

    ``extra="forbid"`` — неизвестный ключ теперь 422, а не молчаливый no-op:
    раньше опечатка в имени ключа возвращала ``{"status": "updated"}``, ничего
    не изменив. Все поля Optional: форма шлёт объект целиком, а PATCH-семантика
    (обновляем только присланное) сохраняется через ``exclude_unset``.
    """

    model_config = ConfigDict(extra="forbid")

    # Только ключи, которые какой-то сервис реально читает. Бывшие мёртвые
    # настройки (slippage_tolerance_pct, execution_timeout_sec,
    # daily_loss_limit_pct) удалены и отсюда, и из формы (types.ts
    # SETTING_FIELDS) одновременно — их строки в таблице settings остаются как
    # legacy-сиды, но через API больше не изменяются.
    min_spread_pct: float | None = Field(None, ge=0.01, le=10.0)
    # ТЗ допускает le=100.0, но при 100% стоимость покупки вместе с комиссией
    # превышает баланс: Redis уходит в минус, а строка в hypertable клампится
    # до 0 (paper_trading.py) — Redis и БД начинают противоречить друг другу.
    # Поэтому потолок ниже спецификации.
    max_position_pct: float | None = Field(None, ge=1.0, le=50.0)
    notification_spread_threshold: float | None = Field(None, ge=0.01, le=10.0)
    notification_trade_min_pnl: float | None = Field(None, ge=0.0, le=1_000_000.0)
    estimated_trade_notional: float | None = Field(None, ge=1.0, le=10_000_000.0)
    rebalance_threshold_usd: float | None = Field(None, ge=0.0, le=10_000_000.0)
    # Гейты сейфти (этап «остановить убытки»). min_profit_usd допускает
    # отрицательные значения сознательно: в paper-режиме оператор может
    # временно разрешить мелкие минусы, чтобы наблюдать поток сделок.
    min_profit_usd: float | None = Field(None, ge=-1_000.0, le=1_000_000.0)
    loss_cooldown_sec: float | None = Field(None, ge=0.0, le=86_400.0)
    min_net_spread_pct: float | None = Field(None, ge=0.0, le=10.0)
    depth_max_age_ms_executor: float | None = Field(None, ge=500.0, le=60_000.0)
    depth_max_age_ms_scanner: float | None = Field(None, ge=500.0, le=60_000.0)


@router.put("/settings")
async def update_settings(
    payload: SettingsUpdate,
    _user: str = Depends(get_current_user),
) -> dict:
    """Обновить настройки. Возвращает реально изменённые ключи, а не эхо запроса."""
    values = payload.model_dump(exclude_unset=True, exclude_none=True)
    pool = await get_db_pool()
    updated: dict = {}
    for key, value in values.items():
        status = await pool.execute(
            "UPDATE settings SET value = $1::jsonb, updated_at = now() WHERE key = $2",
            json.dumps(value), key,
        )
        # asyncpg возвращает "UPDATE N" — 0 означает, что строки в таблице нет
        # (например, БД поднята из старого init-db.sql без этого ключа).
        if status and status.split()[-1] != "0":
            updated[key] = value
    missing = sorted(set(values) - set(updated))
    return {"status": "updated", "settings": updated, "not_found": missing}
