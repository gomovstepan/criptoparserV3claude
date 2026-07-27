-- Миграция: точность объёмов сделок/балансов + top-of-book цены в trades.
-- Re-runnable: ALTER TYPE идемпотентен, ADD COLUMN IF NOT EXISTS.
--
-- Применение к существующей БД:
--   docker exec -i arb-timescaledb psql -U arbitrage -d arbitrage_db < scripts/migrate-trade-precision.sql
--
-- 1) amount/change_amount → DECIMAL(28,8): amount = notional/price, и мемкоины
--    с ценой ~1e-6 при больших балансах дают объёмы > 1e10 — за пределами
--    DECIMAL(18,8). Одна такая строка роняла COPY всего батча в executor
--    (балансы в Redis к этому моменту уже сдвинуты — терялся ledger).
--    Prices-хайпертейбл уже был расширен ранее (migrate-volume-precision.sql).
-- 2) buy_top_ask/sell_top_bid: top-of-book обеих ног на момент исполнения.
--    Без них gross_pnl и slippage_cost алгебраически неразложимы постфактум,
--    а строка opportunity хранит цены другого снапшота. Пишет executor
--    (shared/models.py Trade), отдаёт GET /api/v1/trades.

ALTER TABLE trades  ALTER COLUMN amount        TYPE DECIMAL(28,8);
ALTER TABLE balance ALTER COLUMN amount        TYPE DECIMAL(28,8);
ALTER TABLE balance ALTER COLUMN change_amount TYPE DECIMAL(28,8);

ALTER TABLE trades ADD COLUMN IF NOT EXISTS buy_top_ask  DECIMAL(18,8);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS sell_top_bid DECIMAL(18,8);
