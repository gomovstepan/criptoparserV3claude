# MASTER PROMPT: Реализация крипто-арбитражной системы

> Проект реализуется по фазам: junior говорит "Приступай к фазе N".

---

## 1. Архитектура системы

### 1.1. Микросервисы (5 сервисов)

| Сервис | Порт | Назначение | Зависимости |
|--------|------|------------|-------------|
| **api-gateway** | 8000 | Единая точка входа. REST API + WebSocket для frontend. JWT аутентификация. Агрегация данных из TimescaleDB. | TimescaleDB, Redis, Все сервисы (health) |
| **collector** | 8001 | WebSocket подключения к 7 биржам через CCXT Pro. Сбор best bid/ask. Публикация тиков в Redis Stream `prices`. | 7 бирж WS, Redis |
| **scanner** | 8002 | Чтение цен из Redis Stream `prices`. Расчет спредов между биржами. Фильтрация по min_spread. Публикация opportunities в Redis Stream `opportunities`. | Redis, TimescaleDB |
| **executor** | 8003 | Paper trading engine. Чтение opportunities. Симуляция buy/sell с учетом slippage и комиссий. Обновление виртуального баланса. Запись trades в TimescaleDB. | Redis, TimescaleDB |
| **notifier** | 8004 | Telegram бот (aiogram 3.x). Уведомления о спредах и сделках. Команды: /start, /status, /balance, /trades, /killswitch. | Redis, Telegram Bot API |

### 1.2. Data Flow

```
Phase 1: Сбор данных (Collector)
─────────────────────────────────
[Bybit WS] ──┐
[Binance WS]─┤
[KuCoin WS] ─┤    ┌─────────────┐    ┌─────────────────────┐
[Gate.io WS]─┼───>│  Collector  │───>│ Redis: prices stream │
[Bitget WS] ─┤    │   :8001     │    │ (XADD prices *)      │
[CoinEx WS] ─┤    │ CCXT Pro    │    └─────────────────────┘
[BingX WS] ──┘    │ picows      │
                   └─────────────┘

Phase 2: Сканирование (Scanner)
───────────────────────────────
┌─────────────────────┐    ┌─────────────┐    ┌──────────────────────────┐
│ Redis: prices stream │───>│   Scanner   │───>│ Redis: opportunities     │
│ (XREADGROUP)         │    │   :8002     │    │ stream (XADD opp *)      │
└─────────────────────┘    │ calc spread │    └──────────────────────────┘
                           │ filter      │           │
                           └─────────────┘           ▼
                                              ┌──────────────┐
                                              │ TimescaleDB:  │
                                              │ opportunities │
                                              │ hypertable    │
                                              └──────────────┘

Phase 3: Исполнение (Executor - Paper Trading)
─────────────────────────────────────────────
┌──────────────────────────┐    ┌─────────────┐    ┌─────────────────────┐
│ Redis: opportunities     │───>│   Executor  │───>│ Redis: trades stream │
│ stream (XREADGROUP)      │    │   :8003     │    │ (XADD trades *)      │
└──────────────────────────┘    │ simulate    │    └─────────────────────┘
                                │ calc P&L    │           │
                                └─────────────┘           ▼
                                                   ┌──────────────┐
                                                   │ TimescaleDB:  │
                                                   │ trades        │
                                                   │ hypertable    │
                                                   │ balance       │
                                                   └──────────────┘

Phase 4: Уведомления (Notifier)
──────────────────────────────
┌──────────────────────────┐    ┌─────────────┐    ┌─────────────────┐
│ Redis: opportunities     │───>│   Notifier  │───>│ Telegram Bot API │
│ Redis: trades            │    │   :8004     │    │ (aiogram 3.x)    │
└──────────────────────────┘    │ format msg  │    └─────────────────┘
                                │ queue+send  │
                                └─────────────┘

Phase 5: Frontend (React Dashboard)
──────────────────────────────────
┌─────────────────┐    WS /ws     ┌─────────────┐    ┌──────────────────┐
│  React Dashboard│◄─────────────>│ API Gateway │◄───│ TimescaleDB      │
│  (Browser)      │    real-time  │   :8000     │    │ (historical data)│
│                 │               │ REST /api/* │    └──────────────────┘
│  - Price table  │◄──────────────┤ WebSocket   │    ┌──────────────────┐
│  - Spread table │               │ JWT Auth    │◄───│ Redis Streams    │
│  - Trade history│               └─────────────┘    └──────────────────┘
│  - P&L charts   │
└─────────────────┘
```

### 1.3. База данных — TimescaleDB (4 hypertables)

| Hypertable | Chunk Interval | Retention | Compression | Назначение |
|------------|---------------|-----------|-------------|------------|
| **prices** | 1 час | 30 дней | 7 дней | Тиковые данные bid/ask со всех бирж |
| **opportunities** | 1 день | 90 дней | 7 дней | Обнаруженные арбитражные возможности |
| **trades** | 1 день | 1 год | 30 дней | Paper trading сделки с P&L |
| **balance** | 1 день | 1 год | — | История виртуального баланса по биржам |

Дополнительные таблицы (PostgreSQL):
- **users** — пользователи (JWT auth)
- **settings** — системные настройки (min_spread, max_position и т.д.)
- **exchange_configs** — конфигурация 7 бирж (комиссии, rate limits)
- **tracked_pairs** — отслеживаемые пары (BTC/USDT, ETH/USDT и т.д.)
- **audit_log** — лог действий пользователей

Continuous Aggregates:
- **prices_hourly** — часовая статистика цен (avg, min, max, last)
- **pnl_daily** — ежедневный P&L summary (trade_count, total_gross_pnl, total_net_pnl)

### 1.4. Redis Streams (3 потока)

| Stream | Consumer Groups | Maxlen | Назначение |
|--------|----------------|--------|------------|
| **prices** | `scanner-cg`, `writer-cg` | ~100,000 | Тиковые данные от collector |
| **opportunities** | `executor-cg`, `notifier-cg` | ~10,000 | Арбитражные возможности от scanner |
| **trades** | `notifier-cg` | ~10,000 | Результаты paper trades от executor |

Дополнительные Redis структуры:
- **balance:{exchange}** (Hash) — текущий виртуальный баланс по биржам
- **config** (Hash) — runtime конфигурация
- **telegram_queue** (List) — очередь сообщений в Telegram

### 1.5. Техстек

**Backend:**
| Компонент | Версия/Библиотека |
|-----------|-------------------|
| Python | 3.11+ |
| Framework | FastAPI (uvicorn) |
| Биржи API | CCXT Pro (WebSocket) |
| WebSocket client | picows + uvloop |
| База данных | TimescaleDB (PostgreSQL 16) + asyncpg |
| Message Bus | Redis 7+ (redis-py) |
| Auth | PyJWT (HS256) |
| Telegram | aiogram 3.x |
| Логирование | structlog + orjson |
| Метрики | prometheus-client |

**Frontend:**
| Компонент | Версия/Библиотека |
|-----------|-------------------|
| React | 19 |
| Сборка | Vite |
| TypeScript | 5.5+ |
| Стили | Tailwind CSS |
| UI компоненты | shadcn/ui (Radix UI) |
| State management | Zustand |
| Графики | Recharts |
| Иконки | Lucide React |
| Toast | Sonner |
| Routing | React Router DOM |

