"""Конфигурация системы: переменные окружения и статические данные 7 бирж.

- ``Settings`` — значения из ``.env`` (хост/порт Redis и TimescaleDB, секреты).
- ``EXCHANGES`` — справочник 7 поддерживаемых бирж (комиссии, лимиты, CCXT id).

Данные бирж здесь — источник правды для seed'ов в ``scripts/init-db.sql`` и для
collector'а. Числа по комиссиям соответствуют таблице из ТЗ (раздел 2.2).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Переменные окружения. Имена совпадают с ключами в ``.env`` (регистр игнорируется)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # ── TimescaleDB ──
    postgres_host: str = "timescaledb"
    postgres_port: int = 5432
    postgres_user: str = "arbitrage"
    postgres_password: str = ""
    postgres_db: str = "arbitrage_db"

    # ── Redis ──
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""

    # ── Порты сервисов ──
    api_gateway_port: int = 8000
    collector_port: int = 8001
    scanner_port: int = 8002
    executor_port: int = 8003
    notifier_port: int = 8004

    # ── Auth ──
    jwt_secret: str = ""
    jwt_expiry_hours: int = 24
    cors_origins: str = "http://localhost:5173"

    # ── Telegram ──
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # ── Tracked pairs (collector) ──
    tracked_symbols: str = "BTC/USDT,ETH/USDT"

    # ── Trading mode ──
    # true — paper (executor симулирует сделки на виртуальных балансах),
    # false — реальная торговля (не реализована, executor отключён).
    paper: bool = True

    @property
    def database_dsn(self) -> str:
        """DSN для asyncpg."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """URL для redis-py."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/0"


@dataclass(frozen=True)
class ExchangeConfig:
    """Статические данные одной биржи."""

    name: str               # ключ внутри системы (binance, bybit, ...)
    ccxt_id: str            # идентификатор в библиотеке CCXT
    maker_fee_pct: float    # комиссия maker, %
    taker_fee_pct: float    # комиссия taker, %
    withdrawal_btc: float   # фикс. комиссия вывода BTC
    withdrawal_usdt: float  # фикс. комиссия вывода USDT (TRC20)
    rate_limit_req_per_sec: int
    is_active: bool = True


# Справочник 7 бирж MVP. Комиссии — из ТЗ (раздел 2.2).
# Прим.: в актуальной CCXT идентификатор Gate.io — "gate".
EXCHANGES: dict[str, ExchangeConfig] = {
    "bybit":   ExchangeConfig("bybit",   "bybit",   0.10, 0.10, 0.000085, 1.0, 50),
    "binance": ExchangeConfig("binance", "binance", 0.10, 0.10, 0.0005,   0.0, 1200),
    "kucoin":  ExchangeConfig("kucoin",  "kucoin",  0.10, 0.10, 0.0,      0.0, 200),
    "gateio":  ExchangeConfig("gateio",  "gate",    0.30, 0.30, 0.001,    1.0, 200),
    "bitget":  ExchangeConfig("bitget",  "bitget",  0.10, 0.10, 0.0003,   1.0, 20),
    "coinex":  ExchangeConfig("coinex",  "coinex",  0.20, 0.20, 0.0001,   1.0, 10),
    "bingx":   ExchangeConfig("bingx",   "bingx",   0.10, 0.10, 0.00035,  1.0, 24),
}


def get_exchange(name: str) -> ExchangeConfig:
    """Вернуть конфиг биржи по системному имени (KeyError, если нет)."""
    return EXCHANGES[name]


# Единый экземпляр настроек для импорта в сервисы.
settings = Settings()
