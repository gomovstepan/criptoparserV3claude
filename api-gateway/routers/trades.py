"""GET /api/v1/trades — paper trades с пагинацией, фильтрами и CSV-экспортом (Фазы 9, 12)."""
from __future__ import annotations

import csv
import io
from math import ceil

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from auth import get_current_user
from routers.query_filters import build_filters as _build_filters
from shared.db import get_db_pool

router = APIRouter(prefix="/api/v1", tags=["trades"])


class TradeOut(BaseModel):
    """Строка сделки — зеркало ``_row_to_dict`` (и схема в OpenAPI)."""

    id: str
    opportunity_id: str
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    amount: float
    buy_fee: float
    sell_fee: float
    slippage_cost: float
    gross_pnl: float
    net_pnl: float
    buy_top_ask: float | None
    sell_top_bid: float | None
    status: str
    executed_at: str
    duration_ms: int | None


class TradesPage(BaseModel):
    items: list[TradeOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class TradesDeleteResult(BaseModel):
    deleted: int
    truncated: bool

# Колонки, которые отдаём наружу (и в JSON, и в CSV). Разложение
# gross → slippage → fees → net обязано доезжать до фронта целиком:
# без него цифры в карточке сделки не сходятся (K4).
_COLUMNS = (
    "time, id, opportunity_id, symbol, buy_exchange, sell_exchange, buy_price, "
    "sell_price, amount, buy_fee, sell_fee, slippage_cost, gross_pnl, net_pnl, "
    "buy_top_ask, sell_top_bid, status, duration_ms"
)


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
        "buy_fee": float(r["buy_fee"]),
        "sell_fee": float(r["sell_fee"]),
        "slippage_cost": float(r["slippage_cost"]),
        "gross_pnl": float(r["gross_pnl"]),
        "net_pnl": float(r["net_pnl"]),
        # Nullable: сделки до миграции top-цен не имеют.
        "buy_top_ask": float(r["buy_top_ask"]) if r["buy_top_ask"] is not None else None,
        "sell_top_bid": float(r["sell_top_bid"]) if r["sell_top_bid"] is not None else None,
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
) -> TradesPage:
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
) -> TradesDeleteResult:
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

    header = [
        "executed_at", "id", "opportunity_id", "symbol", "buy_exchange", "sell_exchange",
        "buy_price", "sell_price", "amount", "buy_fee", "sell_fee", "slippage_cost",
        "gross_pnl", "net_pnl", "buy_top_ask", "sell_top_bid", "status", "duration_ms",
    ]
    # Сериализация до 200k строк — CPU-bound: в треде, иначе она блокирует
    # event loop (включая /ws-броадкастеры) на всё время выгрузки.
    content = await run_in_threadpool(_rows_to_csv, rows, header)

    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trades.csv"},
    )


def _rows_to_csv(rows, header: list[str]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for r in rows:
        d = _row_to_dict(r)
        writer.writerow([d[k] for k in header])
    return buf.getvalue()
