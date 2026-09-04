"""GET /api/v1/config — режим/флаги для фронтенда (paper и т.п.)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from auth import get_current_user
from shared.config import settings

router = APIRouter(prefix="/api/v1", tags=["config"])


@router.get("/config")
async def get_config(_user: str = Depends(get_current_user)) -> dict:
    return {"paper": bool(settings.paper)}
