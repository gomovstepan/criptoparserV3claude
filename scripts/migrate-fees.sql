-- Migration: sync exchange_configs seed with shared/config.py (fee audit July 2026).
-- Эти колонки НИКТО не читает (источник правды — EXCHANGES в shared/config.py,
-- из БД берётся только is_active) — обновление чисто для консистентности seed'а.
-- Re-runnable.
UPDATE exchange_configs SET maker_fee_pct = 0.10, taker_fee_pct = 0.10 WHERE exchange = 'gateio';
UPDATE exchange_configs SET withdrawal_usdt = 1.5 WHERE exchange IN ('binance', 'kucoin', 'bitget');
UPDATE exchange_configs SET withdrawal_usdt = 1.7 WHERE exchange = 'coinex';
