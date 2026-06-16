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
# Backend stack (DB, Redis, 5 microservices)
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health        # api-gateway

# Production stack + Prometheus/Grafana
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Tests — run INSIDE the running containers (stdlib unittest, no pip needed, offline-safe)
docker compose up -d
pwsh tests/run-tests.ps1                  # all 16; docker cp → python -m unittest → rm
# Same files also run under `pytest tests/` if pytest is installed.

# Frontend (dev) — run via Preview MCP (.claude/launch.json, server "frontend", port 5173)
cd frontend
npm install --legacy-peer-deps            # React 19 peer conflicts need this flag
npm run dev                               # http://localhost:5173
npm run build                             # `tsc && vite build` — NOT `tsc -b`
```

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

Each microservice is a FastAPI app owning one Redis consumer group:
- **collector** — connects to exchanges (ccxt) per `exchange_configs.is_active`, symbols
  from `tracked_pairs`; publishes ticks to stream `prices`; `db_writer.py` (cg `writer-cg`)
  batch-INSERTs into the `prices` hypertable.
- **scanner** — cg `scanner-cg`; keeps latest bid/ask in memory, computes spreads
  (buy at ask of A, sell at bid of B), dedups via Redis `SET NX EX 5`; writes stream
  `opportunities` + hypertable. `min_spread_pct` read from `settings` (10s refresh).
- **executor** — cg `executor-cg`; paper trading with 0.1–0.3% slippage, position =
  `max_position_pct%` of buy-exchange balance; balances in Redis Hash `balance:{ex}` +
  hypertable. Kill switch is Redis key `executor:kill_switch` ("1"/"0"), re-read each loop.
- **notifier** — aiogram 3 polling bot; cg `notifier-cg` on `opportunities`+`trades`;
  rate-limited queue `telegram_queue` (20/s). Thresholds re-read from `settings`.
- **api-gateway** — REST `/api/v1/*`, WebSocket `/ws`, JWT HS256 (PyJWT) + PBKDF2 passwords,
  rate limiter 100/min/IP, CORS from `settings.cors_origins`. Routers in `routers/` subpackage.

`settings` table is the live control plane: scanner/notifier/executor poll it every ~10s,
so thresholds and the kill switch change from the UI without rebuilds.

## Conventions and gotchas

- **Microservice internal imports are flat** (`from ws_client import ...`), because each
  Dockerfile copies code into `/app`. `shared/` is mounted as `./shared:/app/shared:ro`
  and imported as the package `shared`. Do not rewrite these to package-relative imports.
- **`notifier/tg_queue.py` must not be named `queue.py`** — cwd is first on `sys.path`, so
  `queue.py` would shadow the stdlib `queue` module.
- **Cross-service communication is via Redis, not HTTP.** The kill switch in particular is a
  shared Redis key; gateway and executor never call each other over HTTP (avoids DNS issues).
- **TimescaleDB volume mounts at `/var/lib/postgresql`**, not `.../data` — PG18 stores data
  in a version subdir, and mounting `.../data` makes the container exit with "unused volume".
- **Frontend build is `tsc && vite build`** (not `tsc -b`; project references broke). Tailwind
  config uses absolute paths in `postcss.config.js`/`tailwind.config.js` so Vite works even
  when launched from a different cwd. Changing tailwind config requires a Vite RESTART.
- **Theme tokens** are CSS RGB-channel vars in `index.css` (`:root`=dark, `html.light`=light);
  tailwind colors use `rgb(var(--c-x) / <alpha-value>)`. recharts internal colors are not themed.
- Tests are plain `unittest.TestCase` files run with `python -m unittest` inside containers
  (pytest is not installed in images). Keep new tests stdlib-only so `run-tests.ps1` works offline.

## Environment notes

Windows dev machine. Docker Desktop is often not running at session start — `docker compose
up -d` first. A VPN tunnel (`happ-tun`) intermittently breaks DNS: `files.pythonhosted.org`
won't resolve (so avoid editing `requirements.txt` — keep pip layers cached for offline
rebuilds), and exchange WS hosts may be unreachable (exchanges show "disconnected" — a real
network state, not a bug). On Windows, Vite's file-watcher misses NEW files — restart the dev
server (don't just reload) when adding pages/components.
