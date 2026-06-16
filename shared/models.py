"""Pydantic-модели общих сущностей системы.

Эти модели — контракт данных между сервисами (формат в Redis Streams и в БД):
- ``PriceTick``    — тик цены от collector'а (stream ``prices``);
- ``Opportunity``  — арбитражная возможность от scanner'а (stream ``opportunities``);
- ``Trade``        — результат paper-сделки от executor'а (stream ``trades``);
- ``ExchangeInfo`` — конфиг биржи для REST API.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PriceTick(BaseModel):
    """Лучший bid/ask с одной биржи в один момент времени.

    Формат соответствует ТЗ (раздел 2.1) и полям Redis Stream ``prices``.
    """

    exchange: str
    symbol: str
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    bid_volume: float | None = None
    ask_volume: float | None = None
    timestamp: int          # время с биржи, unix ms
    received_at: int        # время получения collector'ом, unix ms
    latency_ms: int = 0

    def to_redis(self) -> dict[str, str]:
        """Плоский dict строк для ``XADD`` (Redis Stream хранит только строки)."""
        return {
            "exchange": self.exchange,
            "symbol": self.symbol,
            "bid": repr(self.bid),
            "ask": repr(self.ask),
            "bid_volume": repr(self.bid_volume) if self.bid_volume is not None else "",
            "ask_volume": repr(self.ask_volume) if self.ask_volume is not None else "",
            "timestamp": str(self.timestamp),
            "received_at": str(self.received_at),
            "latency_ms": str(self.latency_ms),
        }


class Opportunity(BaseModel):
    """Обнаруженная межбиржевая арбитражная возможность (формат ТЗ, раздел 2.2)."""

    id: str
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float = Field(gt=0)
    sell_price: float = Field(gt=0)
    gross_spread_pct: float
    buy_fee_pct: float
    sell_fee_pct: float
    withdrawal_fee_usd: float = 0.0
    net_spread_pct: float
    detected_at: int        # unix ms
    ttl_seconds: int = 5

    def to_redis(self) -> dict[str, str]:
        """Плоский dict строк для ``XADD opportunities``."""
        return {k: str(v) for k, v in self.model_dump().items()}

    @classmethod
    def from_redis(cls, data: dict) -> "Opportunity":
        """Собрать из полей Redis Stream (pydantic приведёт строки к типам)."""
        return cls(**data)


class Trade(BaseModel):
    """Результат симуляции paper-сделки (формат ТЗ, раздел 2.4)."""

    id: str
    opportunity_id: str
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    amount: float
    buy_fee: float = 0.0
    sell_fee: float = 0.0
    withdrawal_fee: float = 0.0
    slippage_cost: float = 0.0
    gross_pnl: float
    net_pnl: float
    status: Literal["pending", "completed", "failed", "cancelled"] = "pending"
    executed_at: int | None = None
    duration_ms: int | None = None

    def to_redis(self) -> dict[str, str]:
        """Плоский dict строк для ``XADD trades`` (None → пустая строка)."""
        return {k: ("" if v is None else str(v)) for k, v in self.model_dump().items()}

    @classmethod
    def from_redis(cls, data: dict) -> "Trade":
        """Собрать из полей Redis Stream (пустая строка → None)."""
        clean = {k: (None if v == "" else v) for k, v in data.items()}
        return cls(**clean)


class ExchangeInfo(BaseModel):
    """Конфиг биржи для отдачи через REST API / дашборд."""

    exchange: str
    is_active: bool = True
    maker_fee_pct: float
    taker_fee_pct: float
    withdrawal_btc: float | None = None
    withdrawal_usdt: float | None = None
    rate_limit_req_per_sec: int | None = None
