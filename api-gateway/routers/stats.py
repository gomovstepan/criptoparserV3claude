"""Агрегированная статистика для дашборда (Фаза 11).

- GET /api/v1/stats        — KPI (общий P&L, сделки сегодня, активные спреды, лучший спред)
- GET /api/v1/stats/pnl    — почасовая серия P&L за N часов (для графика)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from auth import get_current_user
from shared.db import get_db_pool

router = APIRouter(prefix="/api/v1", tags=["stats"])


@router.get("/stats")
async def get_stats(_user: str = Depends(get_current_user)) -> dict:
    pool = await get_db_pool()
    row = await pool.fetchrow(
        """
        SELECT
          (SELECT COALESCE(sum(net_pnl), 0) FROM trades)                                        AS total_pnl,
          (SELECT count(*) FROM trades WHERE time >= date_trunc('day', now()))                  AS trades_today,
          (SELECT COALESCE(sum(net_pnl), 0) FROM trades WHERE time >= date_trunc('day', now()))  AS pnl_today,
          (SELECT count(*) FROM opportunities WHERE time > now() - interval '5 minutes')         AS active_opportunities,
          (SELECT COALESCE(max(net_spread_pct), 0) FROM opportunities WHERE time > now() - interval '1 hour') AS best_spread
        """
    )
    return {
        "total_pnl": round(float(row["total_pnl"]), 2),
        "trades_today": int(row["trades_today"]),
        "pnl_today": round(float(row["pnl_today"]), 2),
        "active_opportunities": int(row["active_opportunities"]),
        "best_spread_pct": round(float(row["best_spread"]), 4),
    }


@router.get("/stats/pnl")
async def get_pnl_series(
    hours: int = Query(24, ge=1, le=168),
    _user: str = Depends(get_current_user),
) -> dict:
    pool = await get_db_pool()
    rows = await pool.fetch(
        """
        SELECT time_bucket('1 hour', time) AS bucket, COALESCE(sum(net_pnl), 0) AS pnl
        FROM trades
        WHERE time > now() - make_interval(hours => $1)
        GROUP BY bucket ORDER BY bucket
        """,
        hours,
    )
    points = []
    cumulative = 0.0
    for r in rows:
        cumulative += float(r["pnl"])
        points.append({
            "time": r["bucket"].isoformat(),
            "pnl": round(float(r["pnl"]), 2),
            "cumulative": round(cumulative, 2),
        })
    return {"hours": hours, "points": points}