**Инфраструктура:**
| Компонент | Версия |
|-----------|--------|
| Docker | 24.0+ |
| Docker Compose | 2.20+ |
| TimescaleDB | latest-pg16 |
| Redis | 7-alpine |
| Prometheus | v2.52.0+ |
| Grafana | v10.2.2+ |

---

## 2. Описание всех 16 фаз

### Фаза 0: Подготовка окружения

**Команда запуска:** "Приступай к фазе 0"

**Что делать:**
1. Установить Python 3.11+, Docker, Docker Compose, Node.js 20+
2. Создать структуру моно-репозитория: `collector/`, `scanner/`, `api-gateway/`, `executor/`, `notifier/`, `frontend/`, `shared/`, `scripts/`, `tests/`, `monitoring/`
3. Создать базовые `requirements.txt` для каждого backend-сервиса
4. Создать `docker-compose.yml` с сетью `arbitrage-net`
5. Создать `.env.example` с пустыми значениями

**Как проверить:**
```bash
docker --version && docker-compose --version && python3 --version && node --version
```

**Ожидаемый ответ:**
```
Docker version 24.0+
Docker Compose version 2.20+
Python 3.11+
v20+
```

**Критерий завершения:**
- [ ] `docker --version` выводит 24.0+
- [ ] `python3 --version` выводит 3.11+
- [ ] `node --version` выводит v20+
- [ ] Структура папок создана: `collector/`, `scanner/`, `api-gateway/`, `executor/`, `notifier/`, `frontend/`, `shared/`, `scripts/`, `tests/`, `monitoring/`
- [ ] `.env.example` создан с пустыми значениями для всех переменных

---

### Фаза 1: Docker Compose + TimescaleDB + Redis + 5 сервисов-заглушек

**Команда запуска:** "Приступай к фазе 1"

**Что делать:**
1. Написать `docker-compose.yml` с 7 сервисами: `timescaledb`, `redis`, `collector`, `scanner`, `api-gateway`, `executor`, `notifier`
2. Каждый микросервис — FastAPI заглушка с `GET /health` → `{"status":"ok","service":"название"}`
3. Создать `Dockerfile` для каждого сервиса (python:3.11-slim)
4. Настроить TimescaleDB с volume и авто-созданием БД
5. Настроить Redis с AOF persistence и healthcheck
6. Создать `scripts/init-db.sql` — создание БД и расширения timescaledb
7. Healthcheck для каждого сервиса в Docker

**Как проверить:**
```bash
docker-compose up -d --build
sleep 15
curl -s http://localhost:8000/health
curl -s http://localhost:8001/health
curl -s http://localhost:8002/health
curl -s http://localhost:8003/health
curl -s http://localhost:8004/health
```

**Ожидаемый ответ:**
```json
{"status":"ok","service":"api-gateway"}
{"status":"ok","service":"collector"}
{"status":"ok","service":"scanner"}
{"status":"ok","service":"executor"}
{"status":"ok","service":"notifier"}
```

**Критерий завершения:**
- [ ] `docker-compose ps` показывает 7 контейнеров в статусе `Up`
- [ ] Все 5 health endpoints отвечают `{"status":"ok"}`
- [ ] Redis: `docker-compose exec redis redis-cli ping` → `PONG`
- [ ] TimescaleDB: `docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "SELECT 1"` → `1`

---

### Фаза 2: Конфигурация 7 бирж

**Команда запуска:** "Приступай к фазе 2"

**Что делать:**
1. Создать `shared/config.py` — класс `ExchangeConfig` с данными 7 бирж (fee, rate limits, endpoints)
2. Создать `shared/models.py` — Pydantic модели: `PriceTick`, `Opportunity`, `Trade`
3. Обновить `scripts/init-db.sql` — таблицы `exchange_configs`, `tracked_pairs`, `settings` с начальными данными
4. Создать `collector/exchanges.py` — функция `test_exchange_connection(exchange_id)` через CCXT
5. Создать `shared/db.py` — asyncpg connection pool

**Как проверить:**
```bash
docker-compose down -v && docker-compose up -d --build
sleep 10
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "SELECT exchange, maker_fee_pct, taker_fee_pct FROM exchange_configs;"
```

**Ожидаемый ответ:**
```
 exchange | maker_fee_pct | taker_fee_pct
----------+---------------+---------------
 bybit    | 0.10          | 0.10
 binance  | 0.10          | 0.10
 kucoin   | 0.10          | 0.10
 gateio   | 0.30          | 0.30
 bitget   | 0.10          | 0.10
 coinex   | 0.20          | 0.20
 bingx    | 0.10          | 0.10
```

**Критерий завершения:**
- [ ] Таблица `exchange_configs` содержит 7 записей с корректными комиссиями
- [ ] Таблица `tracked_pairs` содержит 8 активных пар (BTC/USDT и ETH/USDT по 4 биржам)
- [ ] CCXT успешно получает ticker с Binance (public API)
- [ ] Все сервисы перезапускаются без ошибок

---

### Фаза 3: WebSocket Collector — Binance

**Команда запуска:** "Приступай к фазе 3"

**Что делать:**
1. Реализовать WebSocket collector для Binance через CCXT Pro (`watch_order_book`)
2. Подписка на best bid/ask для BTC/USDT
3. Публикация тиков в Redis Stream `prices` через `XADD`
4. Graceful shutdown: закрытие WS соединения, flush данных
5. Health endpoint показывает статус WS подключения

**Как проверить:**
```bash
docker-compose up -d --build collector
curl -s http://localhost:8001/health
sleep 10
docker-compose exec redis redis-cli XREVRANGE prices + - COUNT 3
```

**Ожидаемый ответ:**
```json
{"status":"healthy","service":"collector","ws_connections":1,"redis_connected":true}
```
Redis stream:
```
1) 1) "1720000000000-0"
   2) 1) "exchange"
      2) "binance"
      3) "symbol"
      4) "BTC/USDT"
      5) "bid"
      6) "67432.15"
      7) "ask"
      8) "67433.80"
```

**Критерий завершения:**
- [ ] Collector health показывает `"ws_connections":1`
- [ ] Redis Stream `prices` получает данные каждые 1-3 секунды
- [ ] Каждый тик содержит: exchange, symbol, bid, ask, timestamp
- [ ] При остановке collector — graceful shutdown без ошибок

---

### Фаза 4: WebSocket Collectors — все 7 бирж

**Команда запуска:** "Приступай к фазе 4"

**Что делать:**
1. Расширить collector на все 7 бирж: Bybit, Binance, KuCoin, Gate.io, Bitget, CoinEx, BingX
2. Каждая биржа — отдельная CCXT Pro задача в asyncio event loop
3. Конфигурация пар из БД (`tracked_pairs`, фильтр `is_active = true`)
4. Автоматический reconnect: exponential backoff (100ms -> 1s -> 5s -> 30s -> max 60s)
5. Fallback на REST API (`fetch_ticker`) при недоступности WS > 30 секунд
6. Rate limiting: `enableRateLimit=True` в CCXT

**Как проверить:**
```bash
docker-compose up -d --build collector
curl -s http://localhost:8001/health | python3 -m json.tool
```

