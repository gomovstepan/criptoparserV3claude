"""Движок paper-trading (Фаза 7 + глубина стакана + гейты сейфти).

Симулирует исполнение арбитражной возможности проходом по глубине стакана:
покупка «съедает» asks buy-биржи снизу вверх на плановый notional, продажа
съедает bids sell-биржи на полученный amount. Фактические цены исполнения —
VWAP уровней. Если глубины нет или она устарела — сделка пропускается.
Размер позиции — max_position_pct% от текущего баланса buy-биржи. Kill switch
мгновенно останавливает создание новых сделок.

Гейты (в порядке применения, до какой-либо мутации состояния):
возраст opportunity → кулдаун после убыточной оценки → свежесть глубины →
баланс/ребаланс → notional → глубина стакана → ГЕЙТ ПРИБЫЛЬНОСТИ.
Последний — главный сейфти: net_pnl считается по реальным VWAP до движения
балансов, и сделка с net_pnl ниже min_profit_usd не исполняется. Это же место
станет обязательным гейтом реальной торговли.
"""
from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass

import redis.asyncio as redis
import structlog
from prometheus_client import Counter

from balance import get_balance, update_balance
from pnl import settle_trade
from rebalance import RebalanceResult, maybe_rebalance
from shared.depth import (
    depth_key, first_valid_price, is_fresh, parse_depth,
    walk_asks_for_notional, walk_bids_for_amount,
)
from shared.models import Opportunity, Trade

MIN_NOTIONAL_USDT = 10.0  # сделки меньше — пропускаем (недостаточно средств)

_log = structlog.get_logger()

# Причины скипов — отдельным счётчиком: по нему видно, что именно душит поток
# сделок (устаревшая глубина? кулдаун? убыточность?) без grep'а по логам.
_skips = Counter("trades_skipped_total", "Пропущенные возможности по причинам", ["reason"])


def _skip(reason: str, **kw) -> None:
    _log.info(f"trade_skipped_{reason}", **kw)
    _skips.labels(reason=reason).inc()


@dataclass
class ExecutionResult:
    # trade=None — сделка не состоялась, но ребаланс уже случился и подвинул
    # Redis-балансы: его движение обязано попасть в hypertable balance,
    # иначе ledger разойдётся с Redis, а P&L завысится на комиссию вывода.
    trade: Trade | None
    balance_updates: list[tuple[str, float, float]]  # (exchange, new_balance, change)
    rebalance: RebalanceResult | None = None


