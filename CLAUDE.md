# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

CriptoParser V3 — a closed crypto inter-exchange arbitrage system. Collects prices
from 7 exchanges over WebSocket, finds spreads, simulates trades (paper trading),
sends Telegram alerts, and serves a real-time React dashboard. Backend is Python
FastAPI microservices on a Redis Streams bus + TimescaleDB; frontend is React 19/Vite.

The full spec lives in `MASTER_PROMPT.md`, `EXECUTION_PLAN.md`, `TZ_ARCHITECTURE.md`,
and `UIUX_DASHBOARD.md`. All 16 build phases are complete and verified in Docker.

## Commands

```bash
# Main stack (DB, Redis, 5 microservices, frontend) — prod defaults baked in
# (restart: unless-stopped, json-file log rotation, resource limits).
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health        # api-gateway

# Monitoring stack (Prometheus, Grafana, Loki, Promtail) — joins external
# arbitrage-net; bring up the main stack first.
docker compose -f docker-compose.monitoring.yml up -d

# Tests — run INSIDE the running containers (stdlib unittest, no pip needed, offline-safe)
docker compose up -d
bash tests/run-tests.sh                   # all 6 suites; docker cp → python -m unittest → rm

# One suite (what run-tests.sh does per case; container per suite is fixed):
#   test_spread_calculator, test_depth      → arb-scanner
#   test_pnl_calculator, test_paper_trading → arb-executor
#   test_api, test_integration              → arb-api-gateway
docker cp tests/test_depth.py arb-scanner:/app/
docker exec arb-scanner python -m unittest test_depth -v
# Same files also run under `pytest tests/` if pytest is installed.

# Schema migrations — init-db.sql runs ONLY on a fresh timescaledb volume.
# For an existing DB, apply scripts/migrate-*.sql by hand (all are re-runnable):
docker exec -i arb-timescaledb psql -U arbitrage -d arbitrage_db < scripts/migrate-rebalance.sql

# Frontend (dev) — run via Preview MCP (.claude/launch.json, server "frontend", port 5173)
cd frontend
npm install --legacy-peer-deps            # React 19 peer conflicts need this flag
npm run dev                               # http://localhost:5173
npm run build                             # `tsc && vite build` — NOT `tsc -b`
npm run typecheck                         # tsc --noEmit
```

Only `api-gateway` (8000) and `frontend` (5173→nginx:80) publish host ports;
collector/scanner/executor/notifier (8001–8004) are reachable only inside the
`arbitrage-net` network — probe them with `docker compose exec`, not `localhost`.

Default dashboard user: `test@example.com` / `test123`. Swagger at `/docs`.
Port 5173 is mandatory — it is hardcoded in api-gateway `CORS_ORIGINS`.

## Architecture

Data flows one direction through a Redis Streams bus, with TimescaleDB as the store:

```
7 exchanges ─WS→ collector(8001) ─prices→ scanner(8002) ─opportunities→ executor(8003) ─trades→
                      │                        │                              │
                      └──────── TimescaleDB hypertables ──────────────────────┘
                                       ▲                          │
                  REST/WS  api-gateway(8000) ◀─Redis (balance,kill)→ notifier(8004) → Telegram
                                       ▲
                          React frontend (5173)
```

Each microservice is a FastAPI app owning one Redis consumer group. Groups are created
at `id="$"` (new messages only) — except `writer-cg` at `id="0"`, so the DB writer
drains the backlog.

- **collector** — connects to exchanges (ccxt.pro) per `exchange_configs.is_active`, symbols
  from `tracked_pairs`; publishes order-book depth to Redis, THEN the tick to stream `prices`
  (depth-first on purpose: the scanner is woken by the tick and immediately mgets depth);
  `db_writer.py` (cg `writer-cg`) batch-INSERTs into the `prices` hypertable. A **silence
  watchdog** force-reconnects a feed whose whole connection went quiet for 3s (see the
  collector bullet in Conventions) — quiet books on a single symbol are NOT a trigger.