**Ожидаемый ответ:**
```json
{
    "status": "healthy",
    "service": "collector",
    "ws_connections": 7,
    "ws_connections_detail": {
        "binance": "connected",
        "bybit": "connected",
        "kucoin": "connected",
        "gateio": "connected",
        "bitget": "connected",
        "coinex": "connected",
        "bingx": "connected"
    },
    "redis_connected": true
}
```

**Критерий завершения:**
- [ ] Health показывает 7 WS соединений, все статусы `connected`
- [ ] Redis Stream получает тики от всех 7 бирж
- [ ] Reconnect срабатывает при имитации обрыва связи
- [ ] Логи не содержат необработанных exceptions

---

### Фаза 5: TimescaleDB запись цен + Redis Streams

**Команда запуска:** "Приступай к фазе 5"

**Что делать:**
1. Batch INSERT тиков из Redis Stream `prices` в TimescaleDB hypertable `prices`
2. Создать consumer group `writer-cg` для чтения из stream
3. Batch: 100 тиков или 1 секунда (что раньше)
4. Hypertable `prices` с `chunk_time_interval = 1 hour`
5. Индексы: `(exchange, symbol, time DESC)`, `(symbol, time DESC)`
6. Compression policy: сжимать чанки старше 7 дней
7. Retention policy: удалять данные старше 30 дней

**Как проверить:**
```bash
docker-compose up -d --build collector
sleep 30
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "SELECT exchange, symbol, COUNT(*) as ticks FROM prices GROUP BY exchange, symbol ORDER BY ticks DESC LIMIT 5;"
```

**Ожидаемый ответ:**
```
 exchange |  symbol   | ticks
----------+-----------+-------
 binance  | BTC/USDT  |   450
 binance  | ETH/USDT  |   445
 bybit    | BTC/USDT  |   420
 bybit    | ETH/USDT  |   418
 kucoin   | BTC/USDT  |   380
```

**Критерий завершения:**
- [ ] В таблице `prices` есть записи от всех 7 бирж
- [ ] Каждая пара представлена на каждой бирже
- [ ] Hypertable создан, chunk_count >= 1
- [ ] Consumer group `writer-cg` обрабатывает stream без лага

---

### Фаза 6: Scanner микросервис

**Команда запуска:** "Приступай к фазе 6"

**Что делать:**
1. Scanner читает цены из Redis Stream `prices` через consumer group `scanner-cg`
2. Расчет спреда: `spread = (ask_A - bid_B) / bid_B * 100` для всех комбинаций бирж
3. Фильтрация по min_spread (default 0.30%) из настроек БД
4. Учет комиссий при расчете net_spread: gross - buy_fee - sell_fee - withdrawal_fee
5. Публикация opportunity в Redis Stream `opportunities`
6. Дедупликация: не публиковать ту же opportunity (symbol + buy_exchange + sell_exchange) в течение 5 секунд
7. Сохранение opportunity в TimescaleDB hypertable `opportunities`

**Как проверить:**
```bash
docker-compose up -d --build scanner
sleep 20
curl -s http://localhost:8002/health | python3 -m json.tool
docker-compose exec redis redis-cli XREVRANGE opportunities + - COUNT 3
```

**Ожидаемый ответ:**
```json
{
    "status": "healthy",
    "service": "scanner",
    "spreads_calculated_per_minute": 3500,
    "opportunities_found_last_hour": 12
}
```

**Критерий завершения:**
- [ ] Scanner health показывает активную обработку
- [ ] Redis Stream `opportunities` получает записи
- [ ] В БД `opportunities` есть записи с корректными gross/net спредами
- [ ] Net spread < gross spread (учтены комиссии)
- [ ] Дедупликация работает (повторный спред в течение 5 секунд не создает дубль)

---

### Фаза 7: Paper Trading Engine (executor)

**Команда запуска:** "Приступай к фазе 7"

**Что делать:**
1. Executor читает opportunities из Redis Stream `opportunities` через consumer group `executor-cg`
2. Симуляция исполнения buy на бирже A и sell на бирже B
3. Учет slippage: random 0.1-0.3% от цены
4. Учет всех комиссий (maker + taker + withdrawal) при расчете P&L
5. Max position: не более 10% от виртуального баланса на сделку
6. Запись сделки в TimescaleDB hypertable `trades`
7. Публикация результата в Redis Stream `trades`
8. Обновление виртуального баланса в Redis Hash `balance:{exchange}`
9. Kill switch endpoint: `POST /killswitch` — немедленная остановка всех сделок

**Начальный виртуальный баланс:**
| Биржа | Начальный баланс USDT |
|-------|---------------------|
| Binance | 10,000 |
| Bybit | 10,000 |
| KuCoin | 10,000 |
| Bitget | 10,000 |
| Gate.io | 5,000 |
| CoinEx | 5,000 |
| BingX | 5,000 |

**Как проверить:**
```bash
docker-compose up -d --build executor
sleep 20
curl -s http://localhost:8003/health | python3 -m json.tool
docker-compose exec redis redis-cli XREVRANGE trades + - COUNT 3
curl -s -X POST http://localhost:8003/killswitch -H "Content-Type: application/json" -d '{"reason":"test"}'
```

**Ожидаемый ответ:**
```json
{
    "status": "healthy",
    "service": "executor",
    "trades_today": 5,
    "total_pnl_today": -12.45,
    "kill_switch_active": false
}
{"status":"activated","reason":"test","timestamp":"2025-07-03T12:15:00Z"}
```

**Критерий завершения:**
- [ ] Executor создает paper trades при получении opportunities
- [ ] Каждый trade записан в БД с корректными P&L (gross и net)
- [ ] Виртуальный баланс обновляется после каждой сделки
- [ ] Killswitch endpoint останавливает создание новых сделок
- [ ] Max position <= 10% от баланса проверяется перед каждой сделкой

---

### Фаза 8: Telegram Notifier

**Команда запуска:** "Приступай к фазе 8"

**Что делать:**
1. Notifier читает opportunities и trades из Redis Streams через consumer group `notifier-cg`
2. Отправка Telegram сообщений при спреде > `notification_spread_threshold` (default 0.50%)
3. Отправка Telegram сообщений при завершении paper trade
4. Rate limiting: max 20 msg/sec (очередь в Redis List `telegram_queue`)
5. aiogram 3.x для Telegram Bot API
6. Команды бота: `/start`, `/status`, `/balance`, `/trades`, `/killswitch`
7. Форматирование сообщений с эмодзи

**Как проверить:**
```bash
docker-compose up -d --build notifier
curl -s http://localhost:8004/health | python3 -m json.tool
curl -s -X POST http://localhost:8004/notify -H "Content-Type: application/json" -d '{"type":"test","message":"Hello from Arbitrage Bot!"}'
```

**Ожидаемый ответ:**
```json
{
    "status": "healthy",
    "service": "notifier",
    "telegram_connected": true,
    "messages_sent_today": 8,
    "queue_length": 0
}
{"status":"queued","message_id":"test_123"}
```

