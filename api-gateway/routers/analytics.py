"""Аналитика по сделкам для страницы Analytics (Фаза 12).

GET /api/v1/analytics/pnl?days=N — агрегаты за период + дневная серия:
- сводка: total_trades, win_rate, total_gross_pnl, total_net_pnl,
  avg_net_pnl, avg_trade_duration_ms, best_trade, worst_trade;
- daily[]: по дням — trades, net_pnl, gross_pnl + накопительный cumulative_net_pnl.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from auth import get_current_user
from shared.db import get_db_pool

router = APIRouter(prefix="/api/v1", tags=["analytics"])


@router.get("/analytics/pnl")
async def analytics_pnl(
    days: int = Query(7, ge=1, le=365),
    _user: str = Depends(get_current_user),
) -> dict:
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

    rows = await pool.fetch(
        """
        SELECT time_bucket('1 day', time) AS day,
               count(*)                    AS trades,
               COALESCE(sum(net_pnl), 0)   AS net_pnl,
               COALESCE(sum(gross_pnl), 0) AS gross_pnl
        FROM trades
        WHERE time > now() - make_interval(days => $1)
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
        "total_net_pnl": round(float(summary["total_net_pnl"]), 2),
        "avg_net_pnl": round(float(summary["avg_net_pnl"]), 2),
        "avg_trade_duration_ms": int(float(summary["avg_duration_ms"])),
        "best_trade": round(float(summary["best_trade"]), 2),
        "worst_trade": round(float(summary["worst_trade"]), 2),
        "daily": daily,
    }
