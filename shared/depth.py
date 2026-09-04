"""Глубина стакана (market depth): формат хранения и VWAP-расчёты.

Collector пишет топ-N уровней стакана в Redis-ключ ``depth:{exchange}:{symbol}``
(JSON, TTL 10 с). Scanner и executor читают его и симулируют исполнение
проходом по уровням: покупка «съедает» asks снизу вверх, продажа — bids
сверху вниз. Если книга не покрывает объём — исполнение невозможно (None).

Формат JSON: {"ts": unix_ms, "bids": [[price, qty], ...], "asks": [[price, qty], ...]}
``ts`` — локальное время коллектора; свежесть = now - ts <= DEPTH_MAX_AGE_MS.
"""
from __future__ import annotations

import json

DEPTH_LEVELS = 10          # уровней с каждой стороны
DEPTH_TTL_SEC = 10         # жёсткий TTL ключа в Redis
DEPTH_MAX_AGE_MS = 5_000   # мягкий порог свежести для scanner/executor

_EPS = 1e-9


def depth_key(exchange: str, symbol: str) -> str:
    return f"depth:{exchange}:{symbol}"


def dump_depth(bids: list, asks: list, ts: int, levels: int = DEPTH_LEVELS) -> str:
    """JSON топ-``levels`` уровней для записи в Redis."""
    return json.dumps({
        "ts": ts,
        "bids": [[float(p), float(q)] for p, q, *_ in bids[:levels]],
        "asks": [[float(p), float(q)] for p, q, *_ in asks[:levels]],
    })


def parse_depth(raw: str | None) -> dict | None:
    """Распарсить JSON из Redis; None при отсутствии/мусоре/пустой книге."""
    if not raw:
        return None
    try:
        d = json.loads(raw)
        if not d.get("bids") or not d.get("asks"):
            return None
        return {"ts": int(d["ts"]), "bids": d["bids"], "asks": d["asks"]}
    except (ValueError, KeyError, TypeError):
        return None


def is_fresh(depth: dict | None, now_ms: int, max_age_ms: int = DEPTH_MAX_AGE_MS) -> bool:
    return depth is not None and (now_ms - depth["ts"]) <= max_age_ms


def walk_asks_for_notional(asks: list, notional_usd: float) -> tuple[float, float] | None:
    """Купить на ``notional_usd`` USDT, съедая asks снизу вверх.

    Возвращает (amount_base, vwap_price) или None, если глубины не хватает.
    """
    if notional_usd <= 0:
        return None
    remaining = notional_usd
    amount = 0.0
    for price, qty in asks:
        price, qty = float(price), float(qty)
        if price <= 0 or qty <= 0:
            continue
        level_cost = price * qty
        if level_cost >= remaining:
            amount += remaining / price
            remaining = 0.0
            break
        amount += qty
        remaining -= level_cost
    if remaining > _EPS * notional_usd or amount <= 0:
        return None
    return amount, notional_usd / amount


def walk_bids_for_amount(bids: list, amount_base: float) -> float | None:
    """Продать ``amount_base`` базового актива, съедая bids сверху вниз.

    Возвращает vwap_price или None, если глубины не хватает.
    """
    if amount_base <= 0:
        return None
    remaining = amount_base
    proceeds = 0.0
    for price, qty in bids:
        price, qty = float(price), float(qty)
        if price <= 0 or qty <= 0:
            continue
        take = qty if qty < remaining else remaining
        proceeds += take * price
        remaining -= take
        if remaining <= 0:
            break
    if remaining > _EPS * amount_base:
        return None
    return proceeds / amount_base
