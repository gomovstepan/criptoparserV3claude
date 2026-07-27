-- Миграция: ключи settings для гейтов торговли (этап «остановить убытки»).
-- Re-runnable: ON CONFLICT DO NOTHING. Для свежей БД те же строки сеет init-db.sql.
--
-- Применение к существующей БД:
--   docker exec -i arb-timescaledb psql -U arbitrage -d arbitrage_db < scripts/migrate-trading-gates.sql
--
-- Читатели:
--   min_profit_usd, loss_cooldown_sec, depth_max_age_ms_executor — executor
--     (executor/main.py::_ENGINE_SETTINGS, рефрешер ~10с);
--   min_net_spread_pct, depth_max_age_ms_scanner — scanner
--     (scanner/main.py::_SCANNER_SETTINGS, рефрешер ~10с).
-- Все ключи изменяемы через PUT /api/v1/settings (allowlist SettingsUpdate)
-- и форму настроек дашборда (frontend/src/types.ts SETTING_FIELDS).

INSERT INTO settings (key, value, description) VALUES
('min_profit_usd', '0.00', 'Executor profitability gate: skip trade when net_pnl below this (USDT)'),
('loss_cooldown_sec', '60', 'Cooldown (sec) for a (symbol, buy, sell) config after an unprofitable evaluation; 0 disables'),
('min_net_spread_pct', '0.10', 'Scanner filter: min spread % net of both taker fees (withdrawal excluded by ledger model)'),
('depth_max_age_ms_executor', '2000', 'Max depth snapshot age (ms) the executor will trade on'),
('depth_max_age_ms_scanner', '3000', 'Max depth snapshot age (ms) the scanner will price on')
ON CONFLICT (key) DO NOTHING;
