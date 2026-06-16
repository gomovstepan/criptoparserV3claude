# Execution Plan: Крипто-арбитражная SaaS-система

> **Для:** 1 junior Python-разработчик (через kimi swarm)
> **Стек:** Python 3.11+, FastAPI, CCXT, TimescaleDB, Redis Streams, React 19, Docker Compose
> **Микросервисы:** collector (8001), scanner (8002), api-gateway (8000), executor (8003), notifier (8004)
> **Биржи:** Bybit, Binance, KuCoin, Gate.io, Bitget, CoinEx, BingX (7)
> **Формат:** Одна команда junior'а = одна фаза

---

## Фаза 0: Подготовка окружения

**Команда junior'а:** "Приступай к фазе 0"

**Что будет сделано:**
- Установка Python 3.11+, Docker, Docker Compose, Node.js 20+, npm
- Создание структуры моно-репозитория с 5 папками под микросервисы
- Инициализация virtualenv и базовых `requirements.txt` для каждого сервиса
- Создание `docker-compose.yml` с базовой сетью `arbitrage-net`

**Файлы, которые создаются/изменяются:**
- `docker-compose.yml` — корневой compose-файл (пока пустой, только сеть)
- `collector/requirements.txt` — зависимости: fastapi, uvicorn, ccxt, redis, asyncpg, prometheus-client
- `scanner/requirements.txt` — зависимости: fastapi, uvicorn, redis, asyncpg, prometheus-client
- `api-gateway/requirements.txt` — зависимости: fastapi, uvicorn, redis, asyncpg, pyjwt, prometheus-client
- `executor/requirements.txt` — зависимости: fastapi, uvicorn, redis, asyncpg, prometheus-client
- `notifier/requirements.txt` — зависимости: fastapi, uvicorn, redis, aiogram, prometheus-client
- `frontend/package.json` — React 19 + Vite проект
- `.env.example` — шаблон переменных окружения

**Как запустить:**
```bash
# Проверка окружения
docker --version && docker-compose --version && python3 --version && node --version

# Сборка сети
docker-compose up -d

# Проверка, что сеть создана
docker network ls | grep arbitrage-net
```

**Как проверить:**
```bash
# Проверка Python
curl -s http://localhost:8001/health || echo "collector not ready yet - OK for phase 0"
```
**Ожидаемый ответ:**
```
collector not ready yet - OK for phase 0
```

**Критерий завершения:**
- [ ] `docker --version` выводит версию 24.0+
- [ ] `python3 --version` выводит 3.11+
- [ ] `node --version` выводит v20+
- [ ] Структура папок создана: `collector/`, `scanner/`, `api-gateway/`, `executor/`, `notifier/`, `frontend/`
- [ ] `.env.example` создан с пустыми значениями для всех переменных

---

## Фаза 1: Docker Compose + TimescaleDB + Redis + 5 сервисов-заглушек

**Команда junior'а:** "Приступай к фазе 1"

**Что будет сделано:**
- Наполнение `docker-compose.yml` сервисами: `timescaledb`, `redis`, `collector`, `scanner`, `api-gateway`, `executor`, `notifier`
- Каждый микросервис — FastAPI заглушка с `GET /health` endpoint (возвращает `{"status":"ok"}`)
- TimescaleDB с volume для персистентности и авто-созданием БД
- Redis с включенным AOF и healthcheck
- Healthcheck для каждого сервиса в Docker

**Файлы, которые создаются/изменяются:**
- `docker-compose.yml` — полный compose со всеми 7 сервисами + depends_on
- `collector/main.py` — FastAPI заглушка, `GET /health` → `{"status":"ok","service":"collector"}`
- `collector/Dockerfile` — python:3.11-slim, копирует requirements и main.py
- `scanner/main.py` — FastAPI заглушка, `GET /health`
- `scanner/Dockerfile` — python:3.11-slim
- `api-gateway/main.py` — FastAPI заглушка, `GET /health`
- `api-gateway/Dockerfile` — python:3.11-slim
- `executor/main.py` — FastAPI заглушка, `GET /health`
- `executor/Dockerfile` — python:3.11-slim
- `notifier/main.py` — FastAPI заглушка, `GET /health`
- `notifier/Dockerfile` — python:3.11-slim
- `scripts/init-db.sql` — создание БД и расширения timescaledb

**Как запустить:**
```bash
# Запуск всех сервисов
docker-compose up -d --build

# Ждем 15 секунд для инициализации БД
sleep 15

# Проверка статуса
docker-compose ps
```

**Как проверить:**
```bash
# Проверка всех 5 сервисов
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
- [ ] `docker-compose ps` показывает 7 контейнеров (postgres, redis + 5 сервисов) в статусе `Up`
- [ ] Все 5 health endpoints отвечают `{"status":"ok"}`
- [ ] Redis доступен: `docker-compose exec redis redis-cli ping` → `PONG`
- [ ] TimescaleDB доступна: `docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "SELECT 1"` → `1`

---

## Фаза 2: Конфигурация 7 бирж

**Команда junior'а:** "Приступай к фазе 2"

**Что будет сделано:**
- Создание конфигурационного модуля с данными всех 7 бирж (fee, rate limits, endpoints)
- Модуль загрузки конфигурации из `.env` и TimescaleDB
- Инициализация таблицы `exchange_configs` данными 7 бирж
- Создание таблицы `tracked_pairs` с парами P1 (BTC/USDT, ETH/USDT по 4 биржам)
- Проверка подключения к биржам через CCXT (REST, без API ключей — public данные)

**Файлы, которые создаются/изменяются:**
- `shared/config.py` — класс `ExchangeConfig` с данными всех 7 бирж
- `shared/models.py` — Pydantic модели: `Price`, `Opportunity`, `Trade`, `ExchangeConfig`
- `scripts/init-db.sql` — обновлён: добавлены таблицы `exchange_configs`, `tracked_pairs`, `settings`
- `collector/exchanges.py` — функция `test_exchange_connection(exchange_id)` через CCXT

**Как запустить:**
```bash
# Пересобрать и запустить с обновлённой инициализацией БД
docker-compose down -v
docker-compose up -d --build

# Ждём инициализации БД
sleep 10
```

**Как проверить:**
```bash
# Проверка данных бирж в БД
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "SELECT exchange, maker_fee_pct, taker_fee_pct FROM exchange_configs;"

# Проверка пар
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "SELECT symbol, exchange FROM tracked_pairs WHERE is_active = true;"

