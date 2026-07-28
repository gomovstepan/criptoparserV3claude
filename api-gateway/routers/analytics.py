"""Аналитика по сделкам для страницы Analytics (Фаза 12).

GET /api/v1/analytics/pnl?days=N — агрегаты за период + дневная серия:
- сводка: total_trades, win_rate, total_gross_pnl, total_net_pnl,
  avg_net_pnl, avg_trade_duration_ms, best_trade, worst_trade;
- daily[]: по дням — trades, net_pnl, gross_pnl + накопительный cumulative_net_pnl.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from auth import get_current_user
from routers.pnl_sql import PNL_EVENTS
from shared.db import get_db_pool

router = APIRouter(prefix="/api/v1", tags=["analytics"])


class DailyPnl(BaseModel):
    date: str
    trades: int
    net_pnl: float
    gross_pnl: float
    cumulative_net_pnl: float


class AnalyticsPnl(BaseModel):
    period: str
    days: int
    total_trades: int
    winning_trades: int
    win_rate: float
    total_gross_pnl: float
    total_net_pnl: float
    avg_net_pnl: float
    avg_trade_duration_ms: int
    best_trade: float
    worst_trade: float
    daily: list[DailyPnl]


@router.get("/analytics/pnl")
async def analytics_pnl(
    days: int = Query(7, ge=1, le=365),
    _user: str = Depends(get_current_user),
) -> AnalyticsPnl:
    pool = await get_db_pool()

    summary = await pool.fetchrow(
        """
        SELECT
          count(*)                                              AS total_trades,
          count(*) FILTER (WHERE net_pnl > 0)                   AS winning_trades,
          COALESCE(sum(gross_pnl), 0)                           AS total_gross_pnl,
          COALESCE(sum(net_pnl), 0)                             AS total_net_pnl,
          COALESCE(avg(net_pnl), 0)                             AS avg_net_pnl,
          COALESCE(avg(duration_ms), 0)                         AS avg_duration_ms,
          COALESCE(max(net_pnl), 0)                             AS best_trade,
          COALESCE(min(net_pnl), 0)                             AS worst_trade
        FROM trades
        WHERE time > now() - make_interval(days => $1)
        """,
        days,
    )

    rebalance_fees = await pool.fetchval(
        """
        SELECT COALESCE(sum(change_amount), 0)
        FROM balance
        WHERE reason = 'rebalance' AND time > now() - make_interval(days => $1)
        """,
        days,
    )

    # Дневная серия считает net_pnl по тому же определению, что и total_net_pnl
    # ниже: сделки + движения ребаланса (routers/pnl_sql.py). Счётчик сделок и
    # gross_pnl остаются только по сделкам — ребаланс это не сделка.
    rows = await pool.fetch(
        f"""
        SELECT time_bucket('1 day', time)          AS day,
               count(*) FILTER (WHERE is_trade)    AS trades,
               COALESCE(sum(pnl), 0)               AS net_pnl,
               COALESCE(sum(gross_pnl), 0)         AS gross_pnl
        FROM ({PNL_EVENTS.format(window="make_interval(days => $1)")}) AS pnl_events
        GROUP BY day ORDER BY day
        """,
        days,
    )

    daily = []
    cumulative = 0.0
    for r in rows:
        cumulative += float(r["net_pnl"])
        daily.append({
            "date": r["day"].date().isoformat(),
            "trades": int(r["trades"]),
            "net_pnl": round(float(r["net_pnl"]), 2),
            "gross_pnl": round(float(r["gross_pnl"]), 2),
            "cumulative_net_pnl": round(cumulative, 2),
        })

    total_trades = int(summary["total_trades"])
    winning = int(summary["winning_trades"])
    win_rate = round(winning / total_trades * 100, 1) if total_trades else 0.0

    return {
        "period": f"{days}d",
        "days": days,
        "total_trades": total_trades,
        "winning_trades": winning,
        "win_rate": win_rate,
        "total_gross_pnl": round(float(summary["total_gross_pnl"]), 2),
        "total_net_pnl": round(float(summary["total_net_pnl"]) + float(rebalance_fees), 2),
        "avg_net_pnl": round(float(summary["avg_net_pnl"]), 2),
        "avg_trade_duration_ms": int(float(summary["avg_duration_ms"])),
        "best_trade": round(float(summary["best_trade"]), 2),
        "worst_trade": round(float(summary["worst_trade"]), 2),
        "daily": daily,
    }