**Критерий завершения:**
- [ ] Notifier health показывает `telegram_connected: true`
- [ ] Команда `/start` в Telegram отвечает приветственным сообщением
- [ ] Команда `/status` показывает статус всех сервисов
- [ ] При opportunity со спредом > 0.50% приходит Telegram уведомление
- [ ] При завершении trade приходит сообщение с P&L
- [ ] Очередь сообщений не растет (rate limiting работает)

---

### Фаза 9: API Gateway (REST + WebSocket)

**Команда запуска:** "Приступай к фазе 9"

**Что делать:**
1. REST API с префиксом `/api/v1/` на FastAPI
2. JWT аутентификация (HS256, expiry 24h)
3. Endpoints: `GET /api/v1/prices`, `GET /api/v1/opportunities`, `GET /api/v1/trades`, `GET /api/v1/balance`, `GET /api/v1/exchanges`, `GET/PUT /api/v1/settings`
4. WebSocket endpoint `/ws` для real-time push данных
5. Чтение исторических данных из TimescaleDB
6. CORS: `allow_origins=["http://localhost:5173"]`
7. Rate limiting: 100 req/min REST, 10 msg/sec WS per client
8. Prometheus метрики на `/metrics`

**Как проверить:**
```bash
docker-compose up -d --build api-gateway
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"test123"}' | python3 -m json.tool
curl -s http://localhost:8000/docs > /dev/null && echo "Swagger OK"
```

**Ожидаемый ответ:**
```json
{
    "status": "healthy",
    "service": "api-gateway",
    "db_connected": true,
    "redis_connected": true,
    "ws_clients_active": 0
}
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400
}
Swagger OK
```

**Критерий завершения:**
- [ ] Swagger UI доступен на `http://localhost:8000/docs`
- [ ] Логин возвращает JWT токен
- [ ] `GET /api/v1/prices` возвращает цены из TimescaleDB
- [ ] `GET /api/v1/opportunities` возвращает спреды
- [ ] `GET /api/v1/trades` возвращает paper trades с пагинацией
- [ ] WebSocket `/ws` принимает подключения
- [ ] CORS настроен для `localhost:5173`

---

### Фаза 10: Frontend скелет + Login

**Команда запуска:** "Приступай к фазе 10"

**Что делать:**
1. React 19 + Vite + TypeScript проект в папке `frontend/`
2. Tailwind CSS + shadcn/ui интеграция
3. Zustand store для auth состояния
4. Router: `/login`, `/dashboard`, `/opportunities`, `/trades`, `/analytics`, `/exchanges`, `/settings`
5. Login страница с формой email/password, валидацией, JWT storage в localStorage
6. Protected routes: редирект на `/login` если нет токена
7. Layout: Navbar + Sidebar + Content Area
8. Тема: Dark по умолчанию (TradingView-стиль, фон `#0a0a14`)

**Как проверить:**
```bash
cd frontend && npm install && npm run dev
```
В браузере: `http://localhost:5173`

**Ожидаемый ответ:**
- Frontend загружается, отображается Login страница с формой

**Критерий завершения:**
- [ ] Frontend доступен на `http://localhost:5173`
- [ ] Страница `/login` отображает форму с email и password
- [ ] Успешный логин сохраняет JWT в localStorage и редиректит на `/dashboard`
- [ ] Sidebar отображает 6 пунктов меню (Dashboard, Opportunities, Trades, Analytics, Exchanges, Settings)
- [ ] Navbar показывает статус системы
- [ ] Темная тема применена (фон `#0a0a14`)

---

### Фаза 11: Dashboard + Opportunities (WS real-time)

**Команда запуска:** "Приступай к фазе 11"

