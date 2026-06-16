# Техническое задание: Крипто-арбитражная SaaS-система

**Версия:** 1.0  
**Дата:** Июль 2025  
**Автор:** Системный архитектор  
**Статус:** Draft для MVP  

**Контекст:** Закрытая SaaS-система крипто-арбитражной торговли. MVP — только межбиржевой (cross-exchange) арбитраж.  
**Целевые биржи (7):** Bybit, Binance, KuCoin, Gate.io, Bitget, CoinEx, BingX  

---

## 1. Цели и задачи

### 1.1. Цель проекта

Создать закрытую многопользовательскую SaaS-платформу для автоматизированного межбиржевого крипто-арбитража, которая:

1. Мониторит цены на 7 криптобиржах в реальном времени через WebSocket
2. Обнаруживает арбитражные возможности (спреды) между биржами
3. Исполняет сделки в режиме paper trading (симуляция) для валидации стратегий
4. Предоставляет пользователям React-дашборд с real-time визуализацией данных
5. Отправляет уведомления о спредах и сделках через Telegram

### 1.2. KPI системы

| Метрика | Целевое значение | Как измеряется |
|---------|-----------------|----------------|
| End-to-end latency (тик на бирже → отображение на фронтенде) | < 100 ms | Метрика Prometheus: `e2e_latency_ms` |
| Время обнаружения спреда | < 50 ms | Метрика: `spread_detection_latency_ms` |
| Paper trading execution | < 200 ms | Метрика: `paper_execution_ms` |
| Uptime WebSocket соединений | > 99.5% | Метрика: `ws_uptime_percent` |
| Пропускная способность API Gateway | 35,000+ req/sec | Load testing k6/wrk |
| Ingestion цен в TimescaleDB | 100,000+ ticks/sec | Batch INSERT benchmark |
| Пропускная способность Redis Streams | 80,000+ msg/sec | Redis `XADD` benchmark |
| Доступность системы (uptime) | 99.9% | Метрика: `service_uptime_percent` |

### 1.3. Scope MVP

**Входит в MVP:**

| # | Функциональность | Описание |
|---|-----------------|----------|
| 1 | Мониторинг 7 бирж через WebSocket | Сбор цен в real-time (best bid/ask) |
| 2 | Обнаружение межбиржевых спредов | Сравнение цен на идентичные пары между биржами |
| 3 | Paper trading (симуляция) | Исполнение виртуальных сделок с отслеживанием P&L |
| 4 | React Dashboard | Real-time визуализация: цены, спреды, история сделок, P&L |
| 5 | Telegram notifications | Алерты на спреды и завершённые сделки |
| 6 | Управление торговыми парами | Включение/выключение пар, настройка порогов |
| 7 | Исторические данные | Хранение цен и сделок в TimescaleDB |

**Приоритетные пары для MVP:**

| Приоритет | Пара | Биржи | Почему |
|-----------|------|-------|--------|
| P1 | BTC/USDT | Binance, Bybit, KuCoin, Bitget | Максимальная ликвидность, частые спреды |
| P1 | ETH/USDT | Binance, Bybit, KuCoin, Bitget | Высокая ликвидность, хорошие спреды |
| P2 | BTC/USDC | Binance, Bybit, KuCoin | Альтернатива USDT |
| P2 | ETH/USDC | Binance, Bybit, KuCoin | Альтернатива USDT |
| P3 | ETH/BTC | Binance, Bybit, KuCoin | Статистический арбитраж (post-MVP) |

### 1.4. Ограничения и допущения

| # | Ограничение / Допущение | Описание |
|---|------------------------|----------|
| 1 | Только spot рынок | Фьючерсный арбитраж — post-MVP |
| 2 | Paper trading вместо реальных сделок | Реальный trading — Phase 2 (отдельный проект) |
| 3 | Максимальный размер позиции | ≤ 10% от виртуального баланса на сделку |
| 4 | Максимальное время исполнения | 2 секунды — авто-отмена по таймауту |
| 5 | Slippage tolerance | 0.1-0.3% для крупных пар (BTC/USDT, ETH/USDT) |
| 6 | Порог спреда (min_spread) | 0.30-0.50% базовый, 0.50-0.70% оптимальный |
| 7 | Спред должен быть > 3× суммарных комиссий | Защита от убыточных сделок |
| 8 | CCXT Pro для WebSocket | Не HFT-класс, overhead ~5-50ms допустим |
| 9 | Размещение сервера | Tokyo/Singapore для минимальной latency к биржам |
| 10 | Моно-репозиторий | Все микросервисы в одном git-репозитории |
| 11 | Docker Compose для оркестрации | Kubernetes — post-MVP при >100 пользователей |
| 12 | Одна валюта учёта | USDT для всех расчётов |

### 1.5. Что НЕ входит в MVP

| # | Функциональность | Причина исключения | Этап добавления |
|---|-----------------|-------------------|----------------|
| 1 | Реальный trading с реальными API ключами | Требует аудита безопасности и юридического обзора | Phase 2 |
| 2 | Треугольный арбитраж | Сложность, требует 3 одновременных ордера | Phase 2 |
| 3 | Статистический арбитраж (mean reversion) | Требует ML-моделей и бэктестинга | Phase 3 |
| 4 | Funding Rate арбитраж | Только фьючерсы, post-MVP | Phase 2 |
| 5 | DEX ↔ CEX арбитраж | Gas fees, smart contract риски | Phase 3 |
| 6 | Billинг и подписки | MVP — закрытый доступ по инвайтам | Phase 2 |
| 7 | Multi-tenancy (полная изоляция пользователей) | MVP — один "тенант" | Phase 2 |
| 8 | Мобильное приложение | React dashboard адаптивен под mobile | Phase 2 |
| 9 | Backtesting движок | Paper trading покрывает валидацию | Phase 2 |
| 10 | Risk management (полный) | Базовый: max position, kill switch | Phase 2 |

---

## 2. Функциональные требования

### 2.1. Модуль Collector (порт 8001)

**Назначение:** Подключение к WebSocket API 7 бирж, сбор цен в real-time, публикация в Redis Streams.

| ID | Требование | Приоритет |
|----|-----------|-----------|
| C-001 | Поддержка 7 бирж: Bybit, Binance, KuCoin, Gate.io, Bitget, CoinEx, BingX | Must |
| C-002 | Использование CCXT Pro для унифицированного WebSocket API | Must |
| C-003 | Сбор best bid/ask для каждой пары с timestamp (микросекунды) | Must |
| C-004 | Публикация цен в Redis Stream `prices` с форматом JSON | Must |
| C-005 | Автоматический reconnect при обрыве соединения (exponential backoff: 100ms → 1s → 5s → 30s) | Must |
| C-006 | Health check endpoint `GET /health` — проверка WS соединений и Redis | Must |
| C-007 | Graceful shutdown — закрытие всех WS соединений, flush данных в Redis | Must |
| C-008 | Метрики Prometheus: `ws_connections_active`, `ws_messages_total`, `ws_reconnect_total`, `redis_publish_latency_ms` | Must |
| C-009 | Rate limiting — соблюдение лимитов каждой биржи через CCXT `enableRateLimit=True` | Must |
| C-010 | Fallback на REST API при недоступности WebSocket > 30 секунд | Should |
| C-011 | TCP tuning: отключение Nagle's algorithm, TLS session resumption | Should |
| C-012 | Sharding — возможность запуска нескольких инстансов collector по парам/биржам | Could |

**Формат данных из Collector:**

```json
{
  "exchange": "binance",
  "symbol": "BTC/USDT",
  "bid": 67432.15,
  "ask": 67433.80,
  "bid_volume": 1.234,
  "ask_volume": 0.987,
  "timestamp": 1720000000000,
  "received_at": 1720000000015,
  "latency_ms": 15
}
```

### 2.2. Модуль Scanner (порт 8002)

**Назначение:** Чтение цен из Redis Streams, расчёт спредов между биржами, публикация арбитражных возможностей.

| ID | Требование | Приоритет |
|----|-----------|-----------|
| S-001 | Чтение цен из Redis Stream `prices` через consumer group `scanner-cg` | Must |
| S-002 | Расчёт спреда для каждой пары между всеми комбинациями бирж: `spread = (ask_A - bid_B) / bid_B * 100` | Must |
| S-003 | Фильтрация по min_spread (configurable, default: 0.30%) | Must |
| S-004 | Учёт комиссий при расчёте net_spread (maker + taker + withdrawal) | Must |
| S-005 | Публикация opportunity в Redis Stream `opportunities` | Must |
| S-006 | Дедупликация: не публиковать повторно ту же opportunity в течение 5 секунд | Must |
| S-007 | Health check endpoint `GET /health` | Must |
| S-008 | Метрики Prometheus: `spreads_scanned_total`, `opportunities_found_total`, `scanner_latency_ms` | Must |
| S-009 | Graceful shutdown — дождаться обработки текущего batch | Must |
| S-010 | Circuit Breaker — остановка сканирования при > 5 ошибок подряд, recovery через 30 сек | Should |
| S-011 | Адаптивный min_spread — корректировка порога на основе исторических данных | Could |

**Таблица комиссий для расчёта net_spread (конфигурация):**

| Биржа | Spot Maker | Spot Taker | Withdrawal BTC | Withdrawal USDT (TRC20) |
|-------|-----------|-----------|----------------|------------------------|
| Bybit | 0.10% | 0.10% | 0.000085 BTC | 1 USDT |
| Binance | 0.10% | 0.10% | ~0.0005 BTC | Varies |
| KuCoin | 0.10% | 0.10% | Varies | Varies |
| Gate.io | 0.30% | 0.30% | 0.001 BTC | 1 USDT |
| Bitget | 0.10% | 0.10% | 0.0003 BTC | 1 USDT |
| CoinEx | 0.20% | 0.20% | 0.0001 BTC | 1 USDT |
| BingX | 0.10% | 0.10% | 0.00035 BTC | 1 USDT |

**Формат opportunity:**

```json
{
  "id": "opp_1720000000_binance_bybit_btcusdt",
  "symbol": "BTC/USDT",
  "buy_exchange": "binance",
  "sell_exchange": "bybit",
  "buy_price": 67432.15,
  "sell_price": 67450.30,
  "gross_spread_pct": 0.027,
  "buy_fee_pct": 0.10,
  "sell_fee_pct": 0.10,
  "withdrawal_fee_usd": 1.0,
  "net_spread_pct": -0.073,
  "detected_at": 1720000000000,
  "ttl_seconds": 5
}
```

### 2.3. Модуль API Gateway (порт 8000)

**Назначение:** Единая точка входа для frontend. REST API для исторических данных, WebSocket для real-time данных.

| ID | Требование | Приоритет |
|----|-----------|-----------|
| G-001 | REST API на FastAPI с OpenAPI/Swagger документацией | Must |
| G-002 | WebSocket endpoint `/ws` для real-time данных (цены, спреды, сделки) | Must |
| G-003 | Чтение исторических данных из TimescaleDB (prices, opportunities, trades, balance) | Must |
| G-004 | Агрегация данных для дашборда: свечи, P&L, статистика | Must |
| G-005 | JWT аутентификация для всех endpoints | Must |
| G-006 | Rate limiting: 100 req/min для REST, 10 msg/sec для WS per client | Must |
| G-007 | CORS настройки для frontend origin | Must |
| G-008 | Health check `GET /health` + readiness/liveness probes | Must |
| G-009 | Prometheus метрики: `http_requests_total`, `http_request_duration_ms`, `ws_clients_active` | Must |
| G-010 | Graceful shutdown — закрытие всех WS соединений с клиентами | Must |
| G-011 | API versioning — префикс `/api/v1/` | Should |
| G-012 | Request/response logging с correlation ID | Should |

### 2.4. Модуль Executor (порт 8003)

**Назначение:** Paper trading — симуляция исполнения арбитражных сделок, расчёт P&L, запись в TimescaleDB.

