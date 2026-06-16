-- ============================================================================
-- init-db.sql — инициализация TimescaleDB для крипто-арбитражной системы
-- Запускается автоматически при первом старте контейнера timescaledb
-- (монтируется в /docker-entrypoint-initdb.d/). Выполняется внутри БД,
-- указанной в POSTGRES_DB (arbitrage_db).
--
-- Наполнение по фазам:
--   Фаза 1 — расширение timescaledb
--   Фаза 2 — users, settings, exchange_configs, tracked_pairs (+ seed)
--   Фаза 5 — hypertable prices (+ индексы, compression, retention)
-- ============================================================================

-- ── Расширения (Фаза 1) ──────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ── users (Фаза 2) ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    telegram_id     BIGINT UNIQUE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_telegram ON users (telegram_id);


-- ── settings (Фаза 2) ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
    id              SERIAL PRIMARY KEY,
    key             VARCHAR(100) UNIQUE NOT NULL,
    value           JSONB NOT NULL,
    description     TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by      UUID REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_settings_key ON settings (key);

INSERT INTO settings (key, value, description) VALUES
('min_spread_pct', '0.30', 'Minimum spread % to trigger opportunity'),
('max_position_pct', '10.00', 'Max % of balance per trade'),
('slippage_tolerance_pct', '0.20', 'Slippage tolerance %'),
('execution_timeout_sec', '2', 'Max execution time in seconds'),
('kill_switch', 'false', 'Emergency stop flag'),
('notification_spread_threshold', '0.50', 'Min spread % for Telegram alert'),
('notification_trade_min_pnl', '5.00', 'Min |net P&L| USDT to alert a trade in Telegram'),
('daily_loss_limit_pct', '5.00', 'Daily loss limit % - stop trading')
ON CONFLICT (key) DO NOTHING;


-- ── exchange_configs (Фаза 2) ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS exchange_configs (
    id              SERIAL PRIMARY KEY,
    exchange        VARCHAR(20) UNIQUE NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    maker_fee_pct   DECIMAL(6,4) NOT NULL,
    taker_fee_pct   DECIMAL(6,4) NOT NULL,
    withdrawal_btc  DECIMAL(18,8),
    withdrawal_usdt DECIMAL(18,8),
    ws_endpoint     VARCHAR(255),
    rest_endpoint   VARCHAR(255),
    rate_limit_req_per_sec INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO exchange_configs
    (exchange, maker_fee_pct, taker_fee_pct, withdrawal_btc, withdrawal_usdt, rate_limit_req_per_sec) VALUES
('bybit',   0.10, 0.10, 0.000085, 1.0, 50),
('binance', 0.10, 0.10, 0.0005,   0.0, 1200),
('kucoin',  0.10, 0.10, 0.0,      0.0, 200),
('gateio',  0.30, 0.30, 0.001,    1.0, 200),
('bitget',  0.10, 0.10, 0.0003,   1.0, 20),
('coinex',  0.20, 0.20, 0.0001,   1.0, 10),
('bingx',   0.10, 0.10, 0.00035,  1.0, 24)
ON CONFLICT (exchange) DO NOTHING;


-- ── tracked_pairs (Фаза 2) ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tracked_pairs (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL,
    exchange        VARCHAR(20) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    priority        INTEGER NOT NULL DEFAULT 3,
    min_spread_override DECIMAL(6,4),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, exchange)
);

-- P1: BTC/USDT и ETH/USDT по 4 биржам = 8 активных пар
INSERT INTO tracked_pairs (symbol, exchange, is_active, priority) VALUES
('BTC/USDT', 'binance', true, 1),
('BTC/USDT', 'bybit',   true, 1),
('BTC/USDT', 'kucoin',  true, 1),
('BTC/USDT', 'bitget',  true, 1),
('ETH/USDT', 'binance', true, 1),
('ETH/USDT', 'bybit',   true, 1),
('ETH/USDT', 'kucoin',  true, 1),
('ETH/USDT', 'bitget',  true, 1)
ON CONFLICT (symbol, exchange) DO NOTHING;


-- ── prices hypertable (Фаза 5) ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prices (
    time            TIMESTAMPTZ NOT NULL,
    exchange        VARCHAR(20) NOT NULL,
    symbol          VARCHAR(20) NOT NULL,
    bid             DECIMAL(18,8) NOT NULL,
    ask             DECIMAL(18,8) NOT NULL,
    bid_volume      DECIMAL(18,8),
    ask_volume      DECIMAL(18,8),
    latency_ms      INTEGER,
    CONSTRAINT prices_bid_positive CHECK (bid > 0),
    CONSTRAINT prices_ask_positive CHECK (ask > 0)
);

