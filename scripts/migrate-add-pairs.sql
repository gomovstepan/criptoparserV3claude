-- Миграция: добавление 37 торговых пар на все 7 бирж.
-- Безопасно запускать повторно (ON CONFLICT DO NOTHING).
-- Использование:
--   docker exec -i arb-timescaledb psql -U arbitrage -d arbitrage_db < scripts/migrate-add-pairs.sql

INSERT INTO tracked_pairs (symbol, exchange, is_active, priority)
SELECT s.symbol, e.exchange, true,
       CASE WHEN s.symbol IN ('BTC/USDT','ETH/USDT') THEN 1 ELSE 2 END
FROM (VALUES
  ('BTC/USDT'),('ETH/USDT'),('SOL/USDT'),('XRP/USDT'),('DOGE/USDT'),
  ('SUI/USDT'),('ADA/USDT'),('AVAX/USDT'),('ZEC/USDT'),('LINK/USDT'),
  ('PEPE/USDT'),('LTC/USDT'),('NEAR/USDT'),('XMR/USDT'),('UNI/USDT'),
  ('BNB/USDT'),('DOT/USDT'),('PENGU/USDT'),('WLD/USDT'),('SHIB/USDT'),
  ('TON/USDT'),('ARB/USDT'),('HTX/USDT'),('OP/USDT'),('IMX/USDT'),
  ('APT/USDT'),('SEI/USDT'),('TIA/USDT'),('INJ/USDT'),('ENA/USDT'),
  ('PYTH/USDT'),('BLUR/USDT'),('AEVO/USDT'),('FLOKI/USDT'),('BONK/USDT'),
  ('WIF/USDT'),('MEME/USDT')
) AS s(symbol)
CROSS JOIN (VALUES
  ('binance'),('bybit'),('kucoin'),('gateio'),('bitget'),('coinex'),('bingx')
) AS e(exchange)
ON CONFLICT (symbol, exchange) DO NOTHING;