| ID | Требование | Приоритет |
|----|-----------|-----------|
| E-001 | Чтение opportunities из Redis Stream `opportunities` | Must |
| E-002 | Симуляция исполнения buy-ордера на бирже A (buy_exchange) | Must |
| E-003 | Симуляция исполнения sell-ордера на бирже B (sell_exchange) | Must |
| E-004 | Учёт slippage при симуляции (0.1-0.3% random) | Must |
| E-005 | Учёт всех комиссий при расчёте итогового P&L | Must |
| E-006 | Запись результата сделки в TimescaleDB (`trades` hypertable) | Must |
| E-007 | Обновление виртуального баланса после каждой сделки | Must |
| E-008 | Публикация результата сделки в Redis Stream `trades` | Must |
| E-009 | Max position: ≤ 10% от виртуального баланса на сделку | Must |
| E-010 | Kill switch — аварийная остановка всех сделок по API endpoint | Must |
| E-011 | Health check `GET /health` | Must |
| E-012 | Метрики Prometheus: `trades_executed_total`, `trade_pnl_usd`, `executor_latency_ms` | Must |
| E-013 | Graceful shutdown — завершение текущей сделки, flush в БД | Must |
| E-014 | Circuit Breaker — остановка при убытке > X% за сутки | Should |
| E-015 | Partial fill simulation — симуляция частичного исполнения | Could |

**Начальный виртуальный баланс (конфигурация):**

| Биржа | Начальный баланс USDT |
|-------|---------------------|
| Binance | 10,000 |
| Bybit | 10,000 |
| KuCoin | 10,000 |
| Bitget | 10,000 |
| Gate.io | 5,000 |
| CoinEx | 5,000 |
| BingX | 5,000 |
| **Итого** | **50,000 USDT** |

**Формат trade (запись в TimescaleDB):**

```json
{
  "id": "trade_1720000001",
  "opportunity_id": "opp_1720000000_binance_bybit_btcusdt",
  "symbol": "BTC/USDT",
  "buy_exchange": "binance",
  "sell_exchange": "bybit",
  "buy_price": 67432.15,
  "sell_price": 67450.30,
  "amount": 0.1,
  "buy_fee": 6.74,
  "sell_fee": 6.75,
  "withdrawal_fee": 1.0,
  "slippage_cost": 13.49,
  "gross_pnl": 1.82,
  "net_pnl": -25.16,
  "status": "completed",
  "executed_at": 1720000001000,
  "duration_ms": 234
}
```

### 2.5. Модуль Notifier (порт 8004)

**Назначение:** Telegram-уведомления о спредах и завершённых сделках.

| ID | Требование | Приоритет |
|----|-----------|-----------|
| N-001 | Чтение opportunities из Redis Stream `opportunities` | Must |
| N-002 | Чтение trades из Redis Stream `trades` | Must |
| N-003 | Отправка Telegram сообщений при обнаружении спреда > threshold | Must |
| N-004 | Отправка Telegram сообщений при завершении сделки | Must |
| N-005 | Rate limiting: max 20 msg/sec (лимит Telegram Bot API) | Must |
| N-006 | Очередь сообщений в Redis List (backpressure) | Must |
| N-007 | Использование aiogram 3.x для взаимодействия с Telegram Bot API | Must |
| N-008 | Форматирование сообщений: эмодзи, форматирование цен, P&L | Must |
| N-009 | Health check `GET /health` | Must |
| N-010 | Метрики Prometheus: `telegram_messages_sent_total`, `telegram_errors_total` | Must |
| N-011 | Graceful shutdown — дождаться отправки очереди | Must |
| N-012 | Команды бота: `/status`, `/balance`, `/trades`, `/settings` | Should |
| N-013 | Подписка/отписка от типов уведомлений | Could |

**Формат Telegram сообщения (спред):**

```
🚨 Arbitrage Opportunity Detected!

Pair: BTC/USDT
Buy: Binance @ $67,432.15
Sell: Bybit @ $67,450.30

Spread: 0.027%
Net Spread: -0.073%

⏱ Detected: 2025-07-03 12:00:00 UTC
```

### 2.6. React Dashboard

**Назначение:** Веб-интерфейс для мониторинга и управления арбитражной системой.

| ID | Требование | Приоритет |
|----|-----------|-----------|
| D-001 | Real-time таблица цен с 7 бирж (best bid/ask) | Must |
| D-002 | Real-time таблица спредов (sortable, filterable) | Must |
| D-003 | График истории спредов (Recharts, time-series) | Must |
| D-004 | Таблица истории сделок с P&L | Must |
| D-005 | Виртуальный баланс по биржам | Must |
| D-006 | Настройки: min_spread, max_position, включение/выключение пар | Must |
| D-007 | Kill switch кнопка (аварийная остановка) | Must |
| D-008 | WebSocket подключение к API Gateway для real-time обновлений | Must |
| D-009 | Автоматический reconnect WS с exponential backoff | Must |
| D-010 | Responsive design (desktop + mobile) | Must |
| D-011 | Dark/Light theme toggle | Should |
| D-012 | Экспорт данных в CSV | Should |
| D-013 | Heatmap спредов (матрица бирж × пары) | Could |

**Страницы дашборда:**

| Страница | URL | Описание |
|----------|-----|----------|
| Dashboard (Home) | `/` | Обзор: цены, спреды, P&L |
| Trades | `/trades` | История сделок с фильтрами |
| Analytics | `/analytics` | Графики, статистика, агрегации |
| Settings | `/settings` | Настройки системы |

### 2.7. Telegram Bot

**Назначение:** Интерактивное управление и мониторинг через Telegram.

| ID | Требование | Приоритет |
|----|-----------|-----------|
| B-001 | Команда `/start` — приветствие, список команд | Must |
| B-002 | Команда `/status` — статус системы (WS соединения, scanner) | Must |
| B-003 | Команда `/balance` — виртуальный баланс по биржам | Must |
| B-004 | Команда `/trades [N]` — последние N сделок (default: 5) | Must |
| B-005 | Команда `/settings` — текущие настройки (min_spread, max_position) | Must |
| B-006 | Команда `/killswitch` — аварийная остановка (с подтверждением) | Must |
| B-007 | Inline buttons для навигации | Should |
| B-008 | Автоматические уведомления о спредах > threshold | Should |
| B-009 | Автоматические уведомления о завершённых сделках | Should |

---

## 3. Нефункциональные требования

### 3.1. Производительность

| Метрика | Требование | Метод измерения |
|---------|-----------|----------------|
| REST API throughput | ≥ 35,000 req/sec | wrk/k6 benchmark |
| REST API latency (p50) | < 10 ms | Prometheus histogram |
| REST API latency (p99) | < 50 ms | Prometheus histogram |
| WebSocket broadcast latency | < 50 ms | end-to-end measurement |
| Redis Streams throughput | ≥ 80,000 msg/sec | redis-benchmark |
| TimescaleDB ingestion | ≥ 100,000 rows/sec | batch INSERT benchmark |
| TimescaleDB query latency (simple) | < 10 ms | p50 measurement |
| TimescaleDB query latency (aggregation) | < 500 ms | p50 measurement |
| Scanner spread detection | < 50 ms | end-to-end measurement |
| Collector WS message processing | < 5 ms | per-message measurement |
| Frontend initial load | < 2 sec | Lighthouse TTI |
| Frontend WS reconnection | < 3 sec | manual test |

### 3.2. Надёжность

| Требование | Описание |
|-----------|----------|
| Uptime SLA | 99.9% (max 43 min downtime/месяц) |
| WebSocket auto-reconnect | Exponential backoff: 100ms → 1s → 5s → 30s → max 60s |
| Redis reconnect | Автоматический с retry every 1s |
| TimescaleDB reconnect | Connection pool с retry, max 5 попыток |
| Graceful degradation | При недоступности биржи — продолжать работу с остальными |
| Circuit Breaker | После 5 ошибок — OPEN state на 30 секунд |
| Dead Letter Queue | Ошибочные сообщения → `*:dlq` stream |
| Health checks | Каждые 10 секунд, 3 retries before unhealthy |
| Data retention | Prices: 30 дней, Opportunities: 90 дней, Trades: 1 год |

### 3.3. Безопасность

| Требование | Описание |
|-----------|----------|
| JWT аутентификация | HS256, expiry 24h, refresh token 7 дней |
| HTTPS only | TLS 1.3 для всех внешних соединений |
| API Keys isolation | Каждая биржа — отдельный encrypted storage |
| Rate limiting | 100 req/min REST, 10 msg/sec WS per IP |
| Input validation | Pydantic models для всех входных данных |
| SQL injection prevention | SQLAlchemy parameterized queries |
| XSS/CSRF protection | CORS strict, CSRF tokens для state-changing ops |
| Secret management | Environment variables, Vault post-MVP |

### 3.4. Масштабируемость

| Аспект | Стратегия |
|--------|----------|
| Горизонтальное (микросервисы) | Независимое масштабирование collector/scanner/executor |
| Collector sharding | По биржам или по парам (запуск N инстансов) |
| Redis | Single instance для MVP, Redis Cluster при >100K msg/sec |
| TimescaleDB | Vertical scaling для MVP, read replicas при >1M rows/sec |
| API Gateway | State-less, за балансировщиком |

### 3.5. Наблюдаемость (observability)

| Компонент | Инструмент | Метрики |
|-----------|-----------|---------|
| Метрики | Prometheus | Все сервисы экспортируют `/metrics` |
| Визуализация | Grafana | Dashboard: latency, throughput, errors, business metrics |
| Логи | structlog + JSON | Centralized logging (ELK post-MVP) |
| Алерты | Prometheus Alertmanager | PagerDuty/OpsGenie post-MVP |
| Трейсинг | OpenTelemetry (post-MVP) | Distributed tracing |

**Grafana Dashboards:**

| Dashboard | Метрики |
|-----------|---------|
| System Overview | CPU, Memory, Network, Disk всех сервисов |
| Arbitrage Business | Spreads found, Trades executed, P&L, Balance |
| Exchange Health | WS connection status, API errors per exchange |
| API Gateway | HTTP requests, latency, errors, WS clients |
| Data Pipeline | Redis stream lengths, consumer lag, DB ingestion rate |

**Key Alerts:**

| Alert | Condition | Severity |
|-------|-----------|----------|
| WS connection down | `ws_connections_active == 0` для биржи > 1 min | Critical |
| High scanner latency | `scanner_latency_ms p99 > 200` | Warning |
| Redis stream growing | `redis_stream_length > 10000` | Warning |
| DB connection errors | `db_connection_errors > 5` in 5 min | Critical |
| Negative P&L streak | `daily_pnl < -5%` | Warning |
| API Gateway 5xx | `http_5xx_rate > 1%` | Critical |
| High memory usage | `container_memory_usage > 90%` | Warning |


---

## 4. Архитектура системы

### 4.1. Диаграмма компонентов (текстовое описание)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL LAYER                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  Bybit   │  │ Binance  │  │  KuCoin  │  │ Gate.io  │  │  Bitget  │      │
│  │  WS API  │  │  WS API  │  │  WS API  │  │  WS API  │  │  WS API  │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│  ┌──────────┐  ┌──────────┐                                                    │
│  │  CoinEx  │  │  BingX   │                                                    │
│  │  WS API  │  │  WS API  │                                                    │
│  └────┬─────┘  └────┬─────┘                                                    │
└───────┼──────────────┼──────────────────────────────────────────────────────────┘
        │              │
        ▼              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MICROSERVICES LAYER                                  │
