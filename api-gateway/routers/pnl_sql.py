"""Единое определение «событий P&L» для всех агрегатов дашборда.

Инвариант системы (см. CLAUDE.md, раздел «P&L accounting invariant»):

    P&L = sum(trades.net_pnl) + sum(balance.change_amount WHERE reason='rebalance')

Комиссия вывода не входит в ``net_pnl`` отдельной сделки — она списывается один
раз при ребалансе (``executor/rebalance.py``), поэтому оба слагаемых обязаны
учитываться вместе. Раньше слагаемое ребаланса стояло в KPI (`/stats`,
`total_net_pnl`), но отсутствовало во временных рядах (`/stats/pnl`,
`daily[].cumulative_net_pnl`) — последняя точка графика никогда не совпадала
с числом над ним.

Фрагмент ниже подставляется как подзапрос: он приводит обе таблицы к общему виду
``(time, pnl, gross_pnl, is_trade)``, чтобы бакетирование считало один и тот же
P&L во всех эндпоинтах. ``$1`` — граница окна (интервал), одинаковая для обеих
половин UNION.
"""
from __future__ import annotations

# Использование: f"SELECT ... FROM ({PNL_EVENTS.format(window='make_interval(hours => $1)')}) e"
#
# is_trade отделяет сделки от движений ребаланса: count(*) и gross_pnl должны
# считаться только по сделкам, а net_pnl — по обоим видам событий.
PNL_EVENTS = """
        SELECT time, net_pnl AS pnl, gross_pnl, true AS is_trade
        FROM trades
        WHERE time > now() - {window}
        UNION ALL
        SELECT time, change_amount AS pnl, 0::numeric AS gross_pnl, false AS is_trade
        FROM balance
        WHERE reason = 'rebalance' AND time > now() - {window}
"""