# Проверка подключения к бирже через CCXT
docker-compose exec collector python -c "
import ccxt
exchange = ccxt.binance({'enableRateLimit': True})
ticker = exchange.fetch_ticker('BTC/USDT')
print(f\"BTC/USDT bid={ticker['bid']}, ask={ticker['ask']}\")
"
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
BTC/USDT bid=67432.15, ask=67433.80
```

**Критерий завершения:**
- [ ] Таблица `exchange_configs` содержит 7 записей с корректными комиссиями
- [ ] Таблица `tracked_pairs` содержит 8 активных пар (BTC/USDT и ETH/USDT по 4 биржам)
- [ ] CCXT успешно получает ticker с Binance (public API)
- [ ] Все сервисы перезапускаются без ошибок

---

## Фаза 3: WebSocket Collector — Binance

**Команда junior'а:** "Приступай к фазе 3"

**Что будет сделано:**
- Реализация WebSocket collector для одной биржи (Binance) с использованием CCXT Pro
- Подписка на order book (best bid/ask) для пары BTC/USDT
- Публикация тиков в Redis Stream `prices` через `XADD`
- Graceful shutdown: закрытие WS соединения, flush данных
- Health endpoint показывает статус WS подключения

**Файлы, которые создаются/изменяются:**
- `collector/main.py` — обновлён: добавлен WebSocket цикл для Binance BTC/USDT
- `collector/ws_client.py` — класс `BinanceCollector`, методы `start()`, `stop()`, `on_message()`
- `collector/redis_publisher.py` — функция `publish_price(exchange, symbol, bid, ask)` → `XADD prices * ...`
- `shared/models.py` — обновлён: добавлена Pydantic модель `PriceTick`

**Как запустить:**
```bash
# Пересобрать только collector
docker-compose up -d --build collector

# Логи collector
docker-compose logs -f collector
```

**Как проверить:**
```bash
# Проверка health collector
curl -s http://localhost:8001/health

# Проверка данных в Redis Stream (должен быть хотя бы 1 тик за 10 сек)
sleep 10
docker-compose exec redis redis-cli XREVRANGE prices + - COUNT 3
```
**Ожидаемый ответ:**
```json
// health
{"status":"healthy","service":"collector","ws_connections":1,"redis_connected":true}

// redis stream (пример)
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
- [ ] При остановке `docker-compose stop collector` — graceful shutdown без ошибок

---

## Фаза 4: WebSocket Collectors — все 7 бирж

**Команда junior'а:** "Приступай к фазе 4"

**Что будет сделано:**
- Расширение collector на все 7 бирж: Bybit, Binance, KuCoin, Gate.io, Bitget, CoinEx, BingX
- Каждая биржа — отдельная CCXT Pro WebSocket задача в asyncio event loop
- Конфигурация пар из БД (tracked_pairs), фильтрация по `is_active = true`
- Автоматический reconnect с exponential backoff (100ms → 1s → 5s → 30s)
- Fallback на REST API при недоступности WS > 30 секунд
- Rate limiting через CCXT `enableRateLimit=True`

**Файлы, которые создаются/изменяются:**
- `collector/main.py` — обновлён: запускает коллекторы для всех активных бирж/пар
- `collector/ws_client.py` — обновлён: обобщён класс `ExchangeCollector`, параметризован exchange_id
- `collector/exchange_factory.py` — фабрика: `create_collector(exchange_id)` возвращает CCXT Pro instance
- `collector/reconnect.py` — функция `reconnect_with_backoff(collector, delays=[0.1, 1, 5, 30])`

**Как запустить:**
```bash
# Пересобрать collector
docker-compose up -d --build collector

# Логи (Ctrl+C чтобы выйти)
docker-compose logs -f collector | grep -E "connected|reconnect|error"
```

**Как проверить:**
```bash
# Health — должно быть 7+ WS соединений
curl -s http://localhost:8001/health | python3 -m json.tool

# Проверка потока данных из разных бирж в Redis
sleep 15
docker-compose exec redis redis-cli XREVRANGE prices + - COUNT 10
```
**Ожидаемый ответ:**
```json
// health
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
    "redis_connected": true,
    "messages_per_minute": 1200
}
```

**Критерий завершения:**
- [ ] Health показывает 7 WS соединений, все статусы `connected`
- [ ] Redis Stream получает тики от всех 7 бирж (проверить через `XREVRANGE`)
- [ ] При остановке одной биржи (имитация) — reconnect через backoff
- [ ] Логи не содержат необработанных exceptions

---

## Фаза 5: TimescaleDB запись цен + Redis Streams

**Команда junior'а:** "Приступай к фазе 5"

**Что будет сделано:**
- Batch INSERT тиков из Redis Stream `prices` в TimescaleDB hypertable `prices`
- Создание consumer group `writer-cg` для чтения из stream
- Batch размер: 100 тиков или 1 секунда (что раньше)
- Создание hypertable `prices` с chunk_time_interval = 1 hour
- Индексы: `(exchange, symbol, time DESC)` и `(symbol, time DESC)`
- Compression policy: сжимать чанки старше 7 дней
- Retention policy: удалять данные старше 30 дней

**Файлы, которые создаются/изменяются:**
- `collector/db_writer.py` — класс `BatchWriter`, методы `start_consuming()`, `flush_batch()`
- `collector/main.py` — обновлён: запускает db_writer как background task
- `scripts/init-db.sql` — обновлён: добавлена hypertable `prices` с индексами, compression, retention
- `shared/db.py` — функция `get_db_pool()` — asyncpg connection pool

**Как запустить:**
```bash
# Пересобрать collector
docker-compose up -d --build collector

# Проверка логов
docker-compose logs -f collector | grep -E "batch|insert|db"
```

**Как проверить:**
```bash
# Дать поработать 30 секунд
sleep 30

# Проверка записей в БД
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "
SELECT exchange, symbol, COUNT(*) as ticks, MAX(time) as last_tick
FROM prices
GROUP BY exchange, symbol
ORDER BY ticks DESC
LIMIT 10;
"

# Проверка hypertable
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "
SELECT hypertable_name, chunk_count FROM timescaledb_information.hypertables WHERE hypertable_name = 'prices';
"
```
**Ожидаемый ответ:**
```
 exchange |  symbol   | ticks |          last_tick
----------+-----------+-------+---------------------------
 binance  | BTC/USDT  |   450 | 2025-07-03 12:05:32+00
 binance  | ETH/USDT  |   445 | 2025-07-03 12:05:31+00
 bybit    | BTC/USDT  |   420 | 2025-07-03 12:05:30+00
 bybit    | ETH/USDT  |   418 | 2025-07-03 12:05:29+00
 kucoin   | BTC/USDT  |   380 | 2025-07-03 12:05:28+00

 hypertable_name | chunk_count
-----------------+-------------
 prices          |           1
```

**Критерий завершения:**
- [ ] В таблице `prices` есть записи от всех 7 бирж
- [ ] Каждая пара (BTC/USDT, ETH/USDT) представлена на каждой бирже
- [ ] Hypertable создан, chunk_count >= 1
- [ ] Consumer group `writer-cg` обрабатывает stream без лага

---

## Фаза 6: Scanner микросервис

**Команда junior'а:** "Приступай к фазе 6"

**Что будет сделано:**
- Scanner читает цены из Redis Stream `prices` через consumer group `scanner-cg`
- Расчёт спреда для каждой пары между всеми парами бирж: `spread = (ask_A - bid_B) / bid_B * 100`
- Фильтрация по min_spread (default 0.30%) из настроек БД
- Учёт комиссий: net_spread = gross_spread - buy_fee - sell_fee - withdrawal_fee_usd
- Публикация opportunity в Redis Stream `opportunities`
- Дедупликация: не публиковать ту же opportunity (same symbol + buy_exchange + sell_exchange) в течение 5 секунд
- Сохранение opportunity в TimescaleDB hypertable `opportunities`

**Файлы, которые создаются/изменяются:**
- `scanner/main.py` — FastAPI app + background task scanner
- `scanner/spread_calculator.py` — функция `calculate_spreads(prices)` возвращает список opportunities
- `scanner/dedup.py` — `OpportunityDedup` с Redis SET для отслеживания последних 5 секунд
- `scripts/init-db.sql` — обновлён: добавлена hypertable `opportunities`
- `scanner/models.py` — Pydantic модели `SpreadResult`, `Opportunity`

**Как запустить:**
```bash
# Пересобрать scanner
docker-compose up -d --build scanner

# Логи
docker-compose logs -f scanner | grep -E "spread|opportunity|calculated"
```

**Как проверить:**
```bash
# Health scanner
curl -s http://localhost:8002/health | python3 -m json.tool

# Проверка opportunities в Redis
sleep 20
docker-compose exec redis redis-cli XREVRANGE opportunities + - COUNT 5

# Проверка записей в БД
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "
SELECT symbol, buy_exchange, sell_exchange, gross_spread_pct, net_spread_pct, time
FROM opportunities
ORDER BY time DESC
LIMIT 5;
"
```
**Ожидаемый ответ:**
```json
// health
{
    "status": "healthy",
    "service": "scanner",
    "spreads_calculated_per_minute": 3500,
    "opportunities_found_last_hour": 12
}

// БД
  symbol   | buy_exchange | sell_exchange | gross_spread_pct | net_spread_pct |           time
-----------+--------------+---------------+------------------+----------------+---------------------------
 BTC/USDT  | kucoin       | binance       |           0.1520 |        -0.0480 | 2025-07-03 12:10:15+00
 ETH/USDT  | bybit        | gateio        |           0.2100 |        -0.0900 | 2025-07-03 12:10:12+00
 BTC/USDT  | coinex       | bybit         |           0.3800 |         0.1800 | 2025-07-03 12:10:08+00
```

**Критерий завершения:**
- [ ] Scanner health показывает активную обработку
- [ ] Redis Stream `opportunities` получает записи
- [ ] В БД `opportunities` есть записи с корректными gross/net спредами
- [ ] Net spread корректно меньше gross spread на сумму комиссий
- [ ] Дедупликация работает: повторный тот же спред в течение 5 секунд не создаёт дубль

---

## Фаза 7: Paper Trading Engine (executor)

**Команда junior'а:** "Приступай к фазе 7"

**Что будет сделано:**
- Executor читает opportunities из Redis Stream `opportunities` через consumer group `executor-cg`
- Симуляция исполнения buy на бирже A и sell на бирже B
- Учёт slippage: random 0.1-0.3% от цены
- Учёт всех комиссий (maker + taker + withdrawal) при расчёте P&L
- Max position: не более 10% от виртуального баланса на сделку
- Запись сделки в TimescaleDB hypertable `trades`
- Публикация результата в Redis Stream `trades`
- Обновление виртуального баланса в Redis Hash `balance:{exchange}`
- Kill switch endpoint: `POST /killswitch` — немедленная остановка всех сделок

**Файлы, которые создаются/изменяются:**
- `executor/main.py` — FastAPI app + background task executor + killswitch endpoint
- `executor/paper_trading.py` — класс `PaperTradingEngine`, метод `execute_opportunity(opp)`
- `executor/balance.py` — функции `get_balance(exchange)`, `update_balance(exchange, asset, delta)`
- `executor/pnl.py` — функция `calculate_pnl(buy_price, sell_price, amount, fees, slippage)`
- `scripts/init-db.sql` — обновлён: добавлена hypertable `trades` + таблица `balance`
- `shared/models.py` — добавлена модель `Trade`

**Как запустить:**
```bash
# Пересобрать executor
docker-compose up -d --build executor

# Инициализация виртуального баланса
docker-compose exec redis redis-cli HSET balance:binance USDT 10000 BTC 0
docker-compose exec redis redis-cli HSET balance:bybit USDT 10000 BTC 0
docker-compose exec redis redis-cli HSET balance:kucoin USDT 10000 BTC 0
docker-compose exec redis redis-cli HSET balance:bitget USDT 10000 BTC 0

# Логи
docker-compose logs -f executor | grep -E "trade|pnl|balance|killswitch"
```

**Как проверить:**
```bash
# Health executor
curl -s http://localhost:8003/health | python3 -m json.tool

# Проверка баланса
docker-compose exec redis redis-cli HGETALL balance:binance

# Проверка trades в Redis
docker-compose exec redis redis-cli XREVRANGE trades + - COUNT 3

# Проверка trades в БД
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "
SELECT id, symbol, buy_exchange, sell_exchange, amount, gross_pnl, net_pnl, status, time
FROM trades
ORDER BY time DESC
LIMIT 3;
"

# Тест killswitch
curl -s -X POST http://localhost:8003/killswitch -H "Content-Type: application/json" -d '{"reason":"test"}'
```
**Ожидаемый ответ:**
```json
// health
{
    "status": "healthy",
    "service": "executor",
    "trades_today": 5,
    "total_pnl_today": -12.45,
    "kill_switch_active": false
}

// balance
1) "USDT"
2) "9876.54"
3) "BTC"
4) "0.00183"

// killswitch
{"status":"activated","reason":"test","timestamp":"2025-07-03T12:15:00Z"}
```

**Критерий завершения:**
- [ ] Executor создаёт paper trades при получении opportunities
- [ ] Каждый trade записан в БД с корректными P&L (gross и net)
- [ ] Виртуальный баланс обновляется после каждой сделки
- [ ] Killswitch endpoint останавливает создание новых сделок
- [ ] Max position ≤ 10% от баланса проверяется перед каждой сделкой

---

## Фаза 8: Telegram Notifier

**Команда junior'а:** "Приступай к фазе 8"

**Что будет сделано:**
- Notifier читает opportunities и trades из Redis Streams через consumer group `notifier-cg`
- Отправка Telegram сообщений при обнаружении спреда > notification_spread_threshold (default 0.50%)
- Отправка Telegram сообщений при завершении paper trade
- Rate limiting: max 20 msg/sec (очередь в Redis List `telegram_queue`)
- Использование aiogram 3.x для Telegram Bot API
- Команды бота: `/start`, `/status`, `/balance`, `/trades`, `/killswitch`
- Форматирование сообщений с эмодзи и цветовой индикацией P&L

**Файлы, которые создаются/изменяются:**
- `notifier/main.py` — FastAPI app + aiogram bot + background consumer
- `notifier/bot.py` — router с командами `/start`, `/status`, `/balance`, `/trades`, `/killswitch`
- `notifier/formatter.py` — функции форматирования сообщений спреда и сделки
- `notifier/queue.py` — `TelegramQueue` с rate limiting через Redis List
- `.env` — добавлен `TELEGRAM_BOT_TOKEN` (получить через @BotFather)

**Как запустить:**
```bash
# Добавить TELEGRAM_BOT_TOKEN в .env
echo "TELEGRAM_BOT_TOKEN=your_token_here" >> .env

# Пересобрать notifier
docker-compose up -d --build notifier

# Логи
docker-compose logs -f notifier | grep -E "telegram|message|bot"
```

**Как проверить:**
```bash
# Health notifier
curl -s http://localhost:8004/health | python3 -m json.tool

# Отправить тестовое сообщение через API
curl -s -X POST http://localhost:8004/notify \
  -H "Content-Type: application/json" \
  -d '{
    "type": "test",
    "message": "Hello from Arbitrage Bot!"
  }'

# Проверка статуса очереди
docker-compose exec redis redis-cli LLEN telegram_queue
```
**Ожидаемый ответ:**
```json
// health
{
    "status": "healthy",
    "service": "notifier",
    "telegram_connected": true,
    "bot_username": "YourArbitrageBot",
    "messages_sent_today": 8,
    "queue_length": 0
}

// test notify
{"status":"queued","message_id":"test_123"}
```

**Критерий завершения:**
- [ ] Notifier health показывает `telegram_connected: true`
- [ ] Команда `/start` в Telegram боте отвечает приветственным сообщением
- [ ] Команда `/status` показывает статус всех сервисов
- [ ] При появлении opportunity со спредом > 0.50% — приходит Telegram уведомление
- [ ] При завершении trade — приходит сообщение с P&L
- [ ] Очередь сообщений не растёт (rate limiting работает)

---

## Фаза 9: API Gateway (REST + WebSocket)

**Команда junior'а:** "Приступай к фазе 9"

**Что будет сделано:**
- REST API с префиксом `/api/v1/` на FastAPI
- JWT аутентификация (HS256, expiry 24h)
- Endpoints: `GET /api/v1/prices`, `GET /api/v1/opportunities`, `GET /api/v1/trades`, `GET /api/v1/balance`, `GET /api/v1/exchanges`
- WebSocket endpoint `/ws` для real-time push данных (цены, спреды, сделки)
- Чтение исторических данных из TimescaleDB
- CORS настройки для frontend origin `http://localhost:5173`
- Rate limiting: 100 req/min REST, 10 msg/sec WS per client
- Prometheus метрики на `/metrics`

**Файлы, которые создаются/изменяются:**
- `api-gateway/main.py` — FastAPI app с routers, middleware, auth
- `api-gateway/routers/prices.py` — `GET /api/v1/prices` с фильтрами exchange, symbol
- `api-gateway/routers/opportunities.py` — `GET /api/v1/opportunities`
- `api-gateway/routers/trades.py` — `GET /api/v1/trades` с пагинацией
- `api-gateway/routers/balance.py` — `GET /api/v1/balance`
- `api-gateway/routers/exchanges.py` — `GET /api/v1/exchanges`, `GET /api/v1/settings`
- `api-gateway/websocket.py` — `WebSocketEndpoint`, подписка на channels (prices, opportunities, trades)
- `api-gateway/auth.py` — JWT encode/decode, зависимость `get_current_user`
- `api-gateway/rate_limiter.py` — simple in-memory rate limiter

**Как запустить:**
```bash
# Пересобрать api-gateway
docker-compose up -d --build api-gateway

# Логи
docker-compose logs -f api-gateway
```

**Как проверить:**
```bash
# Health
curl -s http://localhost:8000/health | python3 -m json.tool

# Получить JWT токен (тестовый пользователь)
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}' | python3 -m json.tool

# REST: получить цены (с токеном)
curl -s http://localhost:8000/api/v1/prices?symbol=BTC/USDT&limit=5 \
  -H "Authorization: Bearer YOUR_TOKEN" | python3 -m json.tool

# REST: получить спреды
curl -s http://localhost:8000/api/v1/opportunities?limit=5 \
  -H "Authorization: Bearer YOUR_TOKEN" | python3 -m json.tool

# REST: получить сделки
curl -s http://localhost:8000/api/v1/trades?limit=5 \
  -H "Authorization: Bearer YOUR_TOKEN" | python3 -m json.tool

# Swagger UI
curl -s http://localhost:8000/docs > /dev/null && echo "Swagger UI available"
```
**Ожидаемый ответ:**
```json
// health
{
    "status": "healthy",
    "service": "api-gateway",
    "db_connected": true,
    "redis_connected": true,
    "ws_clients_active": 0
}

// login
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400
}

// prices
{
    "items": [
        {"exchange": "binance", "symbol": "BTC/USDT", "bid": 67432.15, "ask": 67433.80, "time": "2025-07-03T12:00:00Z"},
        {"exchange": "bybit", "symbol": "BTC/USDT", "bid": 67430.50, "ask": 67435.20, "time": "2025-07-03T12:00:00Z"}
    ],
    "total": 2
}
```

**Критерий завершения:**
- [ ] Swagger UI доступен на `http://localhost:8000/docs`
- [ ] Логин возвращает JWT токен
- [ ] `GET /api/v1/prices` возвращает цены из TimescaleDB
- [ ] `GET /api/v1/opportunities` возвращает спреды
- [ ] `GET /api/v1/trades` возвращает paper trades с пагинацией
- [ ] WebSocket `/ws` принимает подключения (проверить через `wscat` или browser)
- [ ] CORS настроен для `localhost:5173`

---

## Фаза 10: Frontend скелет + Login

**Команда junior'а:** "Приступай к фазе 10"

**Что будет сделано:**
- React 19 + Vite + TypeScript проект в папке `frontend/`
- Tailwind CSS + shadcn/ui интеграция
- Zustand store для auth состояния
- Router: `/login`, `/dashboard`, `/opportunities`, `/trades`, `/analytics`, `/exchanges`, `/settings`
- Login страница с формой email/password, валидацией, JWT storage в localStorage
- Protected routes: редирект на `/login` если нет токена
- Layout: Navbar + Sidebar + Content Area (по UI/UX спецификации)
- Тема: Dark по умолчанию (TradingView-стиль)

**Файлы, которые создаются/изменяются:**
- `frontend/package.json` — зависимости: react, react-dom, react-router-dom, zustand, tailwindcss, shadcn/ui
- `frontend/src/main.tsx` — entry point с Router
- `frontend/src/App.tsx` — корневой компонент с layout
- `frontend/src/pages/Login.tsx` — страница логина с формой
- `frontend/src/pages/Dashboard.tsx` — заглушка страницы дашборда
- `frontend/src/components/Navbar.tsx` — верхняя панель
- `frontend/src/components/Sidebar.tsx` — боковое меню
- `frontend/src/components/Layout.tsx` — обёртка с navbar + sidebar
- `frontend/src/store/authStore.ts` — Zustand store: token, user, login(), logout()
- `frontend/src/lib/api.ts` — axios instance с JWT interceptor
- `frontend/vite.config.ts` — Vite конфигурация
- `frontend/tailwind.config.js` — Tailwind с кастомными цветами

**Как запустить:**
```bash
# Установка зависимостей
cd frontend && npm install

# Запуск dev-сервер
npm run dev

# Или через Docker
docker-compose up -d frontend
```

**Как проверить:**
```bash
# Проверка, что frontend доступен
curl -s http://localhost:5173 | head -20

# Проверка API endpoint для логина (через frontend proxy или напрямую)
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```
**Ожидаемый ответ:**
```html
<!-- frontend HTML (часть) -->
<!doctype html>
<html lang="en">
  <head>
    <title>Crypto Arbitrage Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

**Критерий завершения:**
- [ ] Frontend доступен на `http://localhost:5173`
- [ ] Страница `/login` отображает форму с email и password
- [ ] Успешный логин сохраняет JWT в localStorage и редиректит на `/dashboard`
- [ ] Sidebar отображает 6 пунктов меню (Dashboard, Opportunities, Trades, Analytics, Exchanges, Settings)
- [ ] Navbar показывает статус системы (online/offline индикатор)
- [ ] Тёмная тема применена (фон `#0a0a14`)

---

## Фаза 11: Dashboard + Opportunities (WS real-time)

**Команда junior'а:** "Приступай к фазе 11"

**Что будет сделано:**
- Dashboard страница с KPI Cards (Total P&L, Active Opportunities, Today's Trades, Best Spread)
- Exchange Status Panel: 7 mini-cards со статусом WS, latency, баланс
- Mini P&L Chart (Recharts AreaChart, последние 24 часа)
- Top 5 Opportunities таблица с WebSocket real-time обновлениями
- Last 5 Trades таблица
- Opportunities страница: полная таблица со всеми фильтрами (exchange, pair, min spread)
- WebSocket клиент: подключение к `ws://localhost:8000/ws`, подписка на channels
- Автоматический reconnect WS с exponential backoff

**Файлы, которые создаются/изменяются:**
- `frontend/src/pages/Dashboard.tsx` — полная реализация с KPI, Exchange Status, Charts, Tables
- `frontend/src/pages/Opportunities.tsx` — таблица opportunities с фильтрами
- `frontend/src/components/KPICard.tsx` — карточка KPI с анимацией count-up
- `frontend/src/components/ExchangeStatusCard.tsx` — mini-card биржи
- `frontend/src/components/PriceTable.tsx` — таблица цен с WS обновлениями
- `frontend/src/components/OpportunitiesTable.tsx` — таблица спредов с цветовой индикацией
- `frontend/src/components/PnLChart.tsx` — Recharts AreaChart
- `frontend/src/hooks/useWebSocket.ts` — хук для WS подключения с reconnect
- `frontend/src/store/spreadStore.ts` — Zustand store для spreads/opportunities

**Как запустить:**
```bash
# Пересобрать frontend и api-gateway (для WS поддержки)
docker-compose up -d --build frontend api-gateway
```

**Как проверить:**
```bash
# Проверка API данных для dashboard
curl -s http://localhost:8000/api/v1/opportunities?limit=5 \
  -H "Authorization: Bearer YOUR_TOKEN" | python3 -m json.tool

# Проверка WebSocket (через wscat или curl-альтернативу)
# В браузере: открыть DevTools → Network → WS → подключение к ws://localhost:8000/ws

# Проверка prices endpoint
curl -s "http://localhost:8000/api/v1/prices?symbol=BTC/USDT&limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN" | python3 -m json.tool
```
**Ожидаемый ответ:**
```json
// opportunities
{
    "items": [
        {
            "id": "opp_1720000000_binance_bybit_btcusdt",
            "symbol": "BTC/USDT",
            "buy_exchange": "binance",
            "sell_exchange": "bybit",
            "buy_price": 67432.15,
            "sell_price": 67450.30,
            "gross_spread_pct": 0.027,
            "net_spread_pct": -0.073,
            "detected_at": "2025-07-03T12:00:00Z"
        }
    ],
    "total": 1
}
```

**Критерий завершения:**
- [ ] Dashboard отображает 4 KPI карточки с актуальными данными
- [ ] 7 Exchange Status cards показывают статус WS (зелёная/красная точка)
- [ ] P&L Chart рендерит график за 24 часа
- [ ] Top Opportunities таблица обновляется в реальном времени (WS)
- [ ] Opportunities страница: таблица с фильтрами по бирже и паре
- [ ] WebSocket reconnect работает (перезапустить api-gateway, проверить что frontend переподключился)

---

## Фаза 12: Trades + Analytics

**Команда junior'а:** "Приступай к фазе 12"

**Что будет сделано:**
- Trades страница: таблица всех paper trades с фильтрами (date range, exchange, pair, status, P&L)
- Pagination: выбор размера страницы (10, 25, 50, 100)
- Detail drawer: подробная информация о сделке при клике
- Export CSV: кнопка скачивания trades в CSV
- Analytics страница: статистические карточки (6 KPI), P&L Chart (line), Cumulative P&L Chart
- Date Range Picker для аналитики
- Recharts графики: AreaChart для P&L, BarChart для trades per day

**Файлы, которые создаются/изменяются:**
- `frontend/src/pages/Trades.tsx` — страница с таблицей trades, фильтрами, пагинацией
- `frontend/src/pages/Analytics.tsx` — страница аналитики с графиками
- `frontend/src/components/TradeTable.tsx` — таблица trades со статусными badge
- `frontend/src/components/TradeDetailDrawer.tsx` — drawer с деталями сделки
- `frontend/src/components/PnLChart.tsx` — обновлён: поддержка разных диапазонов дат
- `frontend/src/components/CumulativePnLChart.tsx` — накопительный P&L
- `frontend/src/components/TradesPerDayChart.tsx` — BarChart количества сделок
- `frontend/src/components/DateRangePicker.tsx` — выбор диапазона дат
- `frontend/src/components/ExportCSV.tsx` — кнопка экспорта в CSV
- `frontend/src/store/tradeStore.ts` — Zustand store для trades

**Как запустить:**
```bash
# Пересобрать frontend
docker-compose up -d --build frontend
```

**Как проверить:**
```bash
# Проверка trades API с пагинацией
curl -s "http://localhost:8000/api/v1/trades?page=1&page_size=10&status=completed" \
  -H "Authorization: Bearer YOUR_TOKEN" | python3 -m json.tool

# Проверка аналитики
curl -s "http://localhost:8000/api/v1/analytics/pnl?days=7" \
  -H "Authorization: Bearer YOUR_TOKEN" | python3 -m json.tool

# Проверка export
curl -s "http://localhost:8000/api/v1/trades/export?format=csv" \
  -H "Authorization: Bearer YOUR_TOKEN" -o /tmp/trades_test.csv && head -3 /tmp/trades_test.csv
```
**Ожидаемый ответ:**
```json
// trades
{
    "items": [
        {
            "id": "trade_1720000001",
            "symbol": "BTC/USDT",
            "buy_exchange": "binance",
            "sell_exchange": "bybit",
            "amount": 0.1,
            "gross_pnl": 1.82,
            "net_pnl": -25.16,
            "status": "completed",
            "executed_at": "2025-07-03T12:00:01Z"
        }
    ],
    "total": 156,
    "page": 1,
    "page_size": 10,
    "total_pages": 16
}

// analytics/pnl
{
    "period": "7d",
    "total_trades": 45,
    "total_gross_pnl": 234.50,
    "total_net_pnl": -45.20,
    "win_rate": 48.9,
    "avg_trade_duration_ms": 234,
    "daily": [
        {"date": "2025-07-01", "trades": 8, "net_pnl": 12.50},
        {"date": "2025-07-02", "trades": 12, "net_pnl": -32.40},
        {"date": "2025-07-03", "trades": 25, "net_pnl": -25.30}
    ]
}
```

**Критерий завершения:**
- [ ] Trades страница отображает таблицу с пагинацией
- [ ] Фильтры по статусу, паре, бирже работают
- [ ] Detail drawer открывается при клике на строку
- [ ] Export CSV скачивает файл с корректными данными
- [ ] Analytics страница показывает 6 статистических карточек
- [ ] P&L Chart и Cumulative P&L Chart рендерятся корректно
- [ ] Date Range Picker фильтрует данные

---

## Фаза 13: Exchanges + Settings

**Команда junior'а:** "Приступай к фазе 13"

**Что будет сделано:**
- Exchanges страница: таблица 7 бирж со статусом, комиссиями, балансом, настройками
- Toggle вкл/выкл биржи (is_active)
- Отображение комиссий (maker/taker) и withdrawal fees
- Settings страница: форма настройки min_spread, max_position, slippage_tolerance, execution_timeout
- Kill switch кнопка (danger variant, с подтверждением в модальном окне)
- Тема: Dark/Light/System toggle
- Настройки сохраняются в TimescaleDB таблицу `settings`
- Toast уведомления при сохранении настроек (Sonner)

**Файлы, которые создаются/изменяются:**
- `frontend/src/pages/Exchanges.tsx` — страница с таблицей бирж
- `frontend/src/pages/Settings.tsx` — страница настроек с формой
- `frontend/src/components/ExchangeTable.tsx` — таблица бирж со switch toggle
- `frontend/src/components/SettingsForm.tsx` — форма настроек (min_spread, max_position и т.д.)
- `frontend/src/components/KillSwitchButton.tsx` — кнопка killswitch с confirmation modal
- `frontend/src/components/ThemeToggle.tsx` — переключатель темы
- `frontend/src/store/settingsStore.ts` — Zustand store для настроек
- `api-gateway/routers/settings.py` — `GET/PUT /api/v1/settings`
- `api-gateway/routers/killswitch.py` — `POST /api/v1/killswitch`

**Как запустить:**
```bash
# Пересобрать frontend и api-gateway
docker-compose up -d --build frontend api-gateway
```

**Как проверить:**
```bash
# Получить текущие настройки
curl -s http://localhost:8000/api/v1/settings \
  -H "Authorization: Bearer YOUR_TOKEN" | python3 -m json.tool

# Обновить настройки
curl -s -X PUT http://localhost:8000/api/v1/settings \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"min_spread_pct": 0.50, "max_position_pct": 15}' | python3 -m json.tool

# Активировать killswitch
curl -s -X POST http://localhost:8000/api/v1/killswitch \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason":"manual_trigger"}' | python3 -m json.tool
```
**Ожидаемый ответ:**
```json
// settings GET
{
    "min_spread_pct": 0.30,
    "max_position_pct": 10.00,
    "slippage_tolerance_pct": 0.20,
    "execution_timeout_sec": 2,
    "kill_switch": false,
    "notification_spread_threshold": 0.50,
    "daily_loss_limit_pct": 5.00
}

// settings PUT
{
    "status": "updated",
    "settings": {
        "min_spread_pct": 0.50,
        "max_position_pct": 15.00
    }
}

// killswitch
{
    "status": "activated",
    "reason": "manual_trigger",
    "timestamp": "2025-07-03T14:00:00Z",
    "executor_stopped": true
}
```

**Критерий завершения:**
- [ ] Exchanges страница показывает 7 бирж с корректными комиссиями
- [ ] Toggle вкл/выкл биржи меняет статус в БД
- [ ] Settings страница отображает текущие настройки
- [ ] Изменение настроек сохраняется в БД
- [ ] Kill switch кнопка с подтверждением останавливает executor
- [ ] Переключение темы Dark/Light работает
- [ ] Toast уведомления появляются при сохранении

---

## Фаза 14: Интеграция frontend + backend

**Команда junior'а:** "Приступай к фазе 14"

**Что будет сделано:**
- Полная сквозная интеграция: frontend React → API Gateway → микросервисы
- WebSocket real-time: данные из collector → Redis → API Gateway → React dashboard
- Auth flow: login → JWT → все protected requests → logout
- Error handling: 401 redirect to login, 500 toast error, network error indicator
- Loading states: skeleton screens при загрузке данных
- Responsive design: tablet (sidebar collapsed), mobile (hamburger menu)
- E2E тест: полный цикл от WS тика до отображения на dashboard

**Файлы, которые создаются/изменяются:**
- `frontend/src/lib/api.ts` — обновлён: обработка 401, 500, network errors
- `frontend/src/hooks/useWebSocket.ts` — обновлён: heartbeat ping/pong, reconnect
- `frontend/src/components/LoadingSkeleton.tsx` — skeleton компоненты
- `frontend/src/components/ErrorBoundary.tsx` — error boundary для страниц
- `frontend/src/components/NetworkStatus.tsx` — индикатор статуса сети
- `frontend/src/App.tsx` — обновлён: error boundary, auth guard
- `api-gateway/main.py` — обновлён: CORS, error handling middleware
- `docker-compose.yml` — обновлён: frontend зависит от api-gateway

**Как запустить:**
```bash
# Полный перезапуск всей системы
docker-compose down
docker-compose up -d --build

# Ждём 30 секунд для инициализации
sleep 30
```

**Как проверить:**
```bash
# Проверка всех health endpoints
echo "=== API Gateway ===" && curl -s http://localhost:8000/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"status={d['status']}, ws_clients={d.get('ws_clients_active',0)}\")"
echo "=== Collector ===" && curl -s http://localhost:8001/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"status={d['status']}, ws={d.get('ws_connections',0)}\")"
echo "=== Scanner ===" && curl -s http://localhost:8002/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"status={d['status']}\")"
echo "=== Executor ===" && curl -s http://localhost:8003/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"status={d['status']}, trades={d.get('trades_today',0)}\")"
echo "=== Notifier ===" && curl -s http://localhost:8004/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"status={d['status']}, telegram={d.get('telegram_connected',false)}\")"

# Frontend доступен
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173
```
**Ожидаемый ответ:**
```
=== API Gateway ===
status=healthy, ws_clients=1
=== Collector ===
status=healthy, ws=7
=== Scanner ===
status=healthy
=== Executor ===
status=healthy, trades=3
=== Notifier ===
status=healthy, telegram=true
200
```

**Критерий завершения:**
- [ ] Все 5 сервисов healthy
- [ ] Frontend на `localhost:5173` загружается без ошибок в консоли
- [ ] Login → Dashboard flow работает end-to-end
- [ ] WebSocket данные обновляются на dashboard в реальном времени
- [ ] Opportunities появляются в таблице при появлении спреда
- [ ] Trades отображаются после executor сделок
- [ ] Нет CORS ошибок в браузере
- [ ] При 401 ответе — редирект на login
- [ ] Mobile layout: sidebar скрыт, гамбургер-меню работает

---

## Фаза 15: Тесты + Документация + Деплой

**Команда junior'а:** "Приступай к фазе 15"

**Что будет сделано:**
- Unit-тесты для spread_calculator (scanner): проверка формул спреда
- Unit-тесты для pnl calculator (executor): проверка расчёта P&L
- Integration тест: collector → Redis → scanner → opportunity
- API тесты: все REST endpoints с JWT аутентификацией
- Нагрузочный тест: `prices` stream с 1000 msg/sec
- README.md: инструкция по запуску (docker-compose up -d)
- API документация: Swagger UI автоматически генерируется FastAPI
- `.env.example` с описанием всех переменных
- Docker Compose production overrides: resource limits, restart policies, logging
- Grafana dashboard JSON для импорта

**Файлы, которые создаются/изменяются:**
- `tests/test_spread_calculator.py` — тесты формул scanner
- `tests/test_pnl_calculator.py` — тесты формул executor
- `tests/test_integration.py` — сквозной тест потока данных
- `tests/test_api.py` — тесты REST API
- `README.md` — полная инструкция по установке и запуску
- `docker-compose.prod.yml` — production overrides (limits, restart, logging)
- `monitoring/grafana-dashboard.json` — dashboard для импорта в Grafana
- `.env.example` — обновлён: все переменные с описанием

**Как запустить:**
```bash
# Запуск тестов
docker-compose -f docker-compose.yml -f docker-compose.test.yml up --build tests

# Или локально (если установлен pytest)
cd tests && pytest -v

# Запуск с production конфигурацией
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Проверка логов всех сервисов
docker-compose logs --tail=50
```

**Как проверить:**
```bash
# Запуск тестов
pytest tests/ -v --tb=short

# Проверка всех endpoints
curl -s http://localhost:8000/health
curl -s http://localhost:8000/metrics | head -20
curl -s http://localhost:8000/docs > /dev/null && echo "Swagger OK"

# Проверка Grafana
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000

# Prometheus
curl -s -o /dev/null -w "%{http_code}" http://localhost:9090
```
**Ожидаемый ответ:**
```
tests/test_spread_calculator.py::test_spread_calculation PASSED
tests/test_spread_calculator.py::test_net_spread_with_fees PASSED
tests/test_pnl_calculator.py::test_pnl_positive_trade PASSED
tests/test_pnl_calculator.py::test_pnl_with_slippage PASSED
tests/test_integration.py::test_collector_to_scanner_flow PASSED
tests/test_api.py::test_login PASSED
tests/test_api.py::test_get_prices PASSED
tests/test_api.py::test_get_trades PASSED
========================= 8 passed in 12.34s =========================

200  # Grafana
200  # Prometheus
Swagger OK
```

**Критерий завершения:**
- [ ] Все unit-тесты проходят (spread calculator, PnL calculator)
- [ ] Integration тест проходит (collector → Redis → scanner)
- [ ] API тесты проходят (login, prices, trades)
- [ ] Swagger UI генерирует документацию без ошибок
- [ ] Grafana доступна на `localhost:3000`
- [ ] Prometheus доступен на `localhost:9090`
- [ ] README.md содержит инструкцию `docker-compose up -d`
- [ ] `.env.example` описывает все переменные
- [ ] Production compose имеет resource limits и restart policies

---

## Оценка времени

### Сколько фаз в день

| Режим | Фаз в день | Примечание |
|-------|-----------|------------|
| Спокойный | 1 фаза/день | Junior, много новых технологий |
| Оптимальный | 1-2 фазы/день | Стабильная работа, debug |
| Интенсивный | 2 фазы/день | При опыте с Docker/FastAPI |

### Рекомендуемый график

| Неделя | Фазы | Что делаем |
|--------|------|-----------|
| **Неделя 1** | 0, 1, 2, 3 | Инфраструктура, Docker, БД, конфиг, Binance WS |
| **Неделя 2** | 4, 5, 6 | Все 7 бирж, запись в БД, Scanner |
| **Неделя 3** | 7, 8, 9 | Executor paper trading, Telegram, API Gateway |
| **Неделя 4** | 10, 11, 12 | Frontend скелет, Dashboard, Trades, Analytics |
| **Неделя 5** | 13, 14, 15 | Settings, интеграция, тесты, документация, деплой |

### Итого

- **В спокойном режиме:** 16 дней (3-4 недели)
- **В оптимальном режиме:** 10-12 дней (2-3 недели)
- **В интенсивном режиме:** 8 дней (1.5-2 недели)

### Самые сложные фазы (требуют больше времени)

| Фаза | Сложность | Почему сложно |
|------|-----------|---------------|
| **Фаза 4** | ⭐⭐⭐⭐⭐ | 7 WebSocket соединений, reconnect, rate limiting, разные API бирж |
| **Фаза 11** | ⭐⭐⭐⭐☆ | WebSocket real-time на frontend, reconnect, sync состояния |
| **Фаза 14** | ⭐⭐⭐⭐☆ | Полная интеграция frontend+backend, CORS, auth, error handling |
| **Фазa 7** | ⭐⭐⭐☆☆ | Paper trading логика, P&L расчёты, balance management |

---

## Troubleshooting

### 1. Redis не подключается

**Симптомы:** `ConnectionRefusedError: [Errno 111] Connection refused`, сервис падает при старте.

**Решение:**
```bash
# Проверить, что Redis запущен
docker-compose ps redis

# Проверить сеть
docker network inspect arbitrage-net

# Проверить доступность из контейнера
docker-compose exec collector python -c "import redis; r = redis.Redis(host='redis', port=6379); print(r.ping())"

# Перезапустить Redis
docker-compose restart redis

# Если всё равно не работает — проверить logs
docker-compose logs redis
```

**Причины:**
- Redis ещё не успел запуститься (добавить `depends_on` с `condition: service_healthy`)
- Неправильное имя хоста (должно быть `redis`, не `localhost`)
- Порт занят другим процессом: `lsof -i :6379`

---

### 2. TimescaleDB не создаёт hypertables

**Симптомы:** Таблицы созданы, но `timescaledb_information.hypertables` пустая. INSERT медленный.

**Решение:**
```bash
# Проверить, что расширение timescaledb установлено
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "SELECT * FROM pg_extension WHERE extname = 'timescaledb';"

# Если нет — создать вручную
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

# Создать hypertable вручную
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "SELECT create_hypertable('prices', 'time', if_not_exists => TRUE);"

# Проверить
docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "SELECT hypertable_name, chunk_count FROM timescaledb_information.hypertables;"
```

**Причины:**
- Инициализация SQL не выполнилась (volume не пустой — данные сохранились)
- Образ PostgreSQL не TimescaleDB (должен быть `timescale/timescaledb:latest-pg16`)
- Скрипт `init-db.sql` не смонтирован в `/docker-entrypoint-initdb.d/`

---

### 3. WebSocket disconnect

**Симптомы:** Логи collector: `ConnectionClosed`, `WS disconnected`, данные не поступают.

**Решение:**
```bash
# Проверить логи collector
docker-compose logs -f collector | grep -i "ws\|websocket\|reconnect\|error"

# Проверить доступность биржи из контейнера
docker-compose exec collector python -c "
import ccxt
exchange = ccxt.binance({'enableRateLimit': True})
ticker = exchange.fetch_ticker('BTC/USDT')
print('OK:', ticker['bid'])
"

# Перезапустить collector
docker-compose restart collector

# Проверить rate limits (если 429 ошибки)
docker-compose logs collector | grep -i "rate\|limit\|429"
```

**Причины:**
- Rate limit превышен (уменьшить частоту или добавить прокси)
- Биржа временно недоступна (нормально, reconnect должен сработать)
- IP заблокирован (использовать другой IP или VPN)
- CCXT Pro не поддерживает WS для данной биржи — fallback на REST

---

### 4. CORS ошибки frontend

**Симптомы:** В браузере: `Access to fetch at 'http://localhost:8000/...' from origin 'http://localhost:5173' has been blocked by CORS policy`.

**Решение:**
```bash
# Проверить CORS настройки в api-gateway
curl -s -D - -o /dev/null -X OPTIONS http://localhost:8000/api/v1/prices \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET"

# Должен быть заголовок: Access-Control-Allow-Origin: http://localhost:5173

# В api-gateway/main.py проверить:
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
```

**Причины:**
- `allow_origins` не содержит `http://localhost:5173`
- Preflight OPTIONS request не обрабатывается
- `allow_credentials=True` но `allow_origins=["*"]` — несовместимая комбинация

---

### 5. Telegram webhook не работает

**Симптомы:** Бот не отвечает на команды, `telegram_connected: false` в health.

**Решение:**
```bash
# Проверить токен
docker-compose exec notifier python -c "
import os, asyncio
from aiogram import Bot
bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
me = asyncio.run(bot.get_me())
print(f'Bot: @{me.username}')
"

# Проверить токен через curl
curl -s "https://api.telegram.org/botYOUR_TOKEN/getMe" | python3 -m json.tool

# Если polling используется — проверить, что процесс запущен
docker-compose logs notifier | grep -i "polling\|bot\|error"

# Перезапустить notifier
docker-compose restart notifier
```

**Причины:**
- Неправильный TELEGRAM_BOT_TOKEN (проверить через @BotFather)
- Бот уже запущен в другом месте (Telegram позволяет только 1 polling)
- Network issues из контейнера (проверить `curl https://api.telegram.org`)

---

### 6. Docker container падает с ошибкой

**Симптомы:** `docker-compose ps` показывает `Exit 1`, сервис постоянно перезапускается.

**Решение:**
```bash
# Посмотреть последние 50 строк логов
docker-compose logs --tail=50 SERVICE_NAME

# Примеры:
docker-compose logs --tail=50 collector
docker-compose logs --tail=50 scanner

# Запустить контейнер без перезапуска для отладки
docker-compose run --rm collector python main.py

# Проверить, что healthcheck проходит
docker-compose exec collector curl -f http://localhost:8001/health || echo "Healthcheck FAILED"

# Проверить ресурсы
docker stats --no-stream

# Пересобрать конкретный сервис
docker-compose up -d --build --no-deps collector
```

**Причины:**
- Ошибка в Python коде (SyntaxError, ImportError) — смотреть логи
- Зависимость не установилась (проверить `requirements.txt`)
- Недостаточно памяти (проверить `docker stats`)
- Порт уже занят (проверить `lsof -i :PORT`)
- Не дожидается запуска зависимостей (добавить `depends_on` + retry logic)

---

## Примечания для junior'а

### Как пользоваться docker logs

```bash
# Логи конкретного сервиса
docker-compose logs -f SERVICE_NAME

# Последние 100 строк
docker-compose logs --tail=100 SERVICE_NAME

# Все сервисы
docker-compose logs -f

# С временными метками
docker-compose logs -f --timestamps collector

# Поиск в логах
docker-compose logs collector | grep -i "error\|exception\|failed"
```

### Как перезапускать отдельный сервис

```bash
# Перезапуск без пересборки
docker-compose restart SERVICE_NAME

# Пересборка и перезапуск одного сервиса
docker-compose up -d --build --no-deps SERVICE_NAME

# Остановка сервиса
docker-compose stop SERVICE_NAME

# Запуск остановленного сервиса
docker-compose start SERVICE_NAME

# Полное удаление и пересоздание
docker-compose rm -f SERVICE_NAME && docker-compose up -d --build SERVICE_NAME
```

### Где смотреть ошибки

| Уровень | Команда | Когда использовать |
|---------|---------|-------------------|
| **Логи сервиса** | `docker-compose logs SERVICE` | Всегда первым делом |
| **Python traceback** | В логах сервиса | При Exception в коде |
| **Health endpoint** | `curl http://localhost:PORT/health` | Быстрая проверка статуса |
| **Redis** | `docker-compose exec redis redis-cli INFO` | Проверка memory, connections |
| **БД** | `docker-compose exec timescaledb psql -U arbitrage -d arbitrage_db -c "..."` | SQL запросы, проверка данных |
| **Сеть** | `docker network inspect arbitrage-net` | Проблемы с connectivity |
| **Ресурсы** | `docker stats --no-stream` | OOM, CPU throttling |

### Полезные команды

```bash
# Полный перезапуск всей системы
docker-compose down -v && docker-compose up -d --build

# Зайти в контейнер для отладки
docker-compose exec SERVICE_NAME bash

# Проверить переменные окружения в контейнере
docker-compose exec SERVICE_NAME env | grep -i "redis\|db\|api"

# Очистить все (осторожно — удалит данные!)
docker-compose down -v --rmi all

# Масштабирование collector (если нужно)
docker-compose up -d --scale collector=2
```

### Чек-лист перед каждой фазой

- [ ] Предыдущая фаза завершена (все критерии выполнены)
- [ ] Все сервисы healthy: `docker-compose ps`
- [ ] Проверочный curl из фазы N-1 проходит
- [ ] `.env` файл заполнен необходимыми переменными
- [ ] Логи предыдущей фазы не содержат необработанных ошибок

### Чек-лист после каждой фазы

- [ ] Критерии завершения фазы выполнены (все checkbox'ы)
- [ ] Проверочный curl из фазы проходит с ожидаемым ответом
- [ ] `docker-compose ps` показывает все сервисы Up
- [ ] Логи не содержат критических ошибок
- [ ] Код закоммичен в git
