"""Kill switch через API Gateway (Фаза 13).

Состояние kill switch — единый ключ в Redis (`executor:kill_switch`). Семантика
fail-closed (`shared.redis_utils.kill_switch_engaged`): торговля разрешена только
при явном "0", отсутствие ключа = остановлено. Gateway его читает (GET) и
переключает (POST). Executor подхватывает значение из Redis перед каждой
возможностью, поэтому переключение применяется почти мгновенно (≤ 1 с) без
межсервисного HTTP-вызова.
"""
from __future__ import annotations

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import get_current_user
from redis_client import get_redis
from shared.redis_utils import KILL_SWITCH_KEY, kill_switch_engaged

log = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["killswitch"])


class KillSwitchRequest(BaseModel):
    active: bool
    reason: str = "manual"


@router.get("/killswitch")
async def get_killswitch(_user: str = Depends(get_current_user)) -> dict:
    """Состояние kill switch. Fail-closed, как в executor: нет ключа = активен."""
    r = await get_redis()
    value = await r.get(KILL_SWITCH_KEY)
    return {"active": kill_switch_engaged(value)}


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
