"""JWT-аутентификация и хеширование паролей (Фаза 9).

- JWT: HS256, срок жизни из настроек (по умолчанию 24h).
- Пароли: PBKDF2-HMAC-SHA256 (stdlib, без сторонних зависимостей).
- ``ensure_default_user`` создаёт тестового пользователя при первом старте.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.config import settings

ALGORITHM = "HS256"
PBKDF2_ITERATIONS = 200_000

DEFAULT_USER_EMAIL = os.getenv("DEFAULT_USER_EMAIL", "test@example.com")
DEFAULT_USER_PASSWORD = os.getenv("DEFAULT_USER_PASSWORD", "test123")

_bearer = HTTPBearer(auto_error=True)


# ── Пароли ────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iterations, salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return secrets.compare_digest(digest.hex(), expected)
    except (ValueError, AttributeError):
        return False


# ── JWT ───────────────────────────────────────────────────────────────────
def create_access_token(subject: str) -> tuple[str, int]:
    """Вернуть (token, expires_in_seconds)."""
    expires_in = settings.jwt_expiry_hours * 3600
    payload = {
        "sub": subject,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM), expires_in


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    """Зависимость FastAPI: проверяет JWT, возвращает email пользователя."""
    try:
        payload = decode_token(creds.credentials)
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или просроченный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Пользователь по умолчанию ─────────────────────────────────────────────
async def ensure_default_user(pool) -> None:
    exists = await pool.fetchval("SELECT 1 FROM users WHERE email = $1", DEFAULT_USER_EMAIL)
    if not exists:
        await pool.execute(
            "INSERT INTO users (email, password_hash, is_admin) VALUES ($1, $2, true)",
            DEFAULT_USER_EMAIL, hash_password(DEFAULT_USER_PASSWORD),
        )
