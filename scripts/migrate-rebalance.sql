-- Migration: add rebalance support
-- 1) Extend balance.reason CHECK constraint to include 'rebalance'
ALTER TABLE balance DROP CONSTRAINT IF EXISTS balance_reason_check;
ALTER TABLE balance ADD CONSTRAINT balance_reason_check
    CHECK (reason IN ('trade', 'deposit', 'withdrawal', 'adjustment', 'initial', 'rebalance'));

-- 2) Add rebalance_threshold_usd setting (default $100)
INSERT INTO settings (key, value, description)
VALUES ('rebalance_threshold_usd', '100.00', 'Balance threshold (USDT) triggering rebalance from richest exchange')
ON CONFLICT (key) DO NOTHING;
