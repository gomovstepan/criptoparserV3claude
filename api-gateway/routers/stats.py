"""Агрегированная статистика для дашборда (Фаза 11).

- GET /api/v1/stats        — KPI (общий P&L, сделки сегодня, активные спреды, лучший спред)
- GET /api/v1/stats/pnl    — почасовая серия P&L за N часов (для графика)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from auth import get_current_user
from routers.pnl_sql import PNL_EVENTS
from shared.db import get_db_pool

router = APIRouter(prefix="/api/v1", tags=["stats"])


class StatsKPI(BaseModel):
    total_pnl: float
    trades_today: int
    pnl_today: float
    active_opportunities: int
    best_spread_pct: float


class PnlPoint(BaseModel):
    time: str
    pnl: float
    cumulative: float


class PnlSeries(BaseModel):
    hours: int
    points: list[PnlPoint]


@router.get("/stats")
async def get_stats(_user: str = Depends(get_current_user)) -> StatsKPI:
    pool = await get_db_pool()
    row = await pool.fetchrow(
        """
        SELECT
          (SELECT COALESCE(sum(net_pnl), 0) FROM trades)
            + (SELECT COALESCE(sum(change_amount), 0) FROM balance WHERE reason = 'rebalance')
            AS total_pnl,
          (SELECT count(*) FROM trades WHERE time >= date_trunc('day', now()))                  AS trades_today,
          (SELECT COALESCE(sum(net_pnl), 0) FROM trades WHERE time >= date_trunc('day', now()))
            + (SELECT COALESCE(sum(change_amount), 0) FROM balance WHERE reason = 'rebalance' AND time >= date_trunc('day', now()))
            AS pnl_today,
          (SELECT count(*) FROM opportunities WHERE time > now() - interval '5 minutes')         AS active_opportunities,
          -- Честный net (gross − taker-комиссии обеих ног), как в Opportunities UI.
          -- net_spread_pct display-only: завышает комиссию вывода ~40x.
          (SELECT COALESCE(max(gross_spread_pct - buy_fee_pct - sell_fee_pct), 0)
           FROM opportunities WHERE time > now() - interval '1 hour') AS best_spread
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
) -> PnlSeries:
    pool = await get_db_pool()
    # Серия обязана считать P&L так же, как KPI выше: сделки + движения ребаланса
    # (см. routers/pnl_sql.py). Иначе последняя точка графика расходится с числом
    # над ним. Бакет остаётся часовым и включает часы, где была только комиссия.
    rows = await pool.fetch(
        f"""
        SELECT time_bucket('1 hour', time) AS bucket, COALESCE(sum(pnl), 0) AS pnl
        FROM ({PNL_EVENTS.format(window="make_interval(hours => $1)")}) AS pnl_events
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
