"""Аутентификация: POST /api/v1/auth/login → JWT (Фаза 9)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from auth import create_access_token, verify_password
from shared.db import get_db_pool

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    pool = await get_db_pool()
    row = await pool.fetchrow(
        "SELECT email, password_hash FROM users WHERE email = $1 AND is_active = true",
        req.email,
    )
    if row is None or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверные учётные данные")
    token, expires_in = create_access_token(row["email"])
    return TokenResponse(access_token=token, expires_in=expires_in)
