# CriptoParser V3 — крипто-арбитражная система

Закрытая SaaS-система мониторинга межбиржевого арбитража: собирает цены с 7 бирж,
ищет спреды, симулирует сделки (paper trading), шлёт алерты в Telegram и отдаёт
real-time дашборд. Backend — Python-микросервисы на FastAPI, фронтенд — React 19.

## Архитектура

```
                 ┌────────────┐   prices    ┌──────────┐  opportunities  ┌──────────┐
  7 бирж  ──WS──▶│ collector  │──▶ Redis  ──▶│ scanner  │──▶  Redis    ──▶│ executor │
                 │  (8001)    │   Streams   │  (8002)  │    Streams      │  (8003)  │
                 └─────┬──────┘             └────┬─────┘                 └────┬─────┘
                       │ db_writer               │                            │ trades
                       ▼                         ▼                            ▼
                 ┌──────────────── TimescaleDB (hypertables) ──────────────────┐
                 └──────────────────────────────────────────────────────────────┘
                       ▲                                            │
        REST/WS  ┌─────┴──────┐                              ┌──────┴─────┐
   React  ◀─────▶│ api-gateway│◀──── Redis (balance, kill) ─▶│  notifier  │──▶ Telegram
   (5173)        │   (8000)   │                              │   (8004)   │
                 └────────────┘                              └────────────┘
```

| Сервис | Порт | Назначение |
|--------|------|-----------|
| collector | 8001 | WS-подключения к 7 биржам, публикация тиков в Redis Stream `prices`, запись в TimescaleDB |
| scanner | 8002 | Расчёт межбиржевых спредов, публикация `opportunities` |
| executor | 8003 | Paper-trading: симуляция сделок, P&L, виртуальные балансы, kill switch |
| notifier | 8004 | Telegram-бот (aiogram): алерты по сделкам/спредам, команды |
| api-gateway | 8000 | REST `/api/v1/*` + WebSocket `/ws` + JWT + CORS + `/metrics` + Swagger `/docs` |
| frontend | 5173 | React 19 дашборд (Vite dev) |
| timescaledb | 5432 | Хранилище временных рядов (PostgreSQL 18 + TimescaleDB) |
| redis | 6379 | Streams (шина) + балансы + kill switch + дедуп |
| prometheus | 9090 | Сбор метрик (prod-профиль) |
| grafana | 3000 | Дашборды метрик (prod-профиль) |

## Требования

- Docker Desktop (Windows/macOS/Linux), Docker Compose v2
- Node.js 20+ — только для фронтенда (Vite dev-сервер)
- ~2 ГБ свободной RAM

## Быстрый старт

```bash
# 1. Скопировать пример окружения и заполнить секреты
cp .env.example .env
#   как минимум задать: POSTGRES_PASSWORD, JWT_SECRET (≥32 символов),
#   TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# 2. Поднять backend-стек (БД, Redis, 5 микросервисов)
docker compose up -d --build

# 3. Проверить здоровье
docker compose ps
curl http://localhost:8000/health        # api-gateway → {"status":"healthy",...}
```

Дефолтный пользователь дашборда создаётся при старте: **`test@example.com` / `test123`**.

### Фронтенд (dev)

```bash
cd frontend
npm install --legacy-peer-deps   # React 19 → peer-конфликты, нужен флаг
npm run dev                       # http://localhost:5173
```

> Порт **5173** обязателен — он прописан в `CORS_ORIGINS` api-gateway.

## Документация API

Swagger UI генерируется автоматически: **http://localhost:8000/docs**
(OpenAPI JSON — `/openapi.json`).

## Тесты

Тесты используют stdlib `unittest` и гоняются **внутри уже поднятых контейнеров**
(не требуют установки pytest/зависимостей и работают офлайн):

```powershell
docker compose up -d            # сервисы должны быть запущены
pwsh tests/run-tests.ps1
```

Покрытие:
- `test_spread_calculator.py` — формулы спреда scanner'а (gross/net, комиссии, фильтр)
- `test_pnl_calculator.py` — расчёт P&L executor'а (slippage, комиссии, убыток)
- `test_api.py` — REST API gateway с JWT (login, 401, prices, trades, health)
- `test_integration.py` — сквозной поток `prices → Redis → scanner → opportunities`

Под `pytest` (если установлен) те же файлы запускаются обычным `pytest tests/`.

## Production + мониторинг

Оверрайды `docker-compose.prod.yml` добавляют лимиты ресурсов, рестарт-политику,
ротацию логов и сервисы мониторинга:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

- **Prometheus** — http://localhost:9090 (скрейпит `/metrics` всех 5 сервисов)
- **Grafana** — http://localhost:3000 (логин `admin` / `${GRAFANA_PASSWORD}`),
  дашборд «CriptoParser V3 — Overview» и источник Prometheus подключаются автоматически.

## Переменные окружения

Все переменные описаны в [`.env.example`](.env.example): доступы к TimescaleDB и
Redis, порты сервисов, JWT-секрет и CORS, токен/чат Telegram, пароль Grafana,
адреса API/WS для фронтенда. `.env` в git не коммитится.

## Структура репозитория

```
collector/  scanner/  executor/  notifier/  api-gateway/   # микросервисы
shared/                       # общие config/models/db (монтируется как пакет)
frontend/                     # React 19 + Vite дашборд
scripts/init-db.sql           # схема БД + сиды (биржи, пары, настройки)
tests/                        # тесты + run-tests.ps1
monitoring/                   # prometheus.yml, grafana provisioning + dashboard
docker-compose.yml            # базовый стек
docker-compose.prod.yml       # prod-оверрайды + Prometheus/Grafana
```

## Замечания

- **Реальные спреды малы.** Межбиржевые спреды BTC/ETH почти всегда < 0.3%, поэтому
  при дефолтном `min_spread_pct=0.30` поток opportunities близок к нулю — это
  нормально. Порог настраивается в UI (Settings) без пересборки.
- **Paper trading.** Реальные ордера не выставляются: executor симулирует исполнение
  со slippage 0.1–0.3% и ведёт виртуальные балансы. Kill switch (Settings) мгновенно
  останавливает создание сделок.
- **Сеть.** Collector подключается к биржам по WebSocket — при ограничениях DNS/прокси
  биржи будут отображаться как «disconnected». Это состояние сети, не ошибка приложения.
