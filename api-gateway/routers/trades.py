"""GET /api/v1/trades — paper trades с пагинацией, фильтрами и CSV-экспортом (Фазы 9, 12)."""
from __future__ import annotations

import csv
import io
from math import ceil

from fastapi import APIRouter, Depends, Query, Response

from auth import get_current_user
from shared.db import get_db_pool

router = APIRouter(prefix="/api/v1", tags=["trades"])

# Колонки, которые отдаём наружу (и в JSON, и в CSV).
_COLUMNS = (
    "time, id, opportunity_id, symbol, buy_exchange, sell_exchange, buy_price, "
    "sell_price, amount, gross_pnl, net_pnl, status, duration_ms"
)


def _build_filters(
    status: str | None, symbol: str | None, exchange: str | None,
    start: str | None, end: str | None,
) -> tuple[str, list]:
    """Собрать ``WHERE`` и параметры из фильтров (общая логика list/export)."""
    clauses: list[str] = []
    params: list = []
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


def _row_to_dict(r) -> dict:
    return {
        "id": r["id"],
        "opportunity_id": r["opportunity_id"],
        "symbol": r["symbol"],
        "buy_exchange": r["buy_exchange"],
        "sell_exchange": r["sell_exchange"],
        "buy_price": float(r["buy_price"]),
        "sell_price": float(r["sell_price"]),
        "amount": float(r["amount"]),
        "gross_pnl": float(r["gross_pnl"]),
        "net_pnl": float(r["net_pnl"]),
        "status": r["status"],
        "executed_at": r["time"].isoformat(),
        "duration_ms": r["duration_ms"],
    }


@router.get("/trades")
async def get_trades(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: str | None = None,
    symbol: str | None = None,
    exchange: str | None = None,
    start: str | None = None,
    end: str | None = None,
    _user: str = Depends(get_current_user),
) -> dict:
    where, params = _build_filters(status, symbol, exchange, start, end)

    pool = await get_db_pool()
    total = await pool.fetchval(f"SELECT count(*) FROM trades {where}", *params)

    offset = (page - 1) * page_size
    rows = await pool.fetch(
        f"SELECT {_COLUMNS} FROM trades {where} "
        f"ORDER BY time DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}",
        *params, page_size, offset,
    )
    return {
        "items": [_row_to_dict(r) for r in rows],
        "total": int(total or 0),
        "page": page,
        "page_size": page_size,
        "total_pages": ceil((total or 0) / page_size) if total else 0,
    }


@router.delete("/trades")
async def delete_trades(
    status: str | None = None,
    symbol: str | None = None,
    exchange: str | None = None,
    start: str | None = None,
    end: str | None = None,
    _user: str = Depends(get_current_user),
) -> dict:
    """Удалить сделки по фильтрам; без фильтров — TRUNCATE всей таблицы."""
    where, params = _build_filters(status, symbol, exchange, start, end)
    pool = await get_db_pool()
    if where:
        status_str = await pool.execute(f"DELETE FROM trades {where}", *params)
        # asyncpg возвращает "DELETE N"
        deleted = int(status_str.split()[-1]) if status_str else 0
        return {"deleted": deleted, "truncated": False}

    total = await pool.fetchval("SELECT count(*) FROM trades")
    await pool.execute("TRUNCATE TABLE trades")
    return {"deleted": int(total or 0), "truncated": True}


@router.get("/trades/export")
async def export_trades(
    status: str | None = None,
    symbol: str | None = None,
    exchange: str | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int = Query(50000, ge=1, le=200000),
    _user: str = Depends(get_current_user),
) -> Response:
    """Выгрузка отфильтрованных сделок в CSV (для кнопки Export на фронте)."""
    where, params = _build_filters(status, symbol, exchange, start, end)
    pool = await get_db_pool()
    rows = await pool.fetch(
        f"SELECT {_COLUMNS} FROM trades {where} ORDER BY time DESC LIMIT ${len(params) + 1}",
        *params, limit,
    )

    buf = io.StringIO()
    header = [
        "executed_at", "id", "opportunity_id", "symbol", "buy_exchange", "sell_exchange",
        "buy_price", "sell_price", "amount", "gross_pnl", "net_pnl", "status", "duration_ms",
    ]
    writer = csv.writer(buf)
    writer.writerow(header)
    for r in rows:
        d = _row_to_dict(r)
        writer.writerow([d[k] for k in header])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trades.csv"},
    )