class PaperTradingEngine:
    def __init__(self, redis_client: redis.Redis, max_position_pct: float = 10.0,
                 rebalance_threshold: float = 100.0, min_profit_usd: float = 0.0,
                 loss_cooldown_sec: float = 60.0, depth_max_age_ms: float = 2000.0) -> None:
        self._redis = redis_client
        self.max_position_pct = max_position_pct
        self.rebalance_threshold = rebalance_threshold
        # Гейт прибыльности: сделки с net_pnl ниже порога не исполняются.
        self.min_profit_usd = min_profit_usd
        # После убыточной оценки конфигурация (symbol, buy, sell) замолкает на
        # этот срок — иначе dedup 5с превращает устойчивый плохой спред в поток
        # переоценок. 0 — кулдаун выключен.
        self.loss_cooldown_sec = loss_cooldown_sec
        # Порог свежести стакана ДЛЯ ИСПОЛНЕНИЯ — строже сканерного: здесь
        # коммитятся деньги, а ложный скип бесплатен (спред перевыпустится).
        self.depth_max_age_ms = depth_max_age_ms
        self.kill_switch = False

    # ── Гейты: каждый логирует свою причину скипа и инкрементит счётчик ──

    @staticmethod
    def _expired(opp: Opportunity, now_ms: int) -> bool:
        """Гейт возраста: opportunity живёт ttl_seconds (сеется сканером, 5с).

        Без него после простоя executor исполнил бы весь накопленный бэклог
        по текущим ценам — покупая спред, которого давно нет.
        """
        age_ms = now_ms - opp.detected_at
        if age_ms > opp.ttl_seconds * 1000:
            _skip("expired", symbol=opp.symbol, buy_ex=opp.buy_exchange,
                  sell_ex=opp.sell_exchange, age_ms=age_ms)
            return True
        return False

    async def _in_cooldown(self, opp: Opportunity, cooldown_key: str, cooldown_ttl: int) -> bool:
        """Кулдаун связки после убыточной оценки (0 — выключен)."""
        if cooldown_ttl > 0 and await self._redis.get(cooldown_key):
            _skip("cooldown", symbol=opp.symbol, buy_ex=opp.buy_exchange,
                  sell_ex=opp.sell_exchange)
            return True
        return False

    async def _fresh_depth(self, opp: Opportunity, now_ms: int) -> tuple[dict, dict] | None:
        """Книги обеих ног, если обе свежи (порог depth_max_age_ms); иначе None.

        Свежесть проверяется ДО ребаланса: комиссия вывода не должна
        списываться ради возможности, которую отбраковывает мёртвый стакан.
        """
        raw_buy, raw_sell = await self._redis.mget([
            depth_key(opp.buy_exchange, opp.symbol),
            depth_key(opp.sell_exchange, opp.symbol),
        ])
        buy_depth, sell_depth = parse_depth(raw_buy), parse_depth(raw_sell)
        if not is_fresh(buy_depth, now_ms, self.depth_max_age_ms) \
                or not is_fresh(sell_depth, now_ms, self.depth_max_age_ms):
            _skip("stale_depth", symbol=opp.symbol, buy_ex=opp.buy_exchange,
                  sell_ex=opp.sell_exchange)
            return None
        return buy_depth, sell_depth

    @staticmethod
    def _build_trade(opp: Opportunity, amount: float, effective_buy: float,
                     effective_sell: float, pnl, top_ask: float, top_bid: float,
                     start: float) -> Trade:
        now = int(time.time() * 1000)
        return Trade(
            id=f"trade_{now}_{uuid.uuid4().hex[:8]}",
            opportunity_id=opp.id,
            symbol=opp.symbol,
            buy_exchange=opp.buy_exchange,
            sell_exchange=opp.sell_exchange,
            buy_price=effective_buy,
            sell_price=effective_sell,
            amount=amount,
            buy_fee=pnl.buy_fee,
            sell_fee=pnl.sell_fee,
            withdrawal_fee=0.0,   # списывается один раз при ребалансе, не за сделку
            slippage_cost=pnl.slippage_cost,
            gross_pnl=pnl.gross_pnl,
            net_pnl=pnl.net_pnl,
            buy_top_ask=top_ask,
            sell_top_bid=top_bid,
            status="completed",
            executed_at=now,
            duration_ms=int((time.time() - start) * 1000),
        )

    async def execute_opportunity(self, opp: Opportunity) -> ExecutionResult | None:
        """Симулировать сделку. None — kill switch, гейт или недостаточно средств.

        Если ребаланс уже случился, а сама сделка дальше отваливается
        (мелкий notional, тонкая глубина, убыточность) — возвращается
        ExecutionResult с trade=None, чтобы движение ребаланса всё равно
        доехало до hypertable balance.
        """
        if self.kill_switch:
            return None

        start = time.time()
        now_ms = int(time.time() * 1000)

        if self._expired(opp, now_ms):
            return None

        # ceil, не int(): настройка 0.5с при трункации давала 0 и МОЛЧА
        # выключала кулдаун целиком; любое положительное значение → мин. 1с.
        cooldown_ttl = math.ceil(self.loss_cooldown_sec)
        cooldown_key = f"cooldown:{opp.symbol}:{opp.buy_exchange}:{opp.sell_exchange}"
        if await self._in_cooldown(opp, cooldown_key, cooldown_ttl):
            return None

        depths = await self._fresh_depth(opp, now_ms)
        if depths is None:
            return None
        buy_depth, sell_depth = depths

        buy_balance = await get_balance(self._redis, opp.buy_exchange)

        rebalance_result = await maybe_rebalance(
            self._redis, opp.buy_exchange, buy_balance, self.rebalance_threshold,
        )
        if rebalance_result is not None:
            buy_balance = rebalance_result.receiver_new_balance
        elif buy_balance <= self.rebalance_threshold:
            return None

        def skipped() -> ExecutionResult | None:
            if rebalance_result is None:
                return None
            return ExecutionResult(trade=None, balance_updates=[], rebalance=rebalance_result)

        notional = buy_balance * self.max_position_pct / 100.0  # ≤ 10% баланса
        if notional < MIN_NOTIONAL_USDT:
            _skip("min_notional", symbol=opp.symbol, buy_ex=opp.buy_exchange,
                  notional=notional)
            return skipped()

        walked_buy = walk_asks_for_notional(buy_depth["asks"], notional)
        if walked_buy is None:
            _skip("thin_buy_book", symbol=opp.symbol, exchange=opp.buy_exchange,
                  notional=notional)
            return skipped()
        amount, effective_buy = walked_buy

        effective_sell = walk_bids_for_amount(sell_depth["bids"], amount)
        if effective_sell is None:
            _skip("thin_sell_book", symbol=opp.symbol, exchange=opp.sell_exchange,
                  amount=amount)
            return skipped()

        # НЕ asks[0][0] напрямую: NaN/нулевой dust-уровень прошёл бы в
        # gross_pnl/slippage_cost (net_pnl не задел бы — гейт бы не спас),
        # NaN в NUMERIC-колонке ломает суммы analytics до удаления строки.
        top_ask = first_valid_price(buy_depth["asks"])
        top_bid = first_valid_price(sell_depth["bids"])
        if top_ask is None or top_bid is None:
            _skip("corrupt_book", symbol=opp.symbol, buy_ex=opp.buy_exchange,
                  sell_ex=opp.sell_exchange)
            return skipped()

        pnl = settle_trade(
            amount=amount,
            effective_buy=effective_buy,
            effective_sell=effective_sell,
            top_ask=top_ask,
            top_bid=top_bid,
            buy_fee_pct=opp.buy_fee_pct,
            sell_fee_pct=opp.sell_fee_pct,
        )

        # ГЕЙТ ПРИБЫЛЬНОСТИ — единственное место, где известны реальные
        # VWAP-цены исполнения. Спред, прошедший фильтры сканера, здесь
        # регулярно оказывается убыточным (проскальзывание на тонком стакане).
        if pnl.net_pnl < self.min_profit_usd:
            _skip("unprofitable", symbol=opp.symbol, buy_ex=opp.buy_exchange,
                  sell_ex=opp.sell_exchange, net_pnl=round(pnl.net_pnl, 4),
                  slippage_cost=round(pnl.slippage_cost, 4), notional=round(notional, 2))
            if cooldown_ttl > 0:
                await self._redis.set(cooldown_key, "1", ex=cooldown_ttl)
            return skipped()

        buy_change = -(amount * effective_buy + pnl.buy_fee)
        sell_change = amount * effective_sell - pnl.sell_fee
        new_buy = await update_balance(self._redis, opp.buy_exchange, buy_change)
        new_sell = await update_balance(self._redis, opp.sell_exchange, sell_change)

        trade = self._build_trade(
            opp, amount, effective_buy, effective_sell, pnl, top_ask, top_bid, start,
        )
        return ExecutionResult(
            trade=trade,
            balance_updates=[
                (opp.buy_exchange, max(0.0, new_buy), buy_change),
                (opp.sell_exchange, max(0.0, new_sell), sell_change),
            ],
            rebalance=rebalance_result,
        )