**Что делать:**
1. Dashboard: 4 KPI Cards (Total P&L, Active Opportunities, Today's Trades, Best Spread)
2. Exchange Status Panel: 7 mini-cards со статусом WS, latency
3. Mini P&L Chart (Recharts AreaChart, последние 24 часа)
4. Top 5 Opportunities таблица с WebSocket real-time обновлениями
5. Last 5 Trades таблица
6. Opportunities страница: полная таблица с фильтрами
7. WebSocket клиент: подключение к `ws://localhost:8000/ws`, подписка на channels
8. Автоматический reconnect WS с exponential backoff

**Как проверить:**
```bash
docker-compose up -d --build frontend api-gateway
```
В браузере: открыть `http://localhost:5173`, залогиниться

**Критерий завершения:**
- [ ] Dashboard отображает 4 KPI карточки с актуальными данными
- [ ] 7 Exchange Status cards показывают статус WS
- [ ] P&L Chart рендерит график за 24 часа
- [ ] Top Opportunities таблица обновляется в реальном времени
- [ ] WebSocket reconnect работает

---

### Фаза 12: Trades + Analytics

**Команда запуска:** "Приступай к фазе 12"

**Что делать:**
1. Trades страница: таблица всех paper trades с фильтрами (date, exchange, pair, status, P&L)
2. Pagination: размер страницы 10, 25, 50, 100
3. Detail drawer: подробная информация о сделке при клике
4. Export CSV: кнопка скачивания trades в CSV
5. Analytics страница: 6 статистических KPI, P&L Chart, Cumulative P&L Chart
6. Date Range Picker для аналитики
7. Recharts: AreaChart для P&L, BarChart для trades per day

**Как проверить:**
```bash
docker-compose up -d --build frontend
```
В браузере: открыть `/trades` и `/analytics`

**Критерий завершения:**
- [ ] Trades страница отображает таблицу с пагинацией
- [ ] Фильтры по статусу, паре, бирже работают
- [ ] Detail drawer открывается при клике
- [ ] Export CSV скачивает файл
- [ ] Analytics: 6 стат. карточек, P&L и Cumulative P&L графики

---

### Фаза 13: Exchanges + Settings

**Команда запуска:** "Приступай к фазе 13"

**Что делать:**
1. Exchanges страница: таблица 7 бирж со статусом, комиссиями, балансом
2. Toggle вкл/выкл биржи (is_active)
3. Settings страница: min_spread, max_position, slippage_tolerance, execution_timeout
4. Kill switch кнопка (danger variant, с подтверждением в модальном окне)
5. Тема: Dark/Light/System toggle
6. Настройки сохраняются в TimescaleDB таблицу `settings`
7. Toast уведомления при сохранении (Sonner)

**Как проверить:**
```bash
docker-compose up -d --build frontend api-gateway
```
В браузере: открыть `/exchanges` и `/settings`

**Критерий завершения:**
- [ ] Exchanges: 7 бирж с корректными комиссиями
- [ ] Toggle вкл/выкл меняет статус в БД
- [ ] Settings отображает текущие настройки
- [ ] Kill switch с подтверждением останавливает executor
- [ ] Переключение темы Dark/Light работает

---

### Фаза 14: Интеграция frontend + backend

**Команда запуска:** "Приступай к фазе 14"

**Что делать:**
1. Полная сквозная интеграция: frontend -> API Gateway -> микросервисы
2. WebSocket real-time: collector -> Redis -> API Gateway -> React dashboard
3. Auth flow: login -> JWT -> все protected requests -> logout
4. Error handling: 401 -> redirect login, 500 -> toast error, network error indicator
5. Loading states: skeleton screens
6. Responsive: tablet (sidebar collapsed), mobile (hamburger menu)

**Как проверить:**
```bash
docker-compose down && docker-compose up -d --build
sleep 30
```

**Проверка всех health endpoints:**
```bash
echo "=== API Gateway ===" && curl -s http://localhost:8000/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'status={d[\"status\"]}, ws={d.get(\"ws_clients_active\",0)}')"
echo "=== Collector ===" && curl -s http://localhost:8001/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'status={d[\"status\"]}, ws={d.get(\"ws_connections\",0)}')"
echo "=== Scanner ===" && curl -s http://localhost:8002/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'status={d[\"status\"]}')"
echo "=== Executor ===" && curl -s http://localhost:8003/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'status={d[\"status\"]}, trades={d.get(\"trades_today\",0)}')"
echo "=== Notifier ===" && curl -s http://localhost:8004/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'status={d[\"status\"]}, tg={d.get(\"telegram_connected\",False)}')"
```

**Ожидаемый ответ:**
```
=== API Gateway ===
status=healthy, ws=1
=== Collector ===
status=healthy, ws=7
=== Scanner ===
status=healthy
=== Executor ===
status=healthy, trades=3
=== Notifier ===
status=healthy, tg=True
```

**Критерий завершения:**
- [ ] Все 5 сервисов healthy
- [ ] Frontend загружается без ошибок в консоли
- [ ] Login -> Dashboard flow работает end-to-end
- [ ] WebSocket данные обновляются на dashboard в реальном времени
- [ ] Нет CORS ошибок в браузере
- [ ] Mobile layout работает

---

### Фаза 15: Тесты + Документация + Деплой

**Команда запуска:** "Приступай к фазе 15"

**Что делать:**
1. Unit-тесты: `test_spread_calculator.py`, `test_pnl_calculator.py`
2. Integration тест: collector -> Redis -> scanner -> opportunity
3. API тесты: все REST endpoints с JWT
4. `README.md` — инструкция по запуску
5. `docker-compose.prod.yml` — production overrides
6. `monitoring/grafana-dashboard.json` — dashboard для импорта
7. Обновить `.env.example` с описанием всех переменных

**Как проверить:**
```bash
cd tests && pytest -v --tb=short
curl -s http://localhost:8000/metrics | head -5
curl -s http://localhost:8000/docs > /dev/null && echo "Swagger OK"
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000  # Grafana
curl -s -o /dev/null -w "%{http_code}" http://localhost:9090  # Prometheus
```

**Ожидаемый ответ:**
```
test_spread_calculator.py::test_spread_calculation PASSED
test_pnl_calculator.py::test_pnl_positive_trade PASSED
test_integration.py::test_collector_to_scanner_flow PASSED
========================= 8 passed in 12.34s =========================
200  # Grafana
200  # Prometheus
Swagger OK
```

**Критерий завершения:**
- [ ] Все unit-тесты проходят
- [ ] Integration тест проходит
- [ ] API тесты проходят
- [ ] Swagger UI генерирует документацию
- [ ] Grafana доступна на `localhost:3000`
- [ ] Prometheus доступен на `localhost:9090`
- [ ] README.md содержит инструкцию `docker-compose up -d`


---

## 3. Правила работы для агентов

### 3.1. Код

**Общие правила:**
- Python 3.11+, FastAPI, CCXT Pro, async/await повсеместно
- React 19, TypeScript 5.5+, Tailwind CSS, shadcn/ui
- Docker Compose для всей инфраструктуры
- Комментарии на русском языке (документация, README — на русском)
- Код простой: без сложных паттернов (Strategy, Factory только когда очевидно нужны)
- Максимальная длина функции: 50 строк
- Имена переменных понятные: `buy_price`, а не `bp`

**Python-специфичные:**
```python
# ВСЕГДА используй uvloop
import uvloop
uvloop.install()

# ВСЕГДА включай rate limiting в CCXT
exchange = ccxt.binance({'enableRateLimit': True})

# Graceful shutdown ОБЯЗАТЕЛЕН для каждого сервиса
async def shutdown():
    await close_ws_connections()
    await flush_redis()
    await db_pool.close()

# Structured logging
logger.info("spread_detected", exchange_a="binance", exchange_b="bybit", symbol="BTC/USDT", spread_pct=0.15)
```

**React-специфичные:**
```typescript
// Zustand для state management (НЕ Redux)
import { create } from 'zustand'

// WebSocket с reconnect
const useWebSocket = (url: string) => {
  const [status, setStatus] = useState<'connected' | 'connecting' | 'disconnected'>('connecting')
  // reconnect с exponential backoff
}

// Цвета из дизайн-системы (dark theme)
const colors = {
  pageBg: '#0a0a14',
  surface: '#12121f',
  primary: '#00d4aa',
  success: '#22c55e',
  danger: '#ef4444',
  warning: '#f59e0b',
  textPrimary: '#f1f5f9',
  textSecondary: '#94a3b8',
}
```

**Запрещено:**
- Хардкодить конфигурацию (все в env/config)
- Использовать `any` в TypeScript
- Оставлять `console.log` в production коде
- Коммитить API ключи или пароли
- Оставлять неработающий код (закомментированные блоки)
- Использовать blocking операции в async функциях

### 3.2. Git

**Commit message формат:**
```
фаза-N: краткое описание

- Что сделано (1-2 пункта)
- Как проверить
```

Примеры:
```
фаза-3: WebSocket collector для Binance

- Добавлен CCXT Pro watcher для BTC/USDT
- Публикация тиков в Redis Stream 'prices'

фаза-7: Paper trading engine

- Симуляция buy/sell с учетом slippage
- Kill switch endpoint POST /killswitch
```

**Branching стратегия:**
- `main` — стабильная ветка, только рабочий код
- `фаза-N` — ветка для текущей фазы (N = 0-15)
- После завершения фазы — merge в `main`

```bash
git checkout -b фаза-3
git add .
git commit -m "фаза-3: WebSocket collector для Binance"
git checkout main && git merge фаза-3
```

### 3.3. Проверка

**Каждая фаза проверяется:**
1. curl на health endpoint (должен вернуть JSON с `status: healthy`)
2. Проверка данных в Redis (`XREVRANGE`, `HGETALL`)
3. Проверка данных в БД (SELECT)
4. Проверка логов на отсутствие errors

**Не переходить к следующей фазе без:**
- [ ] Все критерии завершения текущей фазы выполнены
- [ ] Проверочный curl проходит с ожидаемым ответом
- [ ] `docker-compose ps` показывает все сервисы `Up`
- [ ] Логи не содержат критических ошибок
- [ ] Код закоммичен в git

### 3.4. Безопасность

**API ключи:**
- ВСЕГДА в `.env` файле
- НИКОГДА не коммитить в git (`.env` в `.gitignore`)
- Для каждой биржи отдельные переменные: `BINANCE_API_KEY`, `BINANCE_API_SECRET`

**Валидация входных данных:**
- Pydantic models для всех API endpoints
- TypeScript interfaces для всех API ответов
- JWT token проверяется на КАЖДОМ protected endpoint

**Rate limiting:**
- REST: 100 req/min per IP
- WebSocket: 10 msg/sec per client
- Telegram: 20 msg/sec (лимит Bot API)

---

## 4. Troubleshooting

### 4.1. Redis не подключается

**Симптомы:** `ConnectionRefusedError: [Errno 111] Connection refused`

**Решение:**
```bash
# Проверить, что Redis запущен
docker-compose ps redis

# Проверить доступность из контейнера
docker-compose exec collector python -c "import redis; r = redis.Redis(host='redis', port=6379); print(r.ping())"

# Перезапустить Redis
docker-compose restart redis
```

**Причины:**
- Redis еще не успел запуститься (добавить `depends_on` с `condition: service_healthy`)
- Неправильное имя хоста (должно быть `redis`, не `localhost`)

---

### 4.2. TimescaleDB не создает hypertables

**Симптомы:** `timescaledb_information.hypertables` пустая, INSERT медленный

**Решение:**
```bash
# Проверить расширение
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "SELECT * FROM pg_extension WHERE extname = 'timescaledb';"

# Создать вручную
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "SELECT create_hypertable('prices', 'time', if_not_exists => TRUE);"
```

**Причины:**
- Volume не пустой — данные сохранились, init-db.sql не выполнился
- Образ не TimescaleDB (должен быть `timescale/timescaledb:latest-pg16`)

---

### 4.3. WebSocket disconnect

**Симптомы:** `ConnectionClosed`, данные не поступают

**Решение:**
```bash
# Проверить логи
docker-compose logs -f collector | grep -i "ws\|reconnect\|error"

# Проверить доступность биржи
docker-compose exec collector python -c "import ccxt; e = ccxt.binance({'enableRateLimit': True}); print(e.fetch_ticker('BTC/USDT')['bid'])"

# Перезапустить collector
docker-compose restart collector
```

**Причины:**
- Rate limit превышен (429 ошибка)
- Биржа временно недоступна (reconnect должен сработать автоматически)
- CCXT Pro не поддерживает WS для данной биржи — fallback на REST

---

### 4.4. CORS ошибки frontend

**Симптомы:** `Access to fetch at 'http://localhost:8000/...' from origin 'http://localhost:5173' has been blocked by CORS policy`

**Решение:**
```bash
# Проверить CORS
curl -s -D - -o /dev/null -X OPTIONS http://localhost:8000/api/v1/prices \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET"
# Должен быть заголовок: Access-Control-Allow-Origin: http://localhost:5173
```

**В api-gateway/main.py:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### 4.5. Telegram бот не отвечает

**Симптомы:** `telegram_connected: false` в health

**Решение:**
```bash
# Проверить токен
curl -s "https://api.telegram.org/botYOUR_TOKEN/getMe" | python3 -m json.tool

# Проверить polling
docker-compose logs notifier | grep -i "polling\|bot\|error"

# Перезапустить notifier
docker-compose restart notifier
```

**Причины:**
- Неправильный TELEGRAM_BOT_TOKEN
- Бот уже запущен в другом месте (Telegram позволяет только 1 polling)

---

### 4.6. Docker container падает (Exit 1)

**Симптомы:** `docker-compose ps` показывает `Exit 1`

**Решение:**
```bash
# Логи
docker-compose logs --tail=50 SERVICE_NAME

# Запустить без перезапуска для отладки
docker-compose run --rm collector python main.py

# Проверить ресурсы
docker stats --no-stream

# Пересобрать
docker-compose up -d --build --no-deps SERVICE_NAME
```

**Причины:**
- Ошибка в Python коде (SyntaxError, ImportError)
- Недостаточно памяти (OOM)
- Порт уже занят (`lsof -i :PORT`)

---

### 4.7. Scanner не находит спреды

**Симптомы:** `opportunities_found_last_hour: 0`

**Решение:**
```bash
# Проверить, что цены поступают в Redis
docker-compose exec redis redis-cli XLEN prices

# Проверить настройки min_spread
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "SELECT key, value FROM settings WHERE key = 'min_spread_pct';"

# Проверить логи scanner
docker-compose logs -f scanner
```

**Причины:**
- min_spread слишком высокий (попробовать 0.05% для теста)
- Цены не поступают от collector
- Consumer group scanner-cg не создан

---

### 4.8. Executor не создает trades

**Симптомы:** `trades_today: 0`, но opportunities есть

**Решение:**
```bash
# Проверить баланс
docker-compose exec redis redis-cli HGETALL balance:binance

# Проверить killswitch
curl -s http://localhost:8003/health | python3 -c "import sys,json; d=json.load(sys.stdin); print('kill_switch:', d.get('kill_switch_active'))"

# Проверить очередь opportunities
docker-compose exec redis redis-cli XLEN opportunities
```

**Причины:**
- Killswitch активирован
- Виртуальный баланс = 0 (не инициализирован)
- Consumer group executor-cg не создан

---

### 4.9. Frontend не подключается к WebSocket

**Симптомы:** WS статус "disconnected", данные не обновляются

**Решение:**
```bash
# Проверить, что api-gateway WebSocket работает
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8000/ws

# Проверить логи api-gateway
docker-compose logs -f api-gateway

# Проверить, что Redis streams не пустые
docker-compose exec redis redis-cli XLEN prices
docker-compose exec redis redis-cli XLEN opportunities
```

**Причины:**
- API Gateway не запущен
- CORS блокирует WS handshake
- Брандмауэр блокирует порт 8000/5173

---

### 4.10. Медленная запись в TimescaleDB

**Симптомы:** Redis stream растет, лаг consumer group увеличивается

**Решение:**
```bash
# Проверить размер batch
docker-compose logs collector | grep -i "batch\|insert"

# Проверить индексы
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "SELECT indexname FROM pg_indexes WHERE tablename = 'prices';"

# Ручной flush
docker-compose exec redis redis-cli XINFO GROUPS prices
```

**Причины:**
- Batch size слишком маленький (увеличить до 500)
- Нет индексов на (exchange, symbol, time)
- TimescaleDB на HDD вместо SSD

---

### 4.11. Где смотреть логи

```bash
# Логи конкретного сервиса
docker-compose logs -f SERVICE_NAME

# Последние 100 строк
docker-compose logs --tail=100 SERVICE_NAME

# Все сервисы
docker-compose logs -f

# С временными метками
docker-compose logs -f --timestamps collector

# Поиск ошибок
docker-compose logs collector | grep -i "error\|exception\|failed"
```

### 4.12. Как debug

| Уровень | Команда | Когда использовать |
|---------|---------|-------------------|
| Логи сервиса | `docker-compose logs SERVICE` | Всегда первым делом |
| Python traceback | В логах сервиса | При Exception |
| Health endpoint | `curl http://localhost:PORT/health` | Быстрая проверка |
| Redis | `docker-compose exec redis redis-cli INFO` | Проверка memory |
| БД | `docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "SELECT ..."` | SQL запросы |
| Сеть | `docker network inspect arbitrage-net` | Проблемы connectivity |
| Ресурсы | `docker stats --no-stream` | OOM, CPU throttling |

---

## 5. Переменные окружения (.env.example)

```bash
# ============================================
# БАЗА ДАННЫХ (TimescaleDB)
# ============================================
POSTGRES_HOST=timescaledb
POSTGRES_PORT=5432
POSTGRES_USER=arbitrage
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=arbitrage_db

# ============================================
# REDIS
# ============================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# ============================================
# API GATEWAY
# ============================================
API_GATEWAY_PORT=8000
JWT_SECRET=your_jwt_secret_key_min_32_chars_long
JWT_EXPIRY_HOURS=24
CORS_ORIGINS=http://localhost:5173

# ============================================
# COLLECTOR
# ============================================
COLLECTOR_PORT=8001

# ============================================
# SCANNER
# ============================================
SCANNER_PORT=8002

# ============================================
# EXECUTOR
# ============================================
EXECUTOR_PORT=8003

# ============================================
# NOTIFIER (Telegram)
# ============================================
NOTIFIER_PORT=8004
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id

# ============================================
# PROMETHEUS / GRAFANA
# ============================================
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_PASSWORD=admin

# ============================================
# FRONTEND
# ============================================
FRONTEND_PORT=5173
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```


---

## 6. Зависимости

### 6.1. Backend (requirements.txt)

**Все backend-сервисы (общие зависимости):**
```
# Web framework
fastapi>=0.111.0
uvicorn[standard]>=0.30.0

# Async
asyncio-mqtt>=0.16.0

# Database
asyncpg>=0.29.0
alembic>=1.13.0

# Message Bus
redis>=5.0.0

# Crypto exchanges
ccxt>=4.3.0

# Performance
uvloop>=0.19.0
orjson>=3.10.0

# Logging
structlog>=24.1.0

# Metrics
prometheus-client>=0.20.0

# Validation
pydantic>=2.7.0
pydantic-settings>=2.2.0

# Environment
python-dotenv>=1.0.0
```

**Дополнительно для api-gateway:**
```
pyjwt>=2.8.0
python-multipart>=0.0.9  # для form-data (login)
```

**Дополнительно для notifier:**
```
aiogram>=3.7.0
aiohttp>=3.9.0  # aiogram dependency
```

**Dev / тесты:**
```
pytest>=8.2.0
pytest-asyncio>=0.23.0
httpx>=0.27.0  # для тестов FastAPI
```

### 6.2. Frontend (package.json ключевые)

```json
{
  "name": "arbitrage-dashboard",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^6.24.0",
    "zustand": "^4.5.0",
    "recharts": "^2.12.0",
    "lucide-react": "^0.400.0",
    "sonner": "^1.5.0",
    "axios": "^1.7.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.3.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.5.0",
    "vite": "^5.3.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

### 6.3. Docker Compose services

```yaml
version: "3.8"

services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - tsdb_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  collector:
    build: ./collector
    ports:
      - "8001:8001"
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped

  scanner:
    build: ./scanner
    ports:
      - "8002:8002"
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
      timescaledb:
        condition: service_healthy
    restart: unless-stopped

  executor:
    build: ./executor
    ports:
      - "8003:8003"
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
      timescaledb:
        condition: service_healthy
    restart: unless-stopped

  notifier:
    build: ./notifier
    ports:
      - "8004:8004"
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped

  api-gateway:
    build: ./api-gateway
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
      timescaledb:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    env_file: .env
    depends_on:
      - api-gateway

  prometheus:
    image: prom/prometheus:v2.52.0
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:10.2.2
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana-dashboard.json:/var/lib/grafana/dashboards/default.json

volumes:
  tsdb_data:
  prometheus_data:
  grafana_data:

networks:
  default:
    name: arbitrage-net
```

---

## 7. API Quick Reference

### 7.1. REST Endpoints

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `GET` | `/health` | Health check (все сервисы) | Нет |
| `GET` | `/metrics` | Prometheus метрики | Нет |
| `POST` | `/api/v1/auth/login` | Логин, получение JWT | Нет |
| `POST` | `/api/v1/auth/register` | Регистрация | Нет |
| `GET` | `/api/v1/prices` | Список цен (фильтры: exchange, symbol, limit) | JWT |
| `GET` | `/api/v1/opportunities` | Список спредов (фильтры: symbol, min_spread, limit) | JWT |
| `GET` | `/api/v1/trades` | Список trades (пагинация: page, page_size) | JWT |
| `GET` | `/api/v1/trades/export` | Экспорт trades в CSV | JWT |
| `GET` | `/api/v1/balance` | Виртуальный баланс по биржам | JWT |
| `GET` | `/api/v1/exchanges` | Список бирж со статусом | JWT |
| `GET` | `/api/v1/settings` | Текущие настройки | JWT |
| `PUT` | `/api/v1/settings` | Обновление настроек | JWT |
| `POST` | `/api/v1/killswitch` | Аварийная остановка | JWT |
| `GET` | `/api/v1/analytics/pnl` | P&L аналитика (параметр: days) | JWT |
| `GET` | `/docs` | Swagger UI (автогенерация FastAPI) | Нет |
| `POST` | `/killswitch` | Kill switch (executor, прямой) | Нет |
| `POST` | `/notify` | Тестовое уведомление (notifier) | Нет |

### 7.2. WebSocket Channels

**Endpoint:** `ws://localhost:8000/ws`

**Протокол:**
```json
// Клиент -> Сервер (подписка)
{"action": "subscribe", "channels": ["prices", "opportunities", "trades"]}

// Клиент -> Сервер (отписка)
{"action": "unsubscribe", "channels": ["prices"]}

// Сервер -> Клиент (price tick)
{"type": "price", "data": {"exchange": "binance", "symbol": "BTC/USDT", "bid": 67432.15, "ask": 67433.80, "time": "2025-07-03T12:00:00Z"}}

// Сервер -> Клиент (opportunity)
{"type": "opportunity", "data": {"symbol": "BTC/USDT", "buy_exchange": "binance", "sell_exchange": "bybit", "gross_spread_pct": 0.47, "net_spread_pct": 0.27}}

// Сервер -> Клиент (trade)
{"type": "trade", "data": {"id": "trade_123", "symbol": "BTC/USDT", "net_pnl": 24.50, "status": "completed"}}

// Heartbeat (сервер -> клиент каждые 30 сек)
{"type": "ping"}

// Клиент отвечает:
{"type": "pong"}
```

### 7.3. Telegram Bot Commands

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие, список команд |
| `/status` | Статус всех сервисов (WS, scanner, executor) |
| `/balance` | Виртуальный баланс по биржам |
| `/trades [N]` | Последние N сделок (default: 5) |
| `/settings` | Текущие настройки (min_spread, max_position) |
| `/killswitch` | Аварийная остановка (с подтверждением) |

---

## 8. Правила именования

### 8.1. Файлы

| Тип | Формат | Пример |
|-----|--------|--------|
| Модуль Python | `snake_case.py` | `spread_calculator.py` |
| Класс Python | `PascalCase` | `SpreadCalculator` |
| Функция Python | `snake_case` | `calculate_net_spread` |
| Переменная Python | `snake_case` | `buy_price` |
| Константа Python | `UPPER_SNAKE_CASE` | `MIN_SPREAD_PCT` |
| Компонент React | `PascalCase.tsx` | `KPICard.tsx` |
| Хук React | `useCamelCase.ts` | `useWebSocket.ts` |
| Store Zustand | `camelCaseStore.ts` | `spreadStore.ts` |
| CSS/Utility | `kebab-case` | `text-primary` |
| API endpoint | `kebab-case` | `/api/v1/opportunities` |
| Env variable | `UPPER_SNAKE_CASE` | `POSTGRES_HOST` |

### 8.2. Структура директорий

```
.
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env
├── .env.example
├── .gitignore
├── README.md
│
├── api-gateway/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # FastAPI app entry point
│   ├── routers/
│   │   ├── prices.py
│   │   ├── opportunities.py
│   │   ├── trades.py
│   │   ├── balance.py
│   │   ├── exchanges.py
│   │   ├── settings.py
│   │   └── killswitch.py
│   ├── websocket.py            # WS endpoint
│   ├── auth.py                 # JWT utils
│   └── rate_limiter.py
│
├── collector/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # FastAPI app + WS loop
│   ├── ws_client.py            # CCXT Pro WS connections
│   ├── redis_publisher.py      # XADD prices
│   ├── db_writer.py            # Batch writer to TimescaleDB
│   ├── exchange_factory.py     # CCXT exchange factory
│   └── reconnect.py            # Reconnect logic
│
├── scanner/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── spread_calculator.py
│   └── dedup.py               # Opportunity deduplication
│
├── executor/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── paper_trading.py        # PaperTradingEngine
│   ├── balance.py              # Balance management
│   └── pnl.py                  # P&L calculator
│
├── notifier/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── bot.py                  # aiogram router + commands
│   ├── formatter.py            # Message formatting
│   └── queue.py                # TelegramQueue with rate limiting
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx            # Entry point
│   │   ├── App.tsx             # Root + Router
│   │   ├── index.css           # Tailwind + global styles
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Opportunities.tsx
│   │   │   ├── Trades.tsx
│   │   │   ├── Analytics.tsx
│   │   │   ├── Exchanges.tsx
│   │   │   └── Settings.tsx
│   │   ├── components/
│   │   │   ├── Navbar.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Layout.tsx
│   │   │   ├── KPICard.tsx
│   │   │   ├── ExchangeStatusCard.tsx
│   │   │   ├── PriceTable.tsx
│   │   │   ├── OpportunitiesTable.tsx
│   │   │   ├── TradeTable.tsx
│   │   │   ├── PnLChart.tsx
│   │   │   ├── CumulativePnLChart.tsx
│   │   │   ├── TradesPerDayChart.tsx
│   │   │   ├── ExchangeDistributionChart.tsx
│   │   │   ├── KillSwitchButton.tsx
│   │   │   ├── ThemeToggle.tsx
│   │   │   ├── SettingsForm.tsx
│   │   │   ├── ExportCSV.tsx
│   │   │   ├── DateRangePicker.tsx
│   │   │   ├── LoadingSkeleton.tsx
│   │   │   ├── ErrorBoundary.tsx
│   │   │   └── NetworkStatus.tsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   └── useAuth.ts
│   │   ├── store/
│   │   │   ├── authStore.ts
│   │   │   ├── spreadStore.ts
│   │   │   ├── tradeStore.ts
│   │   │   └── settingsStore.ts
│   │   ├── lib/
│   │   │   ├── api.ts          # Axios instance + JWT
│   │   │   └── utils.ts        # Helpers
│   │   └── types/
│   │       └── index.ts        # TypeScript interfaces
│   └── public/
│
├── shared/                     # Общие модули (копируются в контейнеры)
│   ├── models.py               # Pydantic models
│   ├── config.py               # Exchange configs
│   └── db.py                   # DB pool + queries
│
├── scripts/
│   └── init-db.sql             # Инициализация TimescaleDB
│
├── tests/
│   ├── test_spread_calculator.py
│   ├── test_pnl_calculator.py
│   ├── test_integration.py
│   └── test_api.py
│
└── monitoring/
    ├── prometheus.yml
    └── grafana-dashboard.json
```

---

## 9. Критерии качества

**Код:**
- [ ] Код проходит проверку curl (health endpoints отвечают)
- [ ] Нет хардкода — все конфигурации в `.env` или БД `settings`
- [ ] Graceful error handling: try/except с логированием, сервис НЕ падает
- [ ] Structured logging: JSON формат через structlog, correlation ID
- [ ] Комментарии на русском для сложных участков

**Безопасность:**
- [ ] API ключи только в `.env`, не в коде
- [ ] JWT с expiry, refresh token
- [ ] Rate limiting на все endpoints
- [ ] Input validation через Pydantic

**Производительность:**
- [ ] End-to-end latency < 100ms (тик -> фронтенд)
- [ ] Scanner detection < 50ms
- [ ] Paper trading execution < 200ms
- [ ] Batch INSERT в TimescaleDB (100-500 тиков за раз)
- [ ] WebSocket reconnect < 3 секунд

**Надежность:**
- [ ] Health check на каждом сервисе
- [ ] Graceful shutdown (SIGTERM/SIGINT)
- [ ] Auto-reconnect WS с exponential backoff
- [ ] Circuit Breaker (5 ошибок -> OPEN на 30 сек)
- [ ] Dead Letter Queue для ошибочных сообщений

**Frontend:**
- [ ] First load < 2 секунд (Lighthouse)
- [ ] WS reconnect < 3 секунд
- [ ] Responsive: desktop (1280px+), tablet (768px+), mobile (< 768px)
- [ ] Dark theme по умолчанию
- [ ] Skeleton loaders при загрузке

**DevOps:**
- [ ] Docker Compose запускается одной командой
- [ ] Все сервисы имеют healthcheck
- [ ] Prometheus метрики на `/metrics`
- [ ] Grafana dashboard импортируется

---

## 10. Post-MVP Roadmap

### Месяц 2

| Фича | Описание | Сложность |
|------|----------|-----------|
| **Multi-user support** | Роли (admin, trader, viewer), команды, изоляция данных | Средняя |
| **Webhook notifications** | Внешние webhook для интеграций (Discord, Slack) | Низкая |
| **Real trading** | Реальные API ключи, исполнение ордеров через CCXT | Высокая |
| **Billing & подписки** | Stripe/Paddle интеграция, тарифные планы | Средняя |

### Месяц 3

| Фича | Описание | Сложность |
|------|----------|-----------|
| **Triangular arbitrage** | Треугольный арбитраж на одной бирже | Высокая |
| **Funding rate arbitrage** | Арбитраж спот-перпетуал спредов | Средняя |
| **Backtesting engine** | Историческое тестирование стратегий | Высокая |
| **Custom strategies** | UI для настройки кастомных стратегий | Средняя |

### Месяц 4-5

| Фича | Описание | Сложность |
|------|----------|-----------|
| **DEX integration** | Uniswap, PancakeSwap через Web3 | Высокая |
| **AI insights** | ML-подсказки по оптимальным настройкам | Высокая |
| **Mobile app** | React Native приложение | Высокая |
| **White-label** | Кастомизация брендинга для партнеров | Средняя |

### Технический долг (приоритетно)

- [ ] Kubernetes оркестрация (вместо Docker Compose)
- [ ] Redis Cluster (вместо single instance)
- [ ] TimescaleDB read replicas
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] E2E тесты (Playwright)
- [ ] Vault для секретов (вместо .env)
- [ ] Distributed tracing (OpenTelemetry)
- [ ] ELK stack для централизованного логирования

---

*MASTER PROMPT v1.0 | Крипто-арбитражная SaaS-система | 5 микросервисов, 16 фаз, Python 3.11+, React 19*