│                                                                              │
│  ┌──────────────────────┐    Redis Streams (Message Bus)                     │
│  │   Collector :8001    │◄─────────────────────────────────────┐            │
│  │  CCXT Pro → Redis    │    ┌──────────────┐  ┌───────────┐  │            │
│  │  WS connections (7)  │───►│  prices      │  │opportunities│ │            │
│  └──────────────────────┘    │  (stream)    │  │ (stream)   │  │            │
│                              └──────┬───────┘  └─────┬─────┘  │            │
│  ┌──────────────────────┐           │                │        │            │
│  │   Scanner :8002      │◄──────────┘                │        │            │
│  │  Scan → Calculate    │                              │        │            │
│  │  Net Spread → Redis  │──────────────────────────────┘        │            │
│  └──────────────────────┘                                      │            │
│                                                                ▼            │
│  ┌──────────────────────┐    ┌──────────────┐  ┌───────────┐ ┌─────────┐   │
│  │   Executor :8003     │◄───│ opportunities│  │  trades   │ │ balance │   │
│  │  Paper Trading       │    │   (stream)   │  │ (stream)  │ │  (set)  │   │
│  │  Simulate → TimescaleDB    └──────────────┘  └─────┬─────┘ └─────────┘   │
│  └──────────────────────┘                            │                    │
│                                                      │                    │
│  ┌──────────────────────┐                            │                    │
│  │   Notifier :8004     │◄───────────────────────────┘                    │
│  │  Telegram Bot        │                                                 │
│  │  aiogram 3.x         │                                                 │
│  └──────────────────────┘                                                 │
│                                                                              │
│  ┌──────────────────────┐                                                   │
│  │  API Gateway :8000   │◄─── React Dashboard (on user browser)            │
│  │  REST + WebSocket    │      WebSocket /ws                                │
│  │  FastAPI             │      HTTP /api/v1/*                               │
│  │  Auth (JWT)          │                                                   │
│  └──────────┬───────────┘                                                   │
└─────────────┼───────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                          │
│                                                                              │
│  ┌──────────────────────────┐    ┌──────────────────────────┐               │
│  │    TimescaleDB :5432     │    │      Redis :6379         │               │
│  │  ┌──────────────────┐    │    │  ┌──────────────────┐    │               │
│  │  │   prices         │◄───┼────┼──┤  prices (stream) │    │               │
│  │  │   (hypertable)   │    │    │  └──────────────────┘    │               │
│  │  ├──────────────────┤    │    │  ┌──────────────────┐    │               │
│  │  │   opportunities  │◄───┼────┼──┤  opportunities   │    │               │
│  │  │   (hypertable)   │    │    │  │   (stream)       │    │               │
│  │  ├──────────────────┤    │    │  └──────────────────┘    │               │
│  │  │   trades         │◄───┼────┼──┤  trades (stream) │    │               │
│  │  │   (hypertable)   │    │    │  └──────────────────┘    │               │
│  │  ├──────────────────┤    │    │  ┌──────────────────┐    │               │
│  │  │   balance        │◄───┼────┼──┤  balance (hash)  │    │               │
│  │  │   (hypertable)   │    │    │  └──────────────────┘    │               │
│  │  └──────────────────┘    │    │  ┌──────────────────┐    │               │
│  │                          │    │  │  config (hash)   │    │               │
│  │  ┌──────────────────┐    │    │  └──────────────────┘    │               │
│  │  │   users          │    │    │  ┌──────────────────┐    │               │
│  │  │   (table)        │    │    │  │  telegram_queue  │    │               │
│  │  └──────────────────┘    │    │  │  (list)          │    │               │
│  │                          │    │  └──────────────────┘    │               │
│  └──────────────────────────┘    └──────────────────────────┘               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                       OBSERVABILITY LAYER                                    │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Prometheus   │  │   Grafana    │  │  cAdvisor    │  │ Node Exporter│    │
│  │   :9090      │  │   :3000      │  │              │  │              │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2. Поток данных (data flow)

```
Phase 1: Сбор данных (Collector)
─────────────────────────────────
[Bybit WS] ──┐
[Binance WS]─┤
[KuCoin WS] ─┤    ┌─────────────┐    ┌─────────────────────┐
[Gate.io WS]─┼───►│  Collector  │───►│ Redis: prices stream │
[Bitget WS] ─┤    │   :8001     │    │ (XADD prices *)      │
[CoinEx WS] ─┤    │ CCXT Pro    │    └─────────────────────┘
[BingX WS] ──┘    │ picows      │
                   └─────────────┘

Phase 2: Сканирование (Scanner)
───────────────────────────────
┌─────────────────────┐    ┌─────────────┐    ┌──────────────────────────┐
│ Redis: prices stream │───►│   Scanner   │───►│ Redis: opportunities     │
│ (XREADGROUP)         │    │   :8002     │    │ stream (XADD opp *)      │
└─────────────────────┘    │ calc spread │    └──────────────────────────┘
                           │ filter      │           │
                           └─────────────┘           ▼
                                              ┌──────────────┐
                                              │ TimescaleDB:  │
                                              │ opportunities│
                                              │ hypertable   │
                                              └──────────────┘

Phase 3: Исполнение (Executor - Paper Trading)
─────────────────────────────────────────────
┌──────────────────────────┐    ┌─────────────┐    ┌─────────────────────┐
│ Redis: opportunities     │───►│   Executor  │───►│ Redis: trades stream │
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
│ Redis: opportunities     │───►│   Notifier  │───►│ Telegram Bot API │
│ Redis: trades            │    │   :8004     │    │ (aiogram 3.x)    │
└──────────────────────────┘    │ format msg  │    └─────────────────┘
                                │ queue+send  │
                                └─────────────┘

Phase 5: Frontend (React Dashboard)
──────────────────────────────────
┌─────────────────┐    WS /ws     ┌─────────────┐    ┌──────────────────┐
│  React Dashboard│◄─────────────►│ API Gateway │◄───│ TimescaleDB      │
│  (Browser)      │    real-time  │   :8000     │    │ (historical data)│
│                 │               │ REST /api/* │    └──────────────────┘
│  - Price table  │◄──────────────┤ WebSocket   │    ┌──────────────────┐
│  - Spread table │               │ JWT Auth    │◄───│ Redis Streams    │
│  - Trade history│               └─────────────┘    └──────────────────┘
│  - P&L charts   │
└─────────────────┘
```

### 4.3. Взаимодействие микросервисов

| От сервиса | К сервису | Протокол | Назначение |
|-----------|-----------|----------|------------|
| Collector | 7 бирж | WebSocket (CCXT Pro) | Получение цен real-time |
| Collector | Redis | Redis Protocol (XADD) | Публикация цен в stream `prices` |
| Scanner | Redis | Redis Protocol (XREADGROUP) | Чтение цен из stream `prices` |
| Scanner | Redis | Redis Protocol (XADD) | Публикация opportunities |
| Scanner | TimescaleDB | PostgreSQL (asyncpg) | Сохранение opportunities |
| Executor | Redis | Redis Protocol (XREADGROUP) | Чтение opportunities |
| Executor | Redis | Redis Protocol (XADD) | Публикация trades |
| Executor | TimescaleDB | PostgreSQL (asyncpg) | Сохранение trades, обновление balance |
| Notifier | Redis | Redis Protocol (XREADGROUP) | Чтение opportunities + trades |
| Notifier | Telegram | HTTPS (aiogram) | Отправка сообщений |
| API Gateway | TimescaleDB | PostgreSQL (asyncpg) | Чтение исторических данных |
| API Gateway | Redis | Redis Protocol (XREAD) | Real-time данные из streams |
| API Gateway | Frontend | WebSocket (fastapi WS) | Push real-time данных |
| Frontend | API Gateway | HTTPS (REST) | Исторические данные, аутентификация |
| Frontend | API Gateway | WebSocket | Real-time подписка на цены/спреды/сделки |
| Prometheus | Все сервисы | HTTP GET /metrics | Сбор метрик |
| Grafana | Prometheus | HTTP | Визуализация метрик |
| Health checks | Все сервисы | HTTP GET /health | Проверка состояния |

### 4.4. Схема TimescaleDB (все таблицы с типами)

```sql
-- ============================================
-- EXTENSIONS
-- ============================================
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. prices hypertable
-- Хранит все тиковые данные (bid/ask) со всех бирж
-- ============================================
CREATE TABLE prices (
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

-- Convert to hypertable (partition by time, 1-hour chunks)
SELECT create_hypertable('prices', 'time', chunk_time_interval => INTERVAL '1 hour');

-- Indexes
CREATE INDEX idx_prices_exchange_symbol_time 
    ON prices (exchange, symbol, time DESC);
CREATE INDEX idx_prices_symbol_time 
    ON prices (symbol, time DESC);

-- Compression policy (after 7 days)
ALTER TABLE prices SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'exchange, symbol'
);
SELECT add_compression_policy('prices', INTERVAL '7 days');

-- Retention policy (30 days)
SELECT add_retention_policy('prices', INTERVAL '30 days');

-- ============================================
-- 2. opportunities hypertable
-- Хранит обнаруженные арбитражные возможности
-- ============================================
CREATE TABLE opportunities (
    time            TIMESTAMPTZ NOT NULL,
    id              VARCHAR(100) NOT NULL,
    symbol          VARCHAR(20) NOT NULL,
    buy_exchange    VARCHAR(20) NOT NULL,
    sell_exchange   VARCHAR(20) NOT NULL,
    buy_price       DECIMAL(18,8) NOT NULL,
    sell_price      DECIMAL(18,8) NOT NULL,
    gross_spread_pct DECIMAL(8,4) NOT NULL,
    buy_fee_pct     DECIMAL(6,4) NOT NULL,
    sell_fee_pct    DECIMAL(6,4) NOT NULL,
    withdrawal_fee_usd DECIMAL(10,4),
    net_spread_pct  DECIMAL(8,4) NOT NULL,

    CONSTRAINT opp_buy_sell_diff CHECK (buy_exchange != sell_exchange),
    CONSTRAINT opp_net_calc CHECK (net_spread_pct <= gross_spread_pct)
);

SELECT create_hypertable('opportunities', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_opp_symbol_time 
    ON opportunities (symbol, time DESC);
CREATE INDEX idx_opp_buy_sell_time 
    ON opportunities (buy_exchange, sell_exchange, time DESC);
CREATE INDEX idx_opp_net_spread 
    ON opportunities (net_spread_pct, time DESC) 
    WHERE net_spread_pct > 0;

ALTER TABLE opportunities SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, buy_exchange, sell_exchange'
);
SELECT add_compression_policy('opportunities', INTERVAL '7 days');
SELECT add_retention_policy('opportunities', INTERVAL '90 days');

-- ============================================
-- 3. trades hypertable
-- Хранит paper trading сделки
-- ============================================
CREATE TABLE trades (
    time            TIMESTAMPTZ NOT NULL,
    id              VARCHAR(100) PRIMARY KEY,
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

    CONSTRAINT trades_status_check CHECK (status IN ('pending', 'completed', 'failed', 'cancelled'))
);

SELECT create_hypertable('trades', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_trades_symbol_time 
    ON trades (symbol, time DESC);
CREATE INDEX idx_trades_status 
    ON trades (status, time DESC);
CREATE INDEX idx_trades_opportunity 
    ON trades (opportunity_id);

ALTER TABLE trades SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, status'
);
SELECT add_compression_policy('trades', INTERVAL '30 days');
SELECT add_retention_policy('trades', INTERVAL '1 year');

-- ============================================
-- 4. balance hypertable
-- Хранит историю виртуального баланса по биржам
-- ============================================
CREATE TABLE balance (
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

SELECT create_hypertable('balance', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_balance_exchange_time 
    ON balance (exchange, time DESC);
CREATE INDEX idx_balance_asset_time 
    ON balance (asset, time DESC);

SELECT add_retention_policy('balance', INTERVAL '1 year');

-- ============================================
-- 5. users table (regular PostgreSQL table)
-- ============================================
CREATE TABLE users (
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

CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_telegram ON users (telegram_id);

-- ============================================
-- 6. settings table (regular PostgreSQL table)
-- ============================================
CREATE TABLE settings (
    id              SERIAL PRIMARY KEY,
    key             VARCHAR(100) UNIQUE NOT NULL,
    value           JSONB NOT NULL,
    description     TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by      UUID REFERENCES users(id)
);

CREATE INDEX idx_settings_key ON settings (key);

-- Initial settings
INSERT INTO settings (key, value, description) VALUES
('min_spread_pct', '0.30', 'Minimum spread % to trigger opportunity'),
('max_position_pct', '10.00', 'Max % of balance per trade'),
('slippage_tolerance_pct', '0.20', 'Slippage tolerance %'),
('execution_timeout_sec', '2', 'Max execution time in seconds'),
('kill_switch', 'false', 'Emergency stop flag'),
('notification_spread_threshold', '0.50', 'Min spread % for Telegram alert'),
('daily_loss_limit_pct', '5.00', 'Daily loss limit % - stop trading');

-- ============================================
-- 7. exchange_configs table
-- ============================================
CREATE TABLE exchange_configs (
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

-- Initial exchange configs
INSERT INTO exchange_configs (exchange, maker_fee_pct, taker_fee_pct, withdrawal_btc, withdrawal_usdt, rate_limit_req_per_sec) VALUES
('bybit', 0.10, 0.10, 0.000085, 1.0, 50),
('binance', 0.10, 0.10, 0.0005, 0.0, 1200),
('kucoin', 0.10, 0.10, 0.0, 0.0, 200),
('gateio', 0.30, 0.30, 0.001, 1.0, 200),
('bitget', 0.10, 0.10, 0.0003, 1.0, 20),
('coinex', 0.20, 0.20, 0.0001, 1.0, 10),
('bingx', 0.10, 0.10, 0.00035, 1.0, 24);

-- ============================================
-- 8. tracked_pairs table
-- ============================================
CREATE TABLE tracked_pairs (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL,
    exchange        VARCHAR(20) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    priority        INTEGER NOT NULL DEFAULT 3,
    min_spread_override DECIMAL(6,4),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, exchange)
);

-- Initial tracked pairs (P1 priority)
INSERT INTO tracked_pairs (symbol, exchange, is_active, priority) VALUES
('BTC/USDT', 'binance', true, 1),
('BTC/USDT', 'bybit', true, 1),
('BTC/USDT', 'kucoin', true, 1),
('BTC/USDT', 'bitget', true, 1),
('ETH/USDT', 'binance', true, 1),
('ETH/USDT', 'bybit', true, 1),
('ETH/USDT', 'kucoin', true, 1),
('ETH/USDT', 'bitget', true, 1);

-- ============================================
-- 9. audit_log table
-- ============================================
CREATE TABLE audit_log (
    time            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id),
    action          VARCHAR(50) NOT NULL,
    resource        VARCHAR(50) NOT NULL,
    resource_id     VARCHAR(100),
    old_value       JSONB,
    new_value       JSONB,
    ip_address      INET,
    user_agent      TEXT
);

SELECT create_hypertable('audit_log', 'time', chunk_time_interval => INTERVAL '1 week');
CREATE INDEX idx_audit_user ON audit_log (user_id, time DESC);
CREATE INDEX idx_audit_action ON audit_log (action, time DESC);
SELECT add_retention_policy('audit_log', INTERVAL '6 months');

-- ============================================
-- CONTINUOUS AGGREGATES (materialized views)
-- ============================================

-- Hourly price statistics per exchange/symbol
CREATE MATERIALIZED VIEW prices_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    exchange,
    symbol,
    avg(bid) AS avg_bid,
    avg(ask) AS avg_ask,
    min(bid) AS min_bid,
    max(ask) AS max_ask,
    last(bid, time) AS last_bid,
    last(ask, time) AS last_ask,
    count(*) AS tick_count
FROM prices
GROUP BY bucket, exchange, symbol;

CREATE INDEX idx_prices_hourly_symbol ON prices_hourly (symbol, bucket DESC);

-- Daily P&L summary
CREATE MATERIALIZED VIEW pnl_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS day,
    symbol,
    count(*) AS trade_count,
    sum(gross_pnl) AS total_gross_pnl,
    sum(net_pnl) AS total_net_pnl,
    avg(duration_ms) AS avg_duration_ms,
    sum(buy_fee + sell_fee + withdrawal_fee + slippage_cost) AS total_costs
FROM trades
WHERE status = 'completed'
GROUP BY day, symbol;

-- Refresh policies
SELECT add_continuous_aggregate_policy('prices_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('pnl_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

### 4.5. Схема Redis Streams (ключи, формат сообщений)

#### 4.5.1 Stream: `prices`

| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| `exchange` | string | Код биржи | `binance` |
| `symbol` | string | Торговая пара | `BTC/USDT` |
| `bid` | float | Лучшая цена покупки | `67432.15` |
| `ask` | float | Лучшая цена продажи | `67433.80` |
| `bid_volume` | float | Объём на лучшем bid | `1.234` |
| `ask_volume` | float | Объём на лучшем ask | `0.987` |
| `timestamp` | int64 | Время с биржи (unix ms) | `1720000000000` |
| `received_at` | int64 | Время получения (unix ms) | `1720000000015` |
| `latency_ms` | int | Задержка получения | `15` |

```
XADD prices * exchange binance symbol "BTC/USDT" bid 67432.15 ask 67433.80 bid_volume 1.234 ask_volume 0.987 timestamp 1720000000000 received_at 1720000000015 latency_ms 15
```

**Consumer Group:** `scanner-cg`  
**Consumer:** `scanner-1`  
**Maxlen:** ~ 100,000 (backpressure, ~10 секунд данных при 10K msg/sec)

#### 4.5.2 Stream: `opportunities`

| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| `id` | string | Уникальный ID opportunity | `opp_1720000000_binance_bybit_btcusdt` |
| `symbol` | string | Торговая пара | `BTC/USDT` |
| `buy_exchange` | string | Биржа покупки | `binance` |
| `sell_exchange` | string | Биржа продажи | `bybit` |
| `buy_price` | float | Цена покупки | `67432.15` |
| `sell_price` | float | Цена продажи | `67450.30` |
| `gross_spread_pct` | float | Гросс-спред % | `0.027` |
| `net_spread_pct` | float | Нет-спред % (с учётом комиссий) | `-0.073` |
| `detected_at` | int64 | Время обнаружения (unix ms) | `1720000000000` |

**Consumer Groups:** `executor-cg`, `notifier-cg`  
**Maxlen:** ~ 10,000

#### 4.5.3 Stream: `trades`

| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| `id` | string | Уникальный ID сделки | `trade_1720000001` |
| `opportunity_id` | string | ID связанной opportunity | `opp_1720000000_binance_bybit_btcusdt` |
| `symbol` | string | Торговая пара | `BTC/USDT` |
| `buy_exchange` | string | Биржа покупки | `binance` |
| `sell_exchange` | string | Биржа продажи | `bybit` |
| `amount` | float | Объём сделки | `0.1` |
| `net_pnl` | float | Итоговый P&L | `-25.16` |
| `status` | string | Статус: completed/failed | `completed` |
| `executed_at` | int64 | Время исполнения (unix ms) | `1720000001000` |

**Consumer Group:** `notifier-cg`  
**Maxlen:** ~ 10,000

#### 4.5.4 Redis Hash: `balance`

Хранит текущий виртуальный баланс по биржам (ключ: `balance:{exchange}`).

```
HSET balance:binance USDT 10000 BTC 0.5 ETH 2.0
HSET balance:bybit USDT 10000 BTC 0.5 ETH 2.0
HSET balance:kucoin USDT 10000 BTC 0.5 ETH 2.0
```

#### 4.5.5 Redis Hash: `config`

Хранит runtime конфигурацию системы.

```
HSET config min_spread_pct 0.30
HSET config max_position_pct 10.0
HSET config slippage_tolerance_pct 0.20
HSET config execution_timeout_sec 2
HSET config kill_switch false
HSET config notification_spread_threshold 0.50
```

#### 4.5.6 Redis List: `telegram:queue`

Очередь сообщений для Telegram бота (backpressure).

```
LPUSH telegram:queue '{"type":"spread","message":"..."}'
RPOP telegram:queue  (consumer side)
```

#### 4.5.7 Redis Streams Dead Letter Queues

| Стрим | Назначение |
|-------|-----------|
| `prices:dlq` | Необработанные цены (scanner down) |
| `opportunities:dlq` | Необработанные opportunities |
| `trades:dlq` | Необработанные trades |


---

## 5. Технологический стек

### 5.1. Backend

| Компонент | Технология | Версия | Назначение |
|-----------|-----------|--------|------------|
| Язык | Python | 3.11+ | Основной язык разработки |
| Event loop | uvloop | latest | 2-4x ускорение asyncio |
| Web framework | FastAPI | 0.110+ | REST API + WebSocket endpoints |
| ASGI server | uvicorn | 0.30+ | HTTP server (uvloop + httptools) |
| Exchange API | CCXT Pro | 4.3+ | Унифицированный доступ к 7 биржам |
| WS клиент (low-level) | picows | latest | Latency-critical WebSocket connections |
| Database driver | asyncpg | 0.29+ | Асинхронный PostgreSQL/TimescaleDB |
| ORM | SQLAlchemy 2.0 | 2.0+ | ORM + Alembic миграции |
| Migrations | Alembic | latest | Schema migrations |
| Redis client | redis-py (async) | 5.0+ | Redis Streams + pub/sub |
| Telegram Bot | aiogram | 3.5+ | Асинхронный Telegram Bot API |
| Auth | python-jose | latest | JWT encode/decode |
| Password hashing | bcrypt | latest | Хеширование паролей |
| Validation | Pydantic | 2.7+ | Валидация входных/выходных данных |
| HTTP client | httpx | 0.27+ | Async HTTP для внешних API |
| Scheduling | APScheduler | latest | Cron-like задачи внутри сервисов |

### 5.2. Frontend

| Компонент | Технология | Версия | Назначение |
|-----------|-----------|--------|------------|
| Framework | React | 19.x | UI фреймворк |
| Bundler | Vite | 6.x | Сборка (dev + production) |
| Language | TypeScript | 5.5+ | Типизация |
| Styling | Tailwind CSS | 3.4+ | Utility-first CSS |
| UI Components | shadcn/ui | latest | Компоненты на Radix UI |
| State management | Zustand | 4.5+ | Глобальный state |
| Charts | Recharts | 2.12+ | Графики и визуализация |
| Notifications | Sonner | latest | Toast notifications |
| Forms | React Hook Form | 7.51+ | Управление формами |
| Validation | Zod | 3.23+ | Schema validation |
| Routing | React Router | 6.23+ | Клиентский роутинг |
| Icons | Lucide React | latest | Иконки |

### 5.3. Инфраструктура

| Компонент | Технология | Версия | Назначение |
|-----------|-----------|--------|------------|
| Containerization | Docker | 24.x+ | Контейнеризация всех сервисов |
| Orchestration | Docker Compose | 2.24+ | Локальное развёртывание |
| Database | TimescaleDB | 2.14+ (PostgreSQL 16) | Time-series data |
| Message Bus | Redis | 7.2+ | Streams, cache, pub/sub |
| Monitoring | Prometheus | 2.52+ | Метрики |
| Visualization | Grafana | 10.4+ | Дашборды |
| Container metrics | cAdvisor | 0.49+ | Метрики Docker контейнеров |
| Host metrics | Node Exporter | latest | Метрики хоста |
| Reverse Proxy | Traefik | 3.0+ | (Post-MVP) Ingress + SSL |

### 5.4. Библиотеки и зависимости

#### 5.4.1 Общие зависимости (shared/)

```txt
# requirements-shared.txt
pydantic>=2.7.0
pydantic-settings>=2.2.0
orjson>=3.10.0
structlog>=24.1.0
python-json-logger>=2.0.7
tenacity>=8.3.0
prometheus-client>=0.20.0
```

#### 5.4.2 Collector (services/collector/)

```txt
# requirements-collector.txt
-r ../shared/requirements-shared.txt
fastapi>=0.110.0
uvicorn[standard]>=0.30.0
ccxt>=4.3.0
picows>=1.6.0
redis>=5.0.0
asyncpg>=0.29.0
```

#### 5.4.3 Scanner (services/scanner/)

```txt
# requirements-scanner.txt
-r ../shared/requirements-shared.txt
fastapi>=0.110.0
uvicorn[standard]>=0.30.0
redis>=5.0.0
asyncpg>=0.29.0
```

#### 5.4.4 API Gateway (services/api-gateway/)

```txt
# requirements-api-gateway.txt
-r ../shared/requirements-shared.txt
fastapi>=0.110.0
uvicorn[standard]>=0.30.0
python-jose[cryptography]>=3.3.0
bcrypt>=4.1.0
redis>=5.0.0
asyncpg>=0.29.0
sqlalchemy[asyncio]>=2.0.0
alembic>=1.13.0
python-multipart>=0.0.9
```

#### 5.4.5 Executor (services/executor/)

```txt
# requirements-executor.txt
-r ../shared/requirements-shared.txt
fastapi>=0.110.0
uvicorn[standard]>=0.30.0
redis>=5.0.0
asyncpg>=0.29.0
apscheduler>=3.10.0
```

#### 5.4.6 Notifier (services/notifier/)

```txt
# requirements-notifier.txt
-r ../shared/requirements-shared.txt
fastapi>=0.110.0
uvicorn[standard]>=0.30.0
aiogram>=3.5.0
redis>=5.0.0
asyncpg>=0.29.0
```

#### 5.4.7 Frontend (frontend/)

```json
// package.json dependencies
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^6.23.0",
    "zustand": "^4.5.0",
    "recharts": "^2.12.0",
    "sonner": "^1.4.0",
    "react-hook-form": "^7.51.0",
    "zod": "^3.23.0",
    "@hookform/resolvers": "^3.4.0",
    "lucide-react": "^0.400.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.3.0",
    "date-fns": "^3.6.0"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "vite": "^6.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0"
  }
}
```

---

## 6. API Спецификация

### 6.1. REST endpoints (полный список)

#### 6.1.1 Authentication

##### POST /api/v1/auth/register
Регистрация нового пользователя.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response 201:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "created_at": "2025-07-03T12:00:00Z",
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Response 400:**
```json
{
  "detail": "Email already registered",
  "code": "EMAIL_EXISTS"
}
```

**Response 422:**
```json
{
  "detail": [
    {"loc": ["body", "password"], "msg": "Password must be at least 8 characters", "type": "value_error"}
  ]
}
```

##### POST /api/v1/auth/login
Аутентификация пользователя.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Response 401:**
```json
{
  "detail": "Invalid credentials",
  "code": "INVALID_CREDENTIALS"
}
```

##### POST /api/v1/auth/refresh
Обновление access token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

##### GET /api/v1/auth/me
Информация о текущем пользователе.

**Headers:** `Authorization: Bearer {token}`

**Response 200:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "telegram_id": null,
  "is_active": true,
  "is_admin": false,
  "created_at": "2025-07-03T12:00:00Z",
  "last_login": "2025-07-03T12:00:00Z"
}
```

#### 6.1.2 Prices

##### GET /api/v1/prices/latest
Последние цены со всех бирж.

**Headers:** `Authorization: Bearer {token}`

**Query params:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|-------------|----------|
| symbol | string | Нет | Фильтр по паре (например, `BTC/USDT`) |
| exchange | string | Нет | Фильтр по бирже |

**Response 200:**
```json
{
  "data": [
    {
      "exchange": "binance",
      "symbol": "BTC/USDT",
      "bid": 67432.15,
      "ask": 67433.80,
      "bid_volume": 1.234,
      "ask_volume": 0.987,
      "updated_at": "2025-07-03T12:00:00.015Z",
      "latency_ms": 15
    },
    {
      "exchange": "bybit",
      "symbol": "BTC/USDT",
      "bid": 67431.50,
      "ask": 67434.20,
      "bid_volume": 0.876,
      "ask_volume": 1.543,
      "updated_at": "2025-07-03T12:00:00.012Z",
      "latency_ms": 12
    }
  ],
  "meta": {
    "count": 2,
    "timestamp": "2025-07-03T12:00:00Z"
  }
}
```

##### GET /api/v1/prices/history
Исторические цены (свечи/агрегации).

**Headers:** `Authorization: Bearer {token}`

**Query params:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|-------------|----------|
| symbol | string | Да | Торговая пара |
| exchange | string | Да | Биржа |
| from | ISO8601 | Да | Начало периода |
| to | ISO8601 | Да | Конец периода |
| interval | string | Нет | Интервал: `1m`, `5m`, `1h`, `1d` (default: `1h`) |

**Response 200:**
```json
{
  "data": [
    {
      "time": "2025-07-03T11:00:00Z",
      "avg_bid": 67400.50,
      "avg_ask": 67402.10,
      "min_bid": 67380.00,
      "max_ask": 67420.00,
      "last_bid": 67432.15,
      "last_ask": 67433.80,
      "tick_count": 4523
    }
  ]
}
```

#### 6.1.3 Spreads

##### GET /api/v1/spreads/current
Текущие спреды между биржами.

**Headers:** `Authorization: Bearer {token}`

**Query params:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|-------------|----------|
| symbol | string | Нет | Фильтр по паре |
| min_spread | float | Нет | Минимальный спред % (default: 0) |

**Response 200:**
```json
{
  "data": [
    {
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
  "meta": {
    "count": 1,
    "scanned_pairs": 8,
    "scanned_combinations": 56
  }
}
```

##### GET /api/v1/spreads/history
История спредов.

**Headers:** `Authorization: Bearer {token}`

**Query params:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|-------------|----------|
| symbol | string | Да | Торговая пара |
| buy_exchange | string | Да | Биржа покупки |
| sell_exchange | string | Да | Биржа продажи |
| from | ISO8601 | Да | Начало периода |
| to | ISO8601 | Да | Конец периода |
| min_net_spread | float | Нет | Минимальный net спред |

**Response 200:**
```json
{
  "data": [
    {
      "time": "2025-07-03T11:30:00Z",
      "symbol": "BTC/USDT",
      "buy_exchange": "binance",
      "sell_exchange": "bybit",
      "gross_spread_pct": 0.045,
      "net_spread_pct": -0.055
    }
  ],
  "meta": {
    "count": 1
  }
}
```

#### 6.1.4 Trades

##### GET /api/v1/trades
Список сделок (paper trading).

**Headers:** `Authorization: Bearer {token}`

**Query params:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|-------------|----------|
| symbol | string | Нет | Фильтр по паре |
| status | string | Нет | `pending`, `completed`, `failed`, `cancelled` |
| from | ISO8601 | Нет | Начало периода |
| to | ISO8601 | Нет | Конец периода |
| limit | int | Нет | Количество (default: 20, max: 100) |
| offset | int | Нет | Смещение (default: 0) |

**Response 200:**
```json
{
  "data": [
    {
      "id": "trade_1720000001",
      "opportunity_id": "opp_1720000000_binance_bybit_btcusdt",
      "symbol": "BTC/USDT",
      "buy_exchange": "binance",
      "sell_exchange": "bybit",
      "buy_price": 67432.15,
      "sell_price": 67450.30,
      "amount": 0.1,
      "buy_fee": 6.74,
      "sell_fee": 6.75,
      "withdrawal_fee": 1.00,
      "slippage_cost": 13.49,
      "gross_pnl": 1.82,
      "net_pnl": -25.16,
      "status": "completed",
      "executed_at": "2025-07-03T12:00:01Z",
      "duration_ms": 234
    }
  ],
  "meta": {
    "count": 1,
    "total": 150,
    "limit": 20,
    "offset": 0
  }
}
```

##### GET /api/v1/trades/{trade_id}
Детали конкретной сделки.

**Response 200:**
```json
{
  "id": "trade_1720000001",
  "opportunity_id": "opp_1720000000_binance_bybit_btcusdt",
  "symbol": "BTC/USDT",
  "buy_exchange": "binance",
  "sell_exchange": "bybit",
  "buy_price": 67432.15,
  "sell_price": 67450.30,
  "amount": 0.1,
  "buy_fee": 6.74,
  "sell_fee": 6.75,
  "withdrawal_fee": 1.00,
  "slippage_cost": 13.49,
  "gross_pnl": 1.82,
  "net_pnl": -25.16,
  "status": "completed",
  "executed_at": "2025-07-03T12:00:01Z",
  "duration_ms": 234,
  "breakdown": {
    "revenue": 6745.03,
    "cost": 6770.19,
    "fees_total": 27.98,
    "result": -25.16
  }
}
```

**Response 404:**
```json
{
  "detail": "Trade not found",
  "code": "TRADE_NOT_FOUND"
}
```

#### 6.1.5 Balance

##### GET /api/v1/balance
Текущий виртуальный баланс.

**Headers:** `Authorization: Bearer {token}`

**Response 200:**
```json
{
  "data": [
    {
      "exchange": "binance",
      "asset": "USDT",
      "amount": 9988.51,
      "updated_at": "2025-07-03T12:00:01Z"
    },
    {
      "exchange": "binance",
      "asset": "BTC",
      "amount": 0.6000,
      "updated_at": "2025-07-03T12:00:01Z"
    },
    {
      "exchange": "bybit",
      "asset": "USDT",
      "amount": 10013.55,
      "updated_at": "2025-07-03T12:00:01Z"
    }
  ],
  "meta": {
    "total_usdt_equivalent": 20002.06,
    "total_pnl": 2.06
  }
}
```

##### GET /api/v1/balance/history
История изменения баланса.

**Headers:** `Authorization: Bearer {token}`

**Query params:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|-------------|----------|
| exchange | string | Нет | Фильтр по бирже |
| from | ISO8601 | Да | Начало периода |
| to | ISO8601 | Да | Конец периода |

**Response 200:**
```json
{
  "data": [
    {
      "time": "2025-07-03T12:00:01Z",
      "exchange": "binance",
      "asset": "USDT",
      "amount": 9988.51,
      "change_amount": -11.49,
      "reason": "trade",
      "trade_id": "trade_1720000001"
    }
  ]
}
```

#### 6.1.6 P&L Analytics

##### GET /api/v1/analytics/pnl
Аналитика P&L.

**Headers:** `Authorization: Bearer {token}`

**Query params:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|-------------|----------|
| period | string | Нет | `1d`, `7d`, `30d`, `90d` (default: `7d`) |
| symbol | string | Нет | Фильтр по паре |

**Response 200:**
```json
{
  "data": {
    "period": "7d",
    "total_trades": 45,
    "winning_trades": 23,
    "losing_trades": 22,
    "win_rate_pct": 51.1,
    "total_gross_pnl": 125.50,
    "total_net_pnl": -45.20,
    "total_fees": 170.70,
    "avg_trade_pnl": -1.00,
    "max_win": 15.30,
    "max_loss": -18.50,
    "daily_breakdown": [
      {
        "date": "2025-07-03",
        "trades": 8,
        "gross_pnl": 22.50,
        "net_pnl": -8.30,
        "fees": 30.80
      }
    ]
  }
}
```

##### GET /api/v1/analytics/spread-stats
Статистика спредов.

**Headers:** `Authorization: Bearer {token}`

**Query params:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|-------------|----------|
| symbol | string | Да | Торговая пара |
| from | ISO8601 | Да | Начало периода |
| to | ISO8601 | Да | Конец периода |

**Response 200:**
```json
{
  "data": {
    "symbol": "BTC/USDT",
    "period": "7d",
    "avg_gross_spread_pct": 0.032,
    "max_gross_spread_pct": 0.450,
    "avg_net_spread_pct": -0.068,
    "max_net_spread_pct": 0.350,
    "positive_spread_count": 123,
    "total_opportunities": 4520,
    "by_exchange_pair": [
      {
        "buy_exchange": "binance",
        "sell_exchange": "bybit",
        "avg_spread_pct": 0.028,
        "max_spread_pct": 0.380,
        "opportunity_count": 2150
      }
    ]
  }
}
```

#### 6.1.7 Settings

##### GET /api/v1/settings
Текущие настройки системы.

**Headers:** `Authorization: Bearer {token}`

**Response 200:**
```json
{
  "data": {
    "min_spread_pct": 0.30,
    "max_position_pct": 10.0,
    "slippage_tolerance_pct": 0.20,
    "execution_timeout_sec": 2,
    "kill_switch": false,
    "notification_spread_threshold": 0.50,
    "daily_loss_limit_pct": 5.0
  }
}
```

##### PUT /api/v1/settings
Обновление настроек.

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "min_spread_pct": 0.50,
  "max_position_pct": 15.0
}
```

**Response 200:**
```json
{
  "data": {
    "min_spread_pct": 0.50,
    "max_position_pct": 15.0,
    "slippage_tolerance_pct": 0.20,
    "execution_timeout_sec": 2,
    "kill_switch": false,
    "notification_spread_threshold": 0.50,
    "daily_loss_limit_pct": 5.0
  }
}
```

**Response 400:**
```json
{
  "detail": "min_spread_pct must be between 0.01 and 10.0",
  "code": "INVALID_VALUE"
}
```

#### 6.1.8 Kill Switch

##### POST /api/v1/killswitch
Аварийная остановка торговли.

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "reason": "Manual emergency stop",
  "confirm": true
}
```

**Response 200:**
```json
{
  "status": "activated",
  "activated_at": "2025-07-03T12:00:00Z",
  "reason": "Manual emergency stop",
  "affected_services": ["executor", "scanner"]
}
```

##### DELETE /api/v1/killswitch
Снятие аварийной остановки.

**Headers:** `Authorization: Bearer {token}`

**Response 200:**
```json
{
  "status": "deactivated",
  "deactivated_at": "2025-07-03T12:05:00Z"
}
```

#### 6.1.9 System Health

##### GET /health
Health check (public, no auth).

**Response 200:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-07-03T12:00:00Z",
  "checks": {
    "redis": "ok",
    "timescaledb": "ok",
    "collector_ws": 7
  },
  "uptime_seconds": 86400
}
```

**Response 503:**
```json
{
  "status": "unhealthy",
  "checks": {
    "redis": "fail",
    "timescaledb": "ok",
    "collector_ws": 3
  }
}
```

##### GET /api/v1/system/status
Статус всех компонентов системы.

**Headers:** `Authorization: Bearer {token}`

**Response 200:**
```json
{
  "services": {
    "collector": {
      "status": "running",
      "ws_connections": 14,
      "exchanges": {
        "binance": "connected",
        "bybit": "connected",
        "kucoin": "connected",
        "gateio": "connected",
        "bitget": "reconnecting",
        "coinex": "connected",
        "bingx": "connected"
      }
    },
    "scanner": {
      "status": "running",
      "last_scan_ms": 12,
      "pairs_scanned": 8,
      "opportunities_today": 452
    },
    "executor": {
      "status": "running",
      "trades_today": 8,
      "pnl_today": -8.30,
      "kill_switch": false
    },
    "notifier": {
      "status": "running",
      "messages_sent_today": 460
    }
  }
}
```

#### 6.1.10 Pairs Management

##### GET /api/v1/pairs
Список отслеживаемых пар.

**Headers:** `Authorization: Bearer {token}`

**Response 200:**
```json
{
  "data": [
    {
      "symbol": "BTC/USDT",
      "exchange": "binance",
      "is_active": true,
      "priority": 1,
      "min_spread_override": null
    },
    {
      "symbol": "ETH/USDT",
      "exchange": "binance",
      "is_active": true,
      "priority": 1,
      "min_spread_override": null
    }
  ]
}
```

##### PUT /api/v1/pairs/{symbol}/{exchange}
Активация/деактивация пары.

**Headers:** `Authorization: Bearer {token}`

**Request:**
```json
{
  "is_active": false
}
```

**Response 200:**
```json
{
  "symbol": "BTC/USDT",
  "exchange": "binance",
  "is_active": false,
  "priority": 1
}
```

### 6.2. WebSocket channels (полный список)

#### WebSocket Endpoint: `wss://api.example.com/ws`

**Аутентификация:** Query parameter `?token={jwt_token}`

#### 6.2.1 Client → Server Messages

##### Subscribe
Подписка на канал.

```json
{
  "type": "subscribe",
  "channel": "prices",
  "filter": {
    "symbol": "BTC/USDT",
    "exchange": "binance"
  }
}
```

**Channels:** `prices`, `spreads`, `trades`, `balance`

##### Unsubscribe
Отписка от канала.

```json
{
  "type": "unsubscribe",
  "channel": "prices"
}
```

##### Ping
Heartbeat (каждые 30 секунд).

```json
{
  "type": "ping",
  "timestamp": 1720000000000
}
```

#### 6.2.2 Server → Client Messages

##### Prices Update
Real-time обновление цен.

```json
{
  "type": "prices",
  "data": {
    "exchange": "binance",
    "symbol": "BTC/USDT",
    "bid": 67432.15,
    "ask": 67433.80,
    "bid_volume": 1.234,
    "ask_volume": 0.987,
    "timestamp": "2025-07-03T12:00:00.015Z",
    "latency_ms": 15
  }
}
```

**Rate:** ~1-10 обновлений/сек на пару (throttled на frontend: 100ms)

##### Spreads Update
Обнаруженные спреды.

```json
{
  "type": "spreads",
  "data": {
    "symbol": "BTC/USDT",
    "buy_exchange": "binance",
    "sell_exchange": "bybit",
    "buy_price": 67432.15,
    "sell_price": 67450.30,
    "gross_spread_pct": 0.027,
    "net_spread_pct": -0.073,
    "detected_at": "2025-07-03T12:00:00Z"
  }
}
```

**Rate:** По мере обнаружения (dedup 5 сек)

##### Trade Update
Завершённая сделка.

```json
{
  "type": "trades",
  "data": {
    "id": "trade_1720000001",
    "symbol": "BTC/USDT",
    "buy_exchange": "binance",
    "sell_exchange": "bybit",
    "amount": 0.1,
    "net_pnl": -25.16,
    "status": "completed",
    "executed_at": "2025-07-03T12:00:01Z"
  }
}
```

**Rate:** По мере исполнения

##### Balance Update
Изменение баланса.

```json
{
  "type": "balance",
  "data": {
    "exchange": "binance",
    "asset": "USDT",
    "amount": 9988.51,
    "change": -11.49,
    "reason": "trade"
  }
}
```

##### Pong
Ответ на heartbeat.

```json
{
  "type": "pong",
  "timestamp": 1720000000000,
  "server_time": 1720000000005
}
```

##### Error
Ошибка.

```json
{
  "type": "error",
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "Too many messages. Limit: 10/sec",
  "retry_after_ms": 1000
}
```

### 6.3. Форматы запросов/ответов (JSON схемы)

#### 6.3.1 PriceTick (Pydantic model)

```python
class PriceTick(BaseModel):
    exchange: str = Field(..., min_length=2, max_length=20)
    symbol: str = Field(..., pattern=r'^[A-Z]+/[A-Z]+$')
    bid: Decimal = Field(..., gt=0, decimal_places=8)
    ask: Decimal = Field(..., gt=0, decimal_places=8)
    bid_volume: Optional[Decimal] = Field(None, ge=0)
    ask_volume: Optional[Decimal] = Field(None, ge=0)
    timestamp: int = Field(..., description="Unix timestamp in ms")
    received_at: int = Field(..., description="Unix timestamp in ms")
    latency_ms: Optional[int] = Field(None, ge=0)
```

#### 6.3.2 Opportunity (Pydantic model)

```python
class Opportunity(BaseModel):
    id: str = Field(..., min_length=10)
    symbol: str = Field(..., pattern=r'^[A-Z]+/[A-Z]+$')
    buy_exchange: str = Field(..., min_length=2)
    sell_exchange: str = Field(..., min_length=2)
    buy_price: Decimal = Field(..., gt=0)
    sell_price: Decimal = Field(..., gt=0)
    gross_spread_pct: Decimal = Field(...)
    buy_fee_pct: Decimal = Field(..., ge=0)
    sell_fee_pct: Decimal = Field(..., ge=0)
    withdrawal_fee_usd: Optional[Decimal] = Field(None, ge=0)
    net_spread_pct: Decimal = Field(...)
    detected_at: int = Field(..., description="Unix timestamp in ms")
```

#### 6.3.3 Trade (Pydantic model)

```python
class Trade(BaseModel):
    id: str = Field(..., min_length=5)
    opportunity_id: str = Field(..., min_length=10)
    symbol: str = Field(..., pattern=r'^[A-Z]+/[A-Z]+$')
    buy_exchange: str = Field(..., min_length=2)
    sell_exchange: str = Field(..., min_length=2)
    buy_price: Decimal = Field(..., gt=0)
    sell_price: Decimal = Field(..., gt=0)
    amount: Decimal = Field(..., gt=0)
    buy_fee: Decimal = Field(default=0, ge=0)
    sell_fee: Decimal = Field(default=0, ge=0)
    withdrawal_fee: Decimal = Field(default=0, ge=0)
    slippage_cost: Decimal = Field(default=0, ge=0)
    gross_pnl: Decimal = Field(...)
    net_pnl: Decimal = Field(...)
    status: Literal["pending", "completed", "failed", "cancelled"]
    executed_at: Optional[int] = Field(None, description="Unix timestamp in ms")
    duration_ms: Optional[int] = Field(None, ge=0)
```

#### 6.3.4 Settings (Pydantic model)

```python
class SettingsUpdate(BaseModel):
    min_spread_pct: Optional[float] = Field(None, ge=0.01, le=10.0)
    max_position_pct: Optional[float] = Field(None, ge=1.0, le=100.0)
    slippage_tolerance_pct: Optional[float] = Field(None, ge=0.01, le=5.0)
    execution_timeout_sec: Optional[int] = Field(None, ge=1, le=30)
    notification_spread_threshold: Optional[float] = Field(None, ge=0.01, le=10.0)
    daily_loss_limit_pct: Optional[float] = Field(None, ge=0.1, le=50.0)
```

### 6.4. Аутентификация (JWT)

#### 6.4.1 JWT Token Structure

**Header:**
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

**Payload:**
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "is_admin": false,
  "iat": 1720000000,
  "exp": 1720086400,
  "jti": "unique-token-id"
}
```

**Claims:**
| Claim | Описание |
|-------|----------|
| `sub` | UUID пользователя |
| `email` | Email пользователя |
| `is_admin` | Флаг администратора |
| `iat` | Время создания (unix timestamp) |
| `exp` | Время истечения (iat + 24h) |
| `jti` | Уникальный ID токена (для revocation) |

#### 6.4.2 Refresh Token

| Параметр | Значение |
|----------|----------|
| Expiry | 7 дней |
| Storage | HTTP-only cookie + Secure |
| Rotation | Новый refresh token при каждом обновлении |
| Revocation | Blacklist в Redis (`blacklist:{jti}`) |

#### 6.4.3 Middleware Flow

```
Request → Extract Authorization header → Validate JWT signature
   → Check expiry → Check blacklist (Redis)
   → Attach user to request.state.user
   → Proceed to handler OR 401 Unauthorized
```

### 6.5. Rate limiting

#### 6.5.1 REST API Limits

| Тип | Лимит | Window | HTTP Header |
|-----|-------|--------|-------------|
| Anonymous | 10 req/min | 60s | X-RateLimit-* |
| Authenticated | 100 req/min | 60s | X-RateLimit-* |
| Admin | 300 req/min | 60s | X-RateLimit-* |

**Response headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1720000060
```

**Response 429:**
```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 45,
  "limit": 100,
  "window": 60
}
```

#### 6.5.2 WebSocket Limits

| Тип | Лимит | Window | Действие |
|-----|-------|--------|----------|
| Messages | 10 msg/sec | 1s | Disconnect с кодом 1008 |
| Connections | 5 per IP | - | Reject новых |
| Subscriptions | 20 channels | - | Error на превышение |

#### 6.5.3 Implementation

Redis-based sliding window counter:

```python
# Key: ratelimit:{endpoint}:{user_id}
# Value: sorted set of timestamps
ZADD ratelimit:api:user_123 {now_ms} {now_ms}
ZREMRANGEBYSCORE ratelimit:api:user_123 0 {now_ms - window_ms}
ZCARD ratelimit:api:user_123  # current count
EXPIRE ratelimit:api:user_123 {window_seconds}
```


---

## 7. План разработки

### 7.1. Фазы разработки (16 фаз)

| Фаза | Название | Длительность | Задачи | Деливери |
|------|----------|-------------|--------|----------|
| **F1** | **Проектирование** | Неделя 1 | - Финализация ТЗ  <br>- Проектирование схемы БД  <br>- Определение API контрактов  <br>- Настройка репозитория, CI/CD базовый | TZ_ARCHITECTURE.md, DB schema, API spec |
| **F2** | **Инфраструктура** | Неделя 1 | - Docker Compose: TimescaleDB, Redis, Prometheus, Grafana  <br>- Сетевые алиасы, health checks  <br>- Базовый мониторинг | docker-compose.yml, Grafana dashboards |
| **F3** | **Shared library** | Неделя 1-2 | - Pydantic модели (PriceTick, Opportunity, Trade)  <br>- Redis client wrapper  <br>- Config management (Pydantic Settings)  <br>- Logging (structlog)  <br>- Prometheus metrics helpers | `shared/` package |
| **F4** | **Collector: scaffold** | Неделя 2 | - FastAPI skeleton + health endpoint  <br>- CCXT Pro подключение к 1 бирже (Binance)  <br>- WebSocket subscribe/unsubscribe  <br>- Публикация в Redis `prices` | Collector запущен, цены в Redis |
| **F5** | **Collector: 7 бирж** | Неделя 2-3 | - Подключение всех 7 бирж  <br>- Rate limiting per exchange  <br>- Auto-reconnect с exponential backoff  <br>- Graceful shutdown  <br>- Метрики Prometheus | 7 WS соединений, метрики в Grafana |
| **F6** | **TimescaleDB setup** | Неделя 3 | - Создание hypertables (prices, opportunities, trades, balance)  <br>- Миграции Alembic  <br>- Continuous aggregates (hourly prices, daily P&L)  <br>- Retention + compression policies | БД готова, миграции работают |
| **F7** | **Scanner** | Неделя 3-4 | - Чтение `prices` stream (consumer group)  <br>- Расчёт спредов для всех комбинаций  <br>- Учёт комиссий (net spread)  <br>- Фильтрация по min_spread  <br>- Дедупликация  <br>- Публикация в `opportunities` stream  <br>- Сохранение в TimescaleDB | Спреды считаются, opportunities в Redis |
| **F8** | **Executor (Paper Trading)** | Неделя 4-5 | - Чтение `opportunities` stream  <br>- Симуляция buy/sell ордеров  <br>- Slippage simulation  <br>- P&L calculation  <br>- Обновление виртуального баланса  <br>- Запись в `trades` hypertable  <br>- Публикация в `trades` stream | Paper trades исполняются, P&L считается |
| **F9** | **API Gateway: REST** | Неделя 5-6 | - FastAPI + JWT auth  <br>- Endpoints: prices, spreads, trades, balance, analytics  <br>- Rate limiting  <br>- CORS  <br>- OpenAPI docs  <br>- Request logging | REST API полностью функционален |
| **F10** | **API Gateway: WebSocket** | Неделя 6 | - WS endpoint `/ws`  <br>- Subscribe/unsubscribe channels  <br>- Broadcast цен и спредов  <br>- Heartbeat (ping/pong)  <br>- Reconnection handling | Real-time WS работает |
| **F11** | **Notifier (Telegram)** | Неделя 6-7 | - aiogram 3.x бот  <br>- Чтение streams  <br>- Форматирование сообщений  <br>- Rate limiting + очередь  <br>- Команды: /start, /status, /balance, /trades, /killswitch | Telegram alerts работают |
| **F12** | **React Dashboard** | Неделя 7-8 | - Vite + React 19 + TypeScript setup  <br>- Tailwind + shadcn/ui  <br>- Pages: Dashboard, Trades, Analytics, Settings  <br>- Zustand store  <br>- WebSocket client  <br>- Recharts графики  <br>- Responsive design | Dashboard функционален |
| **F13** | **Integration testing** | Неделя 8-9 | - End-to-end pipeline: биржа -> collector -> scanner -> executor -> БД  <br>- Latency benchmarks  <br>- Load testing (k6)  <br>- Bug fixes | Система работает E2E |
| **F14** | **Наблюдаемость** | Неделя 9 | - Prometheus metrics всех сервисов  <br>- Grafana dashboards (system + business)  <br>- Alert rules  <br>- Structured logging  <br>- Health checks | Полная observability |
| **F15** | **Security hardening** | Неделя 9-10 | - JWT security review  <br>- Input validation audit  <br>- Secret management  <br>- CORS/CSRF review  <br>- Kill switch testing | Security review passed |
| **F16** | **Deploy + Launch** | Неделя 10 | - Production Docker Compose  <br>- SSL/certificates  <br>- Backup strategy  <br>- Runbook  <br>- Team onboarding docs | MVP запущен |

### 7.2. Оценка сроков

| Этап | Недели | Дата (старт: 1 июля 2025) |
|------|--------|--------------------------|
| F1-F3: Фундамент | 2 недели | 1-14 июля |
| F4-F8: Core backend | 4 недели | 14 июля - 11 августа |
| F9-F12: API + Frontend | 4 недели | 11 августа - 8 сентября |
| F13-F16: QA + Launch | 3 недели | 8-29 сентября |
| **Итого MVP** | **~10-12 недель** | **Запуск: конец сентября 2025** |

**Buffer:** +2 недели на непредвиденные риски = **середина октября 2025**

### 7.3. Ресурсы

| Роль | Кол-во | Занятость | Начало |
|------|--------|----------|--------|
| Backend Lead (Python/FastAPI) | 1 | 100% | F1 |
| Backend Developer (Python) | 1 | 100% | F3 |
| Frontend Developer (React/TS) | 1 | 100% | F12 (или part-time с F9) |
| DevOps/Infra | 0.5 (совмещение) | 50% | F2 |
| QA Engineer | 0.5 (совмещение) | 50% | F13 |
| Product Owner | 0.25 | 25% | F1 |

---

## 8. Тестирование

### 8.1. Unit тесты

| Компонент | Фреймворк | Покрытие | Что тестировать |
|-----------|-----------|----------|----------------|
| Scanner | pytest + pytest-asyncio | >= 80% | Расчёт спредов, фильтрация, дедупликация |
| Executor | pytest + pytest-asyncio | >= 80% | P&L calculation, slippage sim, balance update |
| API Gateway | pytest + HTTPX | >= 70% | Endpoints, validation, auth middleware |
| Shared models | pytest | >= 90% | Pydantic validation, serialization |
| Notifier | pytest + pytest-asyncio | >= 70% | Message formatting, rate limiting |

**Пример unit test (scanner):**

```python
# tests/test_scanner.py
import pytest
from decimal import Decimal
from scanner.spread_calculator import calculate_spread

@pytest.mark.parametrize("buy_price,sell_price,expected_gross", [
    (Decimal("100.0"), Decimal("100.5"), Decimal("0.5")),
    (Decimal("67432.15"), Decimal("67450.30"), Decimal("0.027")),
])
def test_calculate_gross_spread(buy_price, sell_price, expected_gross):
    result = calculate_spread(buy_price, sell_price)
    assert result["gross_spread_pct"] == expected_gross

def test_net_spread_with_fees():
    result = calculate_spread(
        buy_price=Decimal("100.0"),
        sell_price=Decimal("100.5"),
        buy_fee_pct=Decimal("0.1"),
        sell_fee_pct=Decimal("0.1"),
        withdrawal_fee=Decimal("1.0"),
        trade_volume=Decimal("1000.0")
    )
    # net = gross - buy_fee - sell_fee - withdrawal/trade_volume
    assert result["net_spread_pct"] < result["gross_spread_pct"]

def test_deduplication():
    """Same opportunity within 5 seconds should be deduplicated."""
    opp1 = create_opportunity("BTC/USDT", "binance", "bybit")
    opp2 = create_opportunity("BTC/USDT", "binance", "bybit")
    assert is_duplicate(opp2, [opp1], ttl_seconds=5) is True
```

### 8.2. Integration тесты

| Сценарий | Что проверяется | Инструмент |
|----------|----------------|------------|
| Collector -> Redis | WS сообщение появляется в Redis stream | pytest + Redis container |
| Redis -> Scanner -> Redis | Price в stream -> opportunity в stream | pytest + testcontainers |
| Scanner -> TimescaleDB | Opportunity сохраняется в БД | pytest + TimescaleDB container |
| Executor -> TimescaleDB | Trade сохраняется, баланс обновляется | pytest + TimescaleDB container |
| API Gateway -> TimescaleDB | REST endpoint возвращает данные из БД | pytest + HTTPX |
| API Gateway -> Redis | WS subscription получает real-time данные | pytest + websockets |
| Full pipeline | End-to-end: биржа-эмулятор -> все сервисы -> БД | Docker Compose test profile |

**Testcontainers setup:**

```python
# tests/conftest.py
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest_asyncio.fixture(scope="session")
async def postgres():
    with PostgresContainer("timescale/timescaledb:latest-pg16") as pg:
        yield pg.get_connection_url()

@pytest_asyncio.fixture(scope="session")
async def redis():
    with RedisContainer("redis:7.2") as redis:
        yield redis.get_connection_url()
```

### 8.3. Stress тесты

| Сценарий | Нагрузка | Целевая метрика | Инструмент |
|----------|----------|----------------|------------|
| Redis Streams ingestion | 100K msg/sec | Zero message loss | redis-benchmark + custom script |
| REST API throughput | 35K req/sec | p99 < 50ms | k6 / wrk |
| WebSocket broadcast | 1000 concurrent clients | Latency < 100ms | k6 WS + custom |
| TimescaleDB write | 100K rows/sec INSERT | No timeouts | pgbench + custom |
| TimescaleDB read | 1000 queries/sec | p99 < 100ms | pgbench |
| Full system | 7 бирж x 4 пары x 10 ticks/sec | End-to-end < 100ms | Custom Python loader |

**k6 скрипт для REST API:**

```javascript
// tests/load/k6_rest.js
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "1m", target: 100 },   // Ramp up
    { duration: "3m", target: 500 },   // Steady state
    { duration: "1m", target: 1000 },  // Peak
    { duration: "1m", target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ["p(99)<50"],   // p99 < 50ms
    http_req_failed: ["rate<0.01"],    // Error rate < 1%
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const TOKEN = __ENV.API_TOKEN;

export default function () {
  const res = http.get(`${BASE_URL}/api/v1/prices/latest`, {
    headers: { "Authorization": `Bearer ${TOKEN}` },
  });
  check(res, {
    "status is 200": (r) => r.status === 200,
    "response time < 50ms": (r) => r.timings.duration < 50,
  });
  sleep(0.1);
}
```

### 8.4. Критерии приёмки

| # | Критерий | Как проверить | Минимальный результат |
|---|----------|--------------|----------------------|
| 1 | Все 7 бирж подключены | Grafana dashboard: 7 WS connections | 7 зелёных индикатора |
| 2 | Цены обновляются real-time | WebSocket + Dashboard | Задержка < 100ms |
| 3 | Спреды обнаруживаются | Scanner metrics + Telegram | > 100 opportunities/день |
| 4 | Paper trading работает | Trades table + P&L | Сделки записываются, P&L корректен |
| 5 | Dashboard отображает данные | Ручное тестирование | Все 4 страницы функциональны |
| 6 | Telegram уведомления | Отправка тестовых сообщений | Сообщения доставляются < 5s |
| 7 | Kill switch работает | Активация + проверка остановки | Executor останавливается < 1s |
| 8 | API проходит load test | k6: 1000 req/sec | p99 < 50ms, error rate < 0.1% |
| 9 | Graceful shutdown | SIGTERM всех сервисов | Нет потери данных, чистый exit |
| 10 | Мониторинг работает | Grafana dashboards | Все метрики отображаются |
| 11 | Аутентификация работает | Попытки доступа без токена | 401 Unauthorized |
| 12 | Data retention работает | Проверка через 30+1 дней | Старые prices удалены |

---

## 9. Безопасность

### 9.1. Хранение API ключей

| Аспект | Требование |
|--------|-----------|
| Шифрование | AES-256-GCM для API ключей бирж в БД |
| Key storage | Master key в environment variable (не в БД) |
| Access | Только executor сервис имеет доступ к ключам |
| Rotation | Поддержка ротации без downtime |
| Logging | API keys НИКОГДА не логируются (маскирование: `ak_****xxxx`) |

**Маскирование в логах:**
```python
def mask_api_key(key: str) -> str:
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}****{key[-4:]}"
```

### 9.2. Аутентификация и авторизация

| Аспект | Реализация |
|--------|-----------|
| Auth method | JWT (HS256) |
| Token lifetime | Access: 24h, Refresh: 7 дней |
| Password requirements | Минимум 8 символов, 1 заглавная, 1 цифра, 1 спецсимвол |
| Password hashing | bcrypt с cost factor 12 |
| Brute force protection | 5 попыток -> блокировка 15 минут (Redis counter) |
| Session management | Multi-device, revoke by refresh token blacklist |
| Roles | `user` (read-only), `admin` (full access) |

### 9.3. Шифрование

| Уровень | Метод | Применение |
|---------|-------|-----------|
| Transport | TLS 1.3 | Все внешние соединения (HTTPS, WSS) |
| Database | AES-256-GCM | API keys бирж, sensitive settings |
| Redis | Нет (trusted network) | Только prices/opportunities (не sensitive) |
| Environment | Docker secrets | Пароли, ключи (не в plain text) |
| Backup | AES-256 | Шифрованные бэкапы БД |

### 9.4. Audit log

| Поле | Описание | Пример |
|------|----------|--------|
| `time` | Время действия | `2025-07-03T12:00:00Z` |
| `user_id` | UUID пользователя | `550e8400-e29b-41d4-a716-446655440000` |
| `action` | Действие | `killswitch_activated`, `settings_changed`, `login` |
| `resource` | Ресурс | `system`, `settings`, `user` |
| `old_value` | Старое значение (JSON) | `{"min_spread_pct": 0.30}` |
| `new_value` | Новое значение (JSON) | `{"min_spread_pct": 0.50}` |
| `ip_address` | IP адрес | `192.168.1.1` |
| `user_agent` | User-Agent | `Mozilla/5.0...` |

**Critical events для audit log:**
- Login / Logout / Failed login
- Kill switch activate/deactivate
- Settings change
- User creation/deletion
- Password change
- API key operations

### 9.5. Защита от угроз

| Угроза | Защита |
|--------|--------|
| DDoS на API | Rate limiting + CloudFlare (post-MVP) |
| WS connection flood | Max 5 connections per IP |
| SQL Injection | SQLAlchemy parameterized queries |
| XSS | No user-generated HTML, CSP headers |
| CSRF | CORS strict origin, CSRF tokens for mutations |
| Man-in-the-middle | TLS 1.3 + certificate pinning (post-MVP) |
| Internal network sniffing | Docker network isolation, no host networking |
| Container escape | Non-root user, read-only filesystem, limited capabilities |
| Secret leakage | .env not in Docker image, git pre-commit hooks |
| Dependency vulnerability | `pip-audit` в CI, Dependabot alerts |

---

## 10. Документация

### 10.1. API документация

| Источник | URL | Описание |
|----------|-----|----------|
| OpenAPI (Swagger UI) | `http://localhost:8000/docs` | Интерактивная документация |
| OpenAPI (ReDoc) | `http://localhost:8000/redoc` | Альтернативный формат |
| OpenAPI JSON | `http://localhost:8000/openapi.json` | Машиночитаемая схема |

**FastAPI автоматически генерирует документацию из Pydantic моделей.**

### 10.2. Runbook

| Сценарий | Команды / Действия |
|----------|-------------------|
| **Проверка статуса** | `docker compose ps` -> проверить все сервисы `healthy` |
| **Просмотр логов** | `docker compose logs -f {service}` (collector/scanner/executor/api-gateway/notifier) |
| **Рестарт сервиса** | `docker compose restart {service}` |
| **Проверка Redis** | `docker compose exec redis redis-cli INFO streams` |
| **Проверка БД** | `docker compose exec timescaledb psql -U arbitrage -c "SELECT count(*) FROM trades;"` |
| **Kill switch** | `curl -X POST http://localhost:8000/api/v1/killswitch -H "Authorization: Bearer {token}" -d '{"confirm":true}'` |
| **Backup БД** | `docker compose exec timescaledb pg_dump -U arbitrage arbitrage > backup_$(date +%Y%m%d).sql` |
| **Restore БД** | `docker compose exec -T timescaledb psql -U arbitrage < backup_YYYYMMDD.sql` |
| **Grafana** | `http://localhost:3000` (admin/admin) |
| **Prometheus** | `http://localhost:9090` |
| **Масштабирование collector** | `docker compose up -d --scale collector=2` |

### 10.3. Переменные окружения (.env пример)

```bash
# ============================================
# КОНФИГУРАЦИЯ ОБЩАЯ
# ============================================
# Режим: development | production
ENVIRONMENT=development

# Версия приложения
VERSION=1.0.0

# Логирование: DEBUG | INFO | WARNING | ERROR
LOG_LEVEL=INFO

# ============================================
# TIMESCALEDB
# ============================================
# Хост БД (Docker service name)
TIMESCALEDB_HOST=timescaledb

# Порт PostgreSQL
TIMESCALEDB_PORT=5432

# Имя базы данных
TIMESCALEDB_DATABASE=arbitrage

# Пользователь
TIMESCALEDB_USER=arbitrage

# Пароль (обязательно изменить в production!)
TIMESCALEDB_PASSWORD=change_me_in_production_123

# Размер пула соединений
TIMESCALEDB_POOL_SIZE=20

# ============================================
# REDIS
# ============================================
# Хост Redis
REDIS_HOST=redis

# Порт Redis
REDIS_PORT=6379

# Пароль Redis (опционально, оставить пустым если нет)
REDIS_PASSWORD=

# Номер базы данных (0-15)
REDIS_DB=0

# ============================================
# SECURITY
# ============================================
# Секретный ключ для JWT (минимум 32 байта, base64)
# Генерация: openssl rand -hex 32
JWT_SECRET_KEY=your_super_secret_key_change_this_in_production_32bytes_min

# Алгоритм JWT
JWT_ALGORITHM=HS256

# Время жизни access token (в минутах)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Время жизни refresh token (в днях)
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Мастер-ключ для шифрования API ключей бирж
# Генерация: openssl rand -hex 32
ENCRYPTION_KEY=your_encryption_key_32_bytes_hex

# ============================================
# API GATEWAY
# ============================================
# Хост для binding
API_GATEWAY_HOST=0.0.0.0

# Порт API Gateway
API_GATEWAY_PORT=8000

# CORS origins (через запятую)
# Production: https://yourdomain.com
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Rate limit: запросов в минуту (аутентифицированный пользователь)
RATE_LIMIT_PER_MINUTE=100

# ============================================
# COLLECTOR
# ============================================
# Хост для binding
COLLECTOR_HOST=0.0.0.0

# Порт Collector
COLLECTOR_PORT=8001

# Список бирж (через запятую)
EXCHANGES=binance,bybit,kucoin,gateio,bitget,coinex,bingx

# Список пар (через запятую)
TRADING_PAIRS=BTC/USDT,ETH/USDT

# Maxlen для Redis stream prices (backpressure)
PRICES_STREAM_MAXLEN=100000

# ============================================
# SCANNER
# ============================================
# Хост для binding
SCANNER_HOST=0.0.0.0

# Порт Scanner
SCANNER_PORT=8002

# Минимальный спред для триггера (%)
MIN_SPREAD_PCT=0.30

# Дедупликация: TTL в секундах
OPPORTUNITY_DEDUP_TTL_SECONDS=5

# ============================================
# EXECUTOR
# ============================================
# Хост для binding
EXECUTOR_HOST=0.0.0.0

# Порт Executor
EXECUTOR_PORT=8003

# Максимальный % баланса на сделку
MAX_POSITION_PCT=10.0

# Slippage tolerance (%)
SLIPPAGE_TOLERANCE_PCT=0.20

# Таймаут исполнения (секунды)
EXECUTION_TIMEOUT_SEC=2

# Дневной лимит убытков (%)
DAILY_LOSS_LIMIT_PCT=5.0

# ============================================
# NOTIFIER (TELEGRAM)
# ============================================
# Хост для binding
NOTIFIER_HOST=0.0.0.0

# Порт Notifier
NOTIFIER_PORT=8004

# Token Telegram бота (от @BotFather)
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather

# Chat ID для уведомлений (получить через @userinfobot)
TELEGRAM_CHAT_ID=your_chat_id

# Минимальный спред для Telegram уведомлений (%)
NOTIFICATION_SPREAD_THRESHOLD_PCT=0.50

# Max сообщений в секунду (лимит Telegram API)
TELEGRAM_RATE_LIMIT_MSG_PER_SEC=20

# ============================================
# EXCHANGE API KEYS (опционально для MVP — paper trading)
# ============================================
# Примечание: Для paper trading API keys НЕ требуются.
# Для production trading добавить:
# BINANCE_API_KEY=xxx
# BINANCE_API_SECRET=xxx
# BYBIT_API_KEY=xxx
# BYBIT_API_SECRET=xxx
# ... и т.д. для всех бирж

# ============================================
# MONITORING
# ============================================
# Порт Prometheus
PROMETHEUS_PORT=9090

# Порт Grafana
GRAFANA_PORT=3000

# Пароль Grafana admin
GRAFANA_ADMIN_PASSWORD=admin_change_me

# Retention метрик Prometheus (дней)
PROMETHEUS_RETENTION_DAYS=15

# ============================================
# DOCKER COMPOSE
# ============================================
# Профиль: dev | prod
COMPOSE_PROFILE=dev

# Ресурсы (production значения)
COLLECTOR_MEMORY_LIMIT=1G
COLLECTOR_CPU_LIMIT=1.5
SCANNER_MEMORY_LIMIT=512M
SCANNER_CPU_LIMIT=1.0
API_GATEWAY_MEMORY_LIMIT=512M
API_GATEWAY_CPU_LIMIT=1.0
EXECUTOR_MEMORY_LIMIT=512M
EXECUTOR_CPU_LIMIT=1.0
NOTIFIER_MEMORY_LIMIT=256M
NOTIFIER_CPU_LIMIT=0.5
```

---

## Приложения

### Appendix A: Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd crypto-arbitrage

# 2. Скопировать .env
cp .env.example .env
# Отредактировать .env — указать свои значения

# 3. Запустить инфраструктуру
docker compose up -d timescaledb redis prometheus grafana

# 4. Применить миграции
docker compose run --rm api-gateway alembic upgrade head

# 5. Запустить все сервисы
docker compose up -d

# 6. Проверить статус
docker compose ps

# 7. Открыть дашборд
open http://localhost:5173

# 8. Открыть API docs
open http://localhost:8000/docs

# 9. Открыть Grafana
open http://localhost:3000
```

### Appendix B: Полезные команды

```bash
# Пересборка одного сервиса
docker compose build --no-cache collector
docker compose up -d collector

# Масштабирование
docker compose up -d --scale collector=2

# Логи в реальном времени
docker compose logs -f --tail=100

# Очистка Redis
docker compose exec redis redis-cli FLUSHDB

# Бэкап БД
docker compose exec timescaledb pg_dump -U arbitrage arbitrage > backup.sql

# Подключение к БД
docker compose exec timescaledb psql -U arbitrage -d arbitrage

# Подключение к Redis
docker compose exec redis redis-cli

# Проверка метрик
curl http://localhost:8000/metrics
curl http://localhost:8001/metrics
curl http://localhost:8002/metrics

# Health checks
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
```

### Appendix C: Порты всех сервисов

| Сервис | Порт | Назначение |
|--------|------|------------|
| api-gateway | 8000 | REST API + WebSocket |
| collector | 8001 | WS -> Redis Streams |
| scanner | 8002 | Price scan -> Opportunities |
| executor | 8003 | Paper trading |
| notifier | 8004 | Telegram alerts |
| timescaledb | 5432 | PostgreSQL/TimescaleDB |
| redis | 6379 | Redis Streams + Cache |
| prometheus | 9090 | Metrics collection |
| grafana | 3000 | Dashboards |
| frontend (dev) | 5173 | Vite dev server |
| frontend (prod) | 80 | Nginx static |

---

*Документ подготовлен на основе исследований рынка (research_arbitrage.md) и технологического исследования (research_tech.md). Версия 1.0, Июль 2025.*
