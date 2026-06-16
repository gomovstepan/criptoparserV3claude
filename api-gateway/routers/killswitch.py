"""Kill switch через API Gateway (Фаза 13).

Состояние kill switch — единый ключ в Redis (`executor:kill_switch`, "1"/"0").
Gateway его читает (GET) и переключает (POST). Executor подхватывает значение из
Redis в начале каждой итерации торгового цикла, поэтому переключение применяется
почти мгновенно (≤ 1 с) без межсервисного HTTP-вызова.
"""
from __future__ import annotations

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import get_current_user
from redis_client import get_redis

log = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["killswitch"])

KILL_SWITCH_KEY = "executor:kill_switch"


class KillSwitchRequest(BaseModel):
    active: bool
    reason: str = "manual"


@router.get("/killswitch")
async def get_killswitch(_user: str = Depends(get_current_user)) -> dict:
    r = await get_redis()
    value = await r.get(KILL_SWITCH_KEY)
    return {"active": value == "1"}


@router.post("/killswitch")
async def set_killswitch(
    req: KillSwitchRequest,
    _user: str = Depends(get_current_user),
) -> dict:
    r = await get_redis()
    await r.set(KILL_SWITCH_KEY, "1" if req.active else "0")
    log.warning("killswitch_set", active=req.active, reason=req.reason)
    return {
        "active": req.active,
        "reason": req.reason,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
