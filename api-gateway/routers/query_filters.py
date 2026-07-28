"""Общий построитель WHERE-условий для роутеров (trades, opportunities).

Значения фильтров всегда уходят ПАРАМЕТРАМИ ($N) в asyncpg — в SQL-строку
интерполируются только номера плейсхолдеров. Единая реализация вместо
копий по роутерам: дрейф форматов фильтров ловится в одном месте.
"""
from __future__ import annotations


def build_filters(
    status: str | None = None,
    symbol: str | None = None,
    exchange: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> tuple[str, list[str]]:
    """Собрать ``WHERE``-строку и список параметров из заданных фильтров."""
    clauses: list[str] = []
    params: list[str] = []
    if status:
        params.append(status)
        clauses.append(f"status = ${len(params)}")
    if symbol:
        params.append(symbol)
        clauses.append(f"symbol = ${len(params)}")
    if exchange:
        params.append(exchange)
        clauses.append(f"(buy_exchange = ${len(params)} OR sell_exchange = ${len(params)})")
    if start:
        params.append(start)
        clauses.append(f"time >= ${len(params)}::timestamptz")
    if end:
        params.append(end)
        clauses.append(f"time <= ${len(params)}::timestamptz")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params
