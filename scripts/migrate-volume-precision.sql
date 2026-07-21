-- Миграция: расширение precision для объёмов в hypertable `prices`.
-- Причина: у мемкоинов (SHIB, PEPE, BONK, FLOKI) объёмы в стакане
-- регулярно превышают 10^10 (NUMERIC(18,8) макс), что вызывало
-- "numeric field overflow" в db_writer и валило весь batch COPY.
-- NUMERIC(28,8) даёт ~10^20 — этого хватает с большим запасом.
--
-- Безопасно запускать повторно. Запуск:
--   docker exec -i arb-timescaledb psql -U arbitrage -d arbitrage_db < scripts/migrate-volume-precision.sql

-- TimescaleDB не даёт ALTER TYPE на сжатых чанках. Распаковываем
-- то, что уже сжалось (если retention/compression успели сработать).
DO $$
DECLARE
    chunk RECORD;
BEGIN
    FOR chunk IN
        SELECT format('%I.%I', chunk_schema, chunk_name) AS qualified
        FROM timescaledb_information.chunks
        WHERE hypertable_name = 'prices' AND is_compressed = true
    LOOP
        EXECUTE format('SELECT decompress_chunk(%L)', chunk.qualified);
    END LOOP;
END $$;

ALTER TABLE prices
    ALTER COLUMN bid_volume TYPE NUMERIC(28,8),
    ALTER COLUMN ask_volume TYPE NUMERIC(28,8);
