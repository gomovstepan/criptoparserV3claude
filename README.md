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
| frontend | 5173 | React 19 дашборд (в контейнере — nginx, проксирует `/api` и `/ws` на api-gateway) |
| timescaledb | 5432 | Хранилище временных рядов (PostgreSQL 18 + TimescaleDB) |
| redis | 6379 | Streams (шина) + балансы + kill switch + дедуп |
| prometheus | 9090 | Сбор метрик (стек мониторинга) |
| grafana | 3000 | Дашборды метрик и логов (стек мониторинга) |
| loki | 3100 | Хранилище логов, наполняется Promtail (стек мониторинга) |

Наружу публикуются только **8000** (api-gateway) и **5173** (фронтенд). Порты
8001–8004 доступны лишь внутри сети `arbitrage-net` — проверять их через
`docker compose exec`, а не с хоста.

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

# 2. Поднять стек (БД, Redis, 5 микросервисов, фронтенд).
#    Прод-настройки — restart-политика, ротация docker-логов, лимиты ресурсов —
#    уже встроены в базовый файл через якорь x-prod-defaults.
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

Никаких env-файлов для фронтенда заводить не нужно: `vite.config.ts` проксирует
`/api` и `/ws` на `localhost:8000` — ровно так же, как это делает nginx в
контейнере. Поэтому api-gateway должен быть поднят (`docker compose up -d`).

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

Покрытие (6 наборов):
- `test_spread_calculator.py` — формулы спреда scanner'а (gross/net, комиссии, фильтр)
- `test_depth.py` — VWAP-проход по стакану (`shared/depth.py`), свежесть глубины
- `test_pnl_calculator.py` — формула P&L executor'а (`pnl.settle_trade`)
- `test_paper_trading.py` — движок сделок: kill switch, пороги, тонкий стакан, дельты балансов
- `test_api.py` — REST API gateway с JWT (login, 401, prices, trades, health)
- `test_integration.py` — сквозной поток `prices → Redis → scanner → opportunities`

Запускать их с хоста через `pytest tests/` нельзя: `test_api` и `test_integration`
обращаются к `localhost:8000` и Redis **изнутри** контейнера api-gateway.

## Мониторинг

Prometheus, Grafana, Loki и Promtail живут в отдельном compose-файле и
подключаются к внешней сети `arbitrage-net`, поэтому основной стек должен быть
поднят первым:

```bash
docker compose up -d                                  # сначала основной стек
docker compose -f docker-compose.monitoring.yml up -d  # затем мониторинг
```

- **Prometheus** — http://localhost:9090 (скрейпит `/metrics` всех 5 сервисов)
- **Grafana** — http://localhost:3000 (логин `admin` / `${GRAFANA_PASSWORD}`),
  дашборды «CriptoParser V3 — Overview» и «Logs», источники Prometheus и Loki
  подключаются автоматически.
- **Loki** — http://localhost:3100, хранит 7 дней; Promtail читает `./logs/*.log`.

## Переменные окружения

Все переменные описаны в [`.env.example`](.env.example): доступы к TimescaleDB и
Redis, порты сервисов, JWT-секрет и CORS, токен/чат Telegram, пароль Grafana,
уровень логирования. `VITE_*` там намеренно нет — фронтенд ходит по
относительным путям (dev-прокси в `vite.config.ts`, nginx в контейнере).

> **`.env` должен быть локальным.** Он перечислен в `.gitignore`, но был
> закоммичен раньше, чем правило появилось, — а `.gitignore` не влияет на уже
> отслеживаемые файлы. Прежде чем класть туда настоящие секреты, выполните
> `git rm --cached .env` и убедитесь, что он больше не в `git ls-files`.

## Структура репозитория

```
collector/  scanner/  executor/  notifier/  api-gateway/   # микросервисы
shared/                       # общие config/models/db/depth/logging (монтируется как пакет)
frontend/                     # React 19 + Vite дашборд
scripts/init-db.sql           # схема БД + сиды (биржи, пары, настройки)
scripts/migrate-*.sql         # миграции для уже существующей БД (init-db.sql
                              #   выполняется только на пустом томе)
tests/                        # тесты + run-tests.ps1
monitoring/                   # prometheus.yml, loki/promtail, grafana provisioning
docker-compose.yml            # весь стек, прод-настройки встроены
docker-compose.monitoring.yml # Prometheus + Grafana + Loki + Promtail
```

## Замечания

- **Реальные спреды малы.** Межбиржевые спреды BTC/ETH почти всегда < 0.3%, поэтому
  при дефолтном `min_spread_pct=0.30` поток opportunities близок к нулю — это
  нормально. Порог настраивается в UI (Settings) без пересборки.
- **Paper trading.** Реальные ордера не выставляются. Executor симулирует исполнение
  проходом по реальному стакану: покупка «съедает» asks, продажа — bids, цены сделки
  это VWAP уровней. Проскальзывание не задаётся процентом, а получается из самой
  книги; если глубины не хватает или она устарела (>5 с), сделка пропускается.
  Kill switch (Settings) останавливает создание сделок.
- **Не всякий спред станет сделкой.** Executor заново проходит по стакану в момент
  исполнения и часто отказывается — это нормально, так отсеиваются спреды, которых
  на реальном объёме нет.
- **Дневной лимит убытка (ТЗ, E-014) не реализован.** Его строка в таблице
  `settings` (вместе с legacy-ключами `slippage_tolerance_pct` и
  `execution_timeout_sec`) осталась как сид, но из UI и API эти параметры
  убраны — форма настроек показывает только то, что сервисы реально читают.
- **Сеть.** Collector подключается к биржам по WebSocket — при ограничениях DNS/прокси
  биржи будут отображаться как «disconnected». Это состояние сети, не ошибка приложения.
