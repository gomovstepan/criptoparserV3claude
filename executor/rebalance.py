"""Ребаланс виртуальных балансов между биржами.

Когда баланс биржи-покупки падает ниже порога — переводим половину
с самой богатой биржи (донора). Комиссия вывода списывается один раз
за ребаланс, а не за каждую сделку.

Донор после перевода обязан сам остаться выше порога: иначе следующая
opportunity с ним как buy-биржей запустила бы обратный перевод —
«пинг-понг» между двумя бедными биржами с уплатой комиссии за каждый круг.
"""
from __future__ import annotations

from dataclasses import dataclass

import redis.asyncio as redis
import structlog

from balance import all_balances, update_balance
from shared.config import EXCHANGES

log = structlog.get_logger()

KILL_SWITCH_KEY = "executor:kill_switch"


@dataclass
class RebalanceResult:
    donor: str
    receiver: str
    gross_amount: float
    fee: float
    net_amount: float
    donor_new_balance: float
    receiver_new_balance: float


async def maybe_rebalance(
    r: redis.Redis,
    exchange: str,
    balance: float,
    threshold: float,
) -> RebalanceResult | None:
    """Ребалансировать если balance <= threshold. None = не нужен или невозможен."""
    if balance > threshold:
        return None

    balances = await all_balances(r)
    donor = max(balances, key=balances.get)
    donor_balance = balances[donor]

    gross_amount = donor_balance / 2.0
    fee = EXCHANGES[donor].withdrawal_usdt
    net_amount = gross_amount - fee

    # gross_amount — одновременно размер перевода и новый баланс донора
    # (половина). Донор обязан остаться выше порога, а перевод — покрывать
    # комиссию вывода, иначе ребаланс лишь гоняет деньги по кругу.
    if donor == exchange or gross_amount <= threshold or net_amount <= 0.0:
        await r.set(KILL_SWITCH_KEY, "1")
        log.warning(
            "rebalance_impossible_kill_switch",
            receiver=exchange,
            donor=donor,
            donor_balance=donor_balance,
            threshold=threshold,
        )
        return None

    donor_new = await update_balance(r, donor, -gross_amount)
    receiver_new = await update_balance(r, exchange, net_amount)

    log.info(
        "rebalance_executed",
        donor=donor,
        receiver=exchange,
        gross=round(gross_amount, 2),
        fee=fee,
        net=round(net_amount, 2),
    )
    return RebalanceResult(
        donor=donor,
        receiver=exchange,
        gross_amount=gross_amount,
        fee=fee,
        net_amount=net_amount,
        donor_new_balance=donor_new,
        receiver_new_balance=receiver_new,
    )