SELECT create_hypertable('prices', 'time',
    chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_prices_exchange_symbol_time
    ON prices (exchange, symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_prices_symbol_time
    ON prices (symbol, time DESC);

-- Сжатие чанков старше 7 дней
ALTER TABLE prices SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'exchange, symbol'
);
SELECT add_compression_policy('prices', INTERVAL '7 days', if_not_exists => TRUE);

-- Удаление данных старше 30 дней
SELECT add_retention_policy('prices', INTERVAL '30 days', if_not_exists => TRUE);


-- ── opportunities hypertable (Фаза 6) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS opportunities (
    time            TIMESTAMPTZ NOT NULL,
    id              VARCHAR(100) NOT NULL,
    symbol          VARCHAR(20) NOT NULL,
    buy_exchange    VARCHAR(20) NOT NULL,
    sell_exchange   VARCHAR(20) NOT NULL,
    buy_price       DECIMAL(18,8) NOT NULL,
    sell_price      DECIMAL(18,8) NOT NULL,
    gross_spread_pct   DECIMAL(8,4) NOT NULL,
    buy_fee_pct     DECIMAL(6,4) NOT NULL,
    sell_fee_pct    DECIMAL(6,4) NOT NULL,
    withdrawal_fee_usd DECIMAL(10,4),
    net_spread_pct  DECIMAL(8,4) NOT NULL,
    CONSTRAINT opp_buy_sell_diff CHECK (buy_exchange != sell_exchange),
    CONSTRAINT opp_net_calc CHECK (net_spread_pct <= gross_spread_pct)
);

SELECT create_hypertable('opportunities', 'time',
    chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_opp_symbol_time
    ON opportunities (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_opp_buy_sell_time
    ON opportunities (buy_exchange, sell_exchange, time DESC);
CREATE INDEX IF NOT EXISTS idx_opp_net_spread
    ON opportunities (net_spread_pct, time DESC) WHERE net_spread_pct > 0;

ALTER TABLE opportunities SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, buy_exchange, sell_exchange'
);
SELECT add_compression_policy('opportunities', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('opportunities', INTERVAL '90 days', if_not_exists => TRUE);


-- ── trades hypertable (Фаза 7) ───────────────────────────────────────────
-- PK включает time: TimescaleDB требует партиционирующую колонку в уник. индексе.
CREATE TABLE IF NOT EXISTS trades (
    time            TIMESTAMPTZ NOT NULL,
    id              VARCHAR(100) NOT NULL,
    opportunity_id  VARCHAR(100) NOT NULL,
    symbol          VARCHAR(20) NOT NULL,
    buy_exchange    VARCHAR(20) NOT NULL,
    sell_exchange   VARCHAR(20) NOT NULL,
    buy_price       DECIMAL(18,8) NOT NULL,
    sell_price      DECIMAL(18,8) NOT NULL,
    amount          DECIMAL(18,8) NOT NULL,
    buy_fee         DECIMAL(18,8) NOT NULL DEFAULT 0,
    sell_fee        DECIMAL(18,8) NOT NULL DEFAULT 0,
    withdrawal_fee  DECIMAL(18,8) NOT NULL DEFAULT 0,
    slippage_cost   DECIMAL(18,8) NOT NULL DEFAULT 0,
    gross_pnl       DECIMAL(18,8) NOT NULL,
    net_pnl         DECIMAL(18,8) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    executed_at     TIMESTAMPTZ,
    duration_ms     INTEGER,
    CONSTRAINT trades_status_check CHECK (status IN ('pending', 'completed', 'failed', 'cancelled')),
    CONSTRAINT trades_pkey PRIMARY KEY (id, time)
);

SELECT create_hypertable('trades', 'time',
    chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_trades_symbol_time ON trades (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades (status, time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_opportunity ON trades (opportunity_id);

ALTER TABLE trades SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, status'
);
SELECT add_compression_policy('trades', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('trades', INTERVAL '1 year', if_not_exists => TRUE);


-- ── balance hypertable (Фаза 7) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS balance (
    time            TIMESTAMPTZ NOT NULL,
    exchange        VARCHAR(20) NOT NULL,
    asset           VARCHAR(10) NOT NULL DEFAULT 'USDT',
    amount          DECIMAL(18,8) NOT NULL,
    trade_id        VARCHAR(100),
    change_amount   DECIMAL(18,8),
    reason          VARCHAR(50) NOT NULL DEFAULT 'trade',
    CONSTRAINT balance_positive CHECK (amount >= 0),
    CONSTRAINT balance_reason_check CHECK (reason IN ('trade', 'deposit', 'withdrawal', 'adjustment', 'initial'))
);

SELECT create_hypertable('balance', 'time',
    chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_balance_exchange_time ON balance (exchange, time DESC);
CREATE INDEX IF NOT EXISTS idx_balance_asset_time ON balance (asset, time DESC);
SELECT add_retention_policy('balance', INTERVAL '1 year', if_not_exists => TRUE);