- **scanner** — cg `scanner-cg`; keeps latest bid/ask in memory (quotes older than 5s are
  evicted — a disconnected exchange's frozen price must not keep producing spreads), prices
  pairs ONLY from fresh depth of both sides (no top-of-book fallback — see the depth section),
  dedups via Redis `SET EX 5` marked AFTER a successful publish; writes stream
  `opportunities` + hypertable. Settings (10s refresh): `min_spread_pct` (gross prefilter),
  `min_net_spread_pct` (gross − both taker fees), `estimated_trade_notional`,
  `depth_max_age_ms_scanner`.
- **executor** — cg `executor-cg`; paper trading, position = `max_position_pct%` of
  buy-exchange balance; balances in Redis Hash `balance:{ex}` + hypertable (on startup,
  fields missing from Redis are restored from the last `balance` ledger row —
  `restore_balances` — before the `INITIAL_BALANCES_USDT` seed). Kill switch is Redis key
  `executor:kill_switch`, **fail-closed**: trading is allowed only on an explicit `"0"`
  (`shared/redis_utils.py::kill_switch_engaged`); a missing key means STOP + a warning.
  The executor seeds it at startup (`"0"` in paper, `"1"` otherwise) and re-reads it
  **before every opportunity** (not once per batch — that let a whole 100-message batch
  execute after the operator hit stop).
  Safety gates run in a fixed order BEFORE any state mutation: opportunity age
  (`detected_at` + `ttl_seconds`) → cooldown → depth freshness (`depth_max_age_ms_executor`,
  default 2s — stricter than the scanner) → balance/rebalance → notional → book walks →
  **profitability gate**: a trade with `net_pnl < min_profit_usd` (settings, default 0) is
  skipped (`trade_skipped_unprofitable`) and the (symbol, buy, sell) config is silenced for
  `loss_cooldown_sec` (default 60, 0 disables). The profitability gate is the primary
  safety for future real trading — never remove or reorder it after balance mutation.
  A rebalance that already moved Redis but whose trade then skips returns
  `ExecutionResult(trade=None, rebalance=...)` so `_persist` still writes it to the ledger.
  `_persist` writes the `trades` and `balance` COPYs in one transaction (with a per-row
  INSERT fallback so one bad record can't void the batch) and always acks:
  nothing reclaims the PEL, and balance moves are `HINCRBYFLOAT`, so redelivery would
  double-apply them. Skip reasons are counted in Prometheus `trades_skipped_total{reason}`.
  Gated by `PAPER` env (`settings.paper`): when `false` it does NOT subscribe to
  `opportunities` and creates no trades (real trading is unimplemented) — balances/kill
  switch stay live. `/health` reports `paper` and the live gate settings.
- **notifier** — aiogram 3 polling bot; cg `notifier-cg` on `opportunities`+`trades`;
  rate-limited queue `telegram_queue` (20/s, 3 retries → `telegram_dead_letter`).
  Thresholds re-read from `settings`.
- **api-gateway** — REST `/api/v1/*`, WebSocket `/ws`, JWT HS256 (PyJWT) + PBKDF2 passwords,
  rate limiter 100/min/IP, CORS from `settings.cors_origins`. Routers in `routers/` subpackage.
  `PUT /api/v1/balance` and `DELETE /api/v1/trades` (filtered DELETE, or TRUNCATE with no
  filters) mutate state — both are paper-only (403 otherwise); `PUT /api/v1/settings`
  additionally rejects a negative `min_profit_usd` outside paper (the executor clamps it
  to ≥0 as a second line). `GET /api/v1/config` exposes `{paper}` to the frontend.

`settings` table is the live control plane: scanner, notifier, and executor each run a
~10s refresher loop, so thresholds change from the UI without a rebuild. Values are JSONB
and come back quoted — every reader does `float(str(row).strip('"'))` via a tolerant
parse, so a bad value leaves the previous one in place instead of killing the service.

The **kill switch is not in this table**. It is the Redis key `executor:kill_switch`,
written by the gateway, the Telegram bot (both write Redis directly), and
`executor/rebalance.py`; re-read by the executor before every opportunity with
**fail-closed** semantics (`kill_switch_engaged`: anything but `"0"` — including a
missing key — means STOP). The `settings.kill_switch` row is a vestigial seed that
nothing reads or writes — do not wire anything to it.

Three legacy keys stay seeded in the table but are exposed by **neither the UI nor the API
allowlist**: `slippage_tolerance_pct`, `execution_timeout_sec` (superseded — slippage now
comes from walking the order book, and there is no execution timeout), and
`daily_loss_limit_pct` (an unimplemented spec requirement, TZ E-014). If you implement one,
add it to the code that reads it, to `SettingsUpdate` in `routers/exchanges.py`, and to
`SETTING_FIELDS` in `frontend/src/types.ts` — in that order.

`GET /api/v1/exchanges` serves fees from the `EXCHANGES` constant in `shared/config.py`
(the same source the scanner/executor math uses); only `is_active` comes from the DB. The
fee columns in `exchange_configs` are a first-boot seed nothing reads — do not make them
authoritative without also feeding them into the scanner and executor.

### Order-book depth is the ONLY pricing path

There is no top-of-book fallback — it was removed deliberately: it engaged exactly when
the depth filter was most needed (feed lag/outage) and priced phantom spreads off dust
orders at the top of the book (every losing trade in the system's history came from that
path). On every book update the collector writes `depth:{exchange}:{symbol}` — JSON of the
top 10 levels, TTL 5s, `ts = min(local_now, exchange_ts)` so exchange-side lag (spikes up
to ~34s were measured) eats the freshness budget (`shared/depth.py`).
Both scanner and executor replay execution against that book:

- `walk_asks_for_notional()` spends `estimated_trade_notional` USDT up the asks → (amount, VWAP);
  `walk_bids_for_amount()` sells that amount down the bids → VWAP. Either returns `None` when
  the book is too thin, mis-sorted, or NaN-ridden, and the opportunity/trade is **dropped** —
  this is the phantom-spread filter.
- Freshness is two-tier and settings-driven: the scanner won't price on depth older than
  `depth_max_age_ms_scanner` (default 3s) — no depth on either side means the pair is simply
  skipped; the executor won't trade on depth older than `depth_max_age_ms_executor`
  (default 2s, stricter — a false skip is free, a stale fill costs money).

So a spread visible in the UI does not imply a trade: the executor re-walks the book at
execution time and frequently skips (see `trades_skipped_total{reason}`). When touching
spread or P&L math, keep `shared/depth.py` the single implementation — scanner and executor
both import it. Trades store `buy_top_ask`/`sell_top_bid` (execution-time top-of-book) so
gross vs slippage stays reconcilable after the fact.

### P&L accounting invariant

`executor/pnl.py::settle_trade` is the single implementation of the trade P&L formula —
`paper_trading.py` calls it, and `tests/test_pnl_calculator.py` covers it. The identity it
maintains is `net_pnl == gross_pnl - slippage_cost - buy_fee - sell_fee`, where `gross_pnl`
is top-of-book and `slippage_cost` is the VWAP-vs-top gap (reported, not subtracted twice).

The withdrawal fee is **not** part of a trade's `net_pnl` (`withdrawal_fee=0` on every trade).
It is charged once per rebalance instead: when the buy exchange's balance falls to
`rebalance_threshold_usd`, `executor/rebalance.py` moves half the richest exchange's balance
over, minus that exchange's `withdrawal_usdt`, and logs it to the `balance` hypertable with
`reason='rebalance'`. If no donor qualifies it **sets the kill switch**.

Therefore total P&L anywhere = `sum(trades.net_pnl)` + `sum(balance.change_amount WHERE
reason='rebalance')`. That definition lives in `api-gateway/routers/pnl_sql.py` (`PNL_EVENTS`)
and is used by both the KPI queries and the time series — previously the series omitted the
rebalance term, so the last point of the chart never matched the number above it. Any new P&L
query must use `PNL_EVENTS`, or it silently overstates profit.

Note the scanner's `net_spread_pct` uses a *different* cost model: it subtracts a withdrawal
fee per opportunity (`withdrawal_usdt / estimated_trade_notional`), which is roughly 40× what
the ledger actually charges. It is display-only — the notifier alerts on gross and the
executor never reads it — so the bias is pessimistic and harmless. Do not add it to any P&L
total and do not filter on it. The scanner's actual profitability filter is
`min_net_spread_pct` over `gross − buy_fee − sell_fee` (withdrawal excluded, matching the
ledger model); the API/frontend expose the same quantity as `net_fees_pct` and the
Opportunities toggle/badges use it. The executor's last word is its own profitability gate
on real VWAPs (`min_profit_usd`).

## Logging & observability

`shared/logging_config.py::setup_logging("<service>")` is called once per service at
`main` import (BEFORE `structlog.get_logger()`), so it captures uvicorn/ccxt/aiogram too.
It writes JSON lines to `${LOG_DIR}/<service>.log` (default `/app/logs`, bind-mounted from
`./logs` on every service) AND human-readable lines to stdout (`docker logs`). Rotating at
10 MB × 5 files. The monitoring stack (`docker-compose.monitoring.yml`) adds **Promtail → Loki → Grafana**
(`monitoring/loki-config.yml`, `promtail-config.yml`, `grafana-logs-dashboard.json`): Promtail
reads `./logs/*.log`, derives the `service` label from the filename and `level` from the JSON.
Loki keeps 7 days. Tune via `LOG_DIR` / `LOG_LEVEL` env.

## Conventions and gotchas

- **Microservice internal imports are flat** (`from ws_client import ...`), because each
  Dockerfile copies code into `/app`. `shared/` is mounted as `./shared:/app/shared:ro`
  and imported as the package `shared`. Do not rewrite these to package-relative imports.
- **`notifier/tg_queue.py` must not be named `queue.py`** — cwd is first on `sys.path`, so
  `queue.py` would shadow the stdlib `queue` module.
- **Cross-service communication is via Redis, not HTTP.** The kill switch in particular is a
  shared Redis key written directly by gateway and Telegram bot; services never call each
  other's mutating endpoints (executor `POST /killswitch` and notifier `POST /notify` were
  removed as unauthenticated surfaces). The only HTTP hop is the Telegram bot polling
  service `/health` endpoints (read-only).
- **Redis holds money and the kill switch — its config is deliberately strict**:
  `--appendonly yes --maxmemory-policy noeviction` (docker-compose). Never revert to an
  eviction policy that can drop `balance:{ex}` or `executor:kill_switch`; memory stays
  bounded because streams are capped (maxlen) and depth/dedup/cooldown keys carry TTLs.
- **Collector WS strategy is per-exchange, not uniform.** Exchanges with
  `watchOrderBookForSymbols` (binance/bybit/kucoin/bitget/coinex) get one multiplexed socket;
  bybit is further chunked to 10 symbols per subscribe (it silently ignores larger ones and
  hangs). gateio/bingx fall back to one task per symbol with a 250 ms stagger and a
  handshake semaphore of 2, or the exchange rejects with "Too many connections".
  On startup `_sync_pairs()` calls `load_markets()` and sets `tracked_pairs.is_active=false`
  for symbols an exchange doesn't list — without it the collector retries forever and floods logs.
  The **silence watchdog** closes and re-subscribes a connection whose ENTIRE feed went
  quiet: multiplexed chunks via `asyncio.wait_for` (3s steady-state; 30s handshake budget —
  a flat 3s caused a reconnect storm at startup because handshake+subscribe through the VPN
  exceeds it), per-symbol exchanges via a per-exchange task on `_last_message_ms`. Never make
  the trigger per-symbol book age: quiet books are normal (28/36 coinex symbols have median
  update gaps > 2s) and reconnecting tears down ALL symbols on the socket. On fire it DELetes
  the exchange's depth keys so scanner/executor see absence immediately; count is in
  `/health.watchdog_reconnects` and `ws_watchdog_reconnects_total{exchange}`.
- **`db_writer` writes via COPY with a per-row INSERT fallback** — one bad record would
  otherwise kill a 1000-row batch. Prices are `NUMERIC(18,8)`; volumes are `NUMERIC(28,8)`
  because memecoin book volumes exceed 10^10 (see `migrate-volume-precision.sql`).
  Over-precision values are dropped/nulled before the COPY, not after.
- **TimescaleDB volume mounts at `/var/lib/postgresql`**, not `.../data` — PG18 stores data
  in a version subdir, and mounting `.../data` makes the container exit with "unused volume".
- **Frontend always uses relative URLs; a proxy supplies the origin.** In Docker, nginx
  (`frontend/nginx.conf`) proxies `/api`, `/ws`, `/docs` to `arb-api-gateway:8000`. In dev,
  `frontend/vite.config.ts` proxies the same paths to `localhost:8000`. So `VITE_API_URL` /
  `VITE_WS_URL` are deliberately unset everywhere and `.env.example` no longer lists them —
  Vite reads env files only from `frontend/`, never the repo-root `.env`, and `.gitignore`
  makes a `frontend/.env` uncommittable. Do not reintroduce those vars; extend the proxy.
- **Frontend build is `tsc && vite build`** (not `tsc -b`; project references broke). Tailwind
  config uses absolute paths in `postcss.config.js`/`tailwind.config.js` so Vite works even
  when launched from a different cwd. Changing tailwind config requires a Vite RESTART.
- **Theme tokens** are CSS RGB-channel vars in `index.css` (`:root`=dark, `html.light`=light);
  tailwind colors use `rgb(var(--c-x) / <alpha-value>)`. recharts internal colors are not themed.
- Tests are plain `unittest.TestCase` files run with `python -m unittest` inside containers
  (pytest is not installed in images). Keep new tests stdlib-only so `run-tests.sh` works offline.
  `test_api`/`test_integration` need the live stack; they hit `localhost:8000` and real Redis
  from inside `arb-api-gateway`. `test_paper_trading` stubs Redis with a plain class, so the
  engine can be tested without a live stack — follow that pattern for new executor tests.
- **Secrets layout**: `.env` is untracked (removed from git index; the old Telegram token
  in git history is considered compromised — rotate via BotFather). DB/Redis/JWT/Grafana
  values are random per-deployment secrets. Telegram credentials live in a separate
  untracked `.env.notifier` (template: `.env.notifier.example`) which only the notifier
  service receives via compose `env_file` — other containers never see the bot token.

## Environment notes

Target environment is a Linux VPS running the Docker stack (Windows is at most an optional
dev machine — do not add Windows-specific tooling). Network access to exchanges may be
degraded or filtered depending on the host's region/route: unresolvable pip hosts mean
`requirements.txt` edits should be avoided when offline (keep pip layers cached), and
exchange WS hosts being unreachable shows as "disconnected" — a real network state, not a
bug. Before real trading, the network path VPS→exchanges must be direct (no consumer VPN
in the data path).
