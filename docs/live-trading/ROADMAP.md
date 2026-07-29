# Дорожная карта перехода на реальную торговлю (этапы 1–6)

Источник: аудит готовности от 28.07.2026 (54 верифицированных вывода; этап 0 —
«гигиена и сейфти» — выполнен). Этот файл — **единственный источник контекста**
для агентов workflow `live-trading-rollout`: агент этапа читает свой раздел,
«Общее для агентов», CLAUDE.md и отчёты `docs/live-trading/stage-*-report.md`
предыдущих этапов. Никакого другого контекста у агента нет.

## Ключевые решения (зафиксированы пользователем)

- **Модель капитала — хеджированная инвентарная, ребаланс РУЧНОЙ.** На каждой
  бирже предразмещён фиксированный капитал (~$300). При падении баланса биржи
  ниже порога `min_exchange_balance_usd` (~$80, живая настройка) торговля с
  участием этой биржи (обе ноги) останавливается и ждёт ручного пополнения.
  Автоперевод из executor/rebalance.py на реале не используется.
- **Площадка — Linux VPS**, путь до бирж без потребительского VPN.
- **Первый реальный запуск — 3-4 биржи, топ-10 пар** (не все 7×37).
- Комиссии в shared/config.py сверены с биржами в июле 2026.

## Общее для агентов

1. Прочитай CLAUDE.md, этот файл (свой раздел + конвенции), все
   `docs/live-trading/stage-*-report.md`.
2. Загрузи указанные для этапа скилы (инструмент Skill); недоступный скил —
   пропусти молча.
3. Тесты пиши вместе с кодом: stdlib unittest, запуск внутри контейнеров
   (`bash tests/run-tests.sh`); для executor-логики — паттерн заглушки Redis из
   tests/test_paper_trading.py. Новые сьюты добавляй в tests/run-tests.sh.
4. Схема БД: init-db.sql выполняется только на свежем томе; для живой БД —
   новый re-runnable скрипт `scripts/migrate-<тема>.sql` + применение вручную
   (`docker exec -i arb-timescaledb psql ... < scripts/migrate-<тема>.sql`).
5. Новая настройка подключается строго по порядку: читающий код →
   `SettingsUpdate` (api-gateway/routers/exchanges.py) → `SETTING_FIELDS`
   (frontend/src/types.ts).
6. По завершении: все контейнеры healthy, run-tests.sh полностью зелёный,
   отчёт `docs/live-trading/stage-<N>-report.md` написан (что сделано, решения,
   отклонения от роадмапа с причинами, новые настройки/миграции/тесты, что
   важно следующему этапу). Коммитит отдельный шаг workflow — сам не коммить.

## Конвенции и инварианты (нарушение = CRITICAL на ревью)

- Порядок гейтов executor (возраст → кулдаун → свежесть → баланс → notional →
  проход книги → гейт прибыльности) — гейт прибыльности всегда ДО мутаций.
- `shared/depth.py` — единственная реализация walk/VWAP; top-of-book fallback
  запрещён.
- P&L: любой запрос — только через `PNL_EVENTS` (api-gateway/routers/pnl_sql.py).
- Kill switch fail-closed: `shared/redis_utils.py::kill_switch_engaged` и
  `KILL_SWITCH_KEY` — единственные точки истины; `settings.kill_switch` мёртв.
- Импорты внутри сервиса плоские; `shared/` — пакет. Межсервисные мутации —
  только через Redis (HTTP — только read-only /health у бота).
- Redis: `appendonly yes`, `noeviction` — не ослаблять; новые нессрочные ключи
  либо capped (maxlen), либо с TTL.
- Деньги в Python 3.11+: на новом/переписываемом денежном пути — Decimal.

---

## Этап 1 — Модель учёта (инвентарная модель)

Скилы: ecc:python-patterns, ecc:redis-patterns, ecc:postgres-patterns,
ecc:database-migrations, ecc:tdd-workflow. Ревью: python + database.

1. **Двухактивный учёт (exchange × asset).** Сейчас executor/balance.py ведёт
   только USDT: buy-нога списывает USDT на buy-бирже, sell-нога НАЧИСЛЯЕТ USDT
   на sell-бирже (paper_trading.py:242-245) — базовый актив не существует.
   Ввести учёт `balance:{ex}` по активам (USDT + базовые активы торгуемых пар),
   sell-нога гейтится наличием base-инвентаря на sell-бирже (новый skip-reason).
   Hypertable `balance` уже имеет колонку asset — расширяется код, не схема.
   Paper-режим переводится на эту же модель (иначе paper перестаёт быть
   репетицией реала): начальный base-инвентарь сидится эквивалентом в USDT по
   текущей цене либо конфигом.
2. **Per-exchange halt вместо авто-ребаланса.** executor/rebalance.py (перевод
   от донора + kill switch) заменить: настройка `min_exchange_balance_usd`
   (seed ~80, SettingsUpdate ge=0, SETTING_FIELDS); при пробое биржа
   исключается из торговли (skip обеих ног, отдельный reason в
   trades_skipped_total) + алерт-событие в стрим для notifier. Ручное
   пополнение фиксируется в ledger (reason='rebalance' — PNL_EVENTS не меняется)
   через существующий PUT /balance (paper) / будущий инструмент оператора.
   Анти-пинг-понг больше не нужен; ветка «нет донора → kill switch» заменяется
   на «все биржи ниже порога → kill switch».
3. **Decimal на денежном пути.** executor: балансы (строки Redis — хранить
   квантованные Decimal-строки), pnl.py, paper_trading.py. Тесты пересчитать.
4. **Схема `orders` (per-leg).** Новая таблица (migrate-orders.sql):
   client_order_id (PK-компонент), exchange_order_id, trade_id (ссылка),
   leg (buy/sell), exchange, symbol, статус
   (submitted/partially_filled/filled/cancelled/failed), price, amount,
   filled_amount, fee, fee_asset, created_at/updated_at. `trades` остаётся
   агрегатом двух ног. Пока пишет только paper-движок (оба «ордера» filled) —
   этап 2B начнёт использовать по-настоящему.
5. **Сверка Redis ↔ PG-ledger.** Периодическая задача в executor (рядом с
   _refresh_settings): сумма ledger по бирже vs Redis; расхождение сверх
   допуска → алерт-лог + метрика; крупное → kill switch.
6. **Ledger как учётный документ.** Снять retention с `trades`
   (migrate-скриптом: remove_retention_policy), ежедневный pg_dump-бэкап
   (cron-контейнер или скрипт + документация), заготовка REVOKE
   TRUNCATE/DELETE для будущей live-роли.

Критерий готовности: тесты (вкл. новые: base-инвентарь гейтит sell, halt по
порогу, Decimal-точность) зелёные; paper-стек работает на инвентарной модели.

## Этап 2A — Инфраструктура биржевых подключений

Скилы: ecc:python-patterns, ecc:error-handling, ecc:security-review,
ecc:tdd-workflow. Ревью: python + security.

1. ccxt в executor/requirements.txt; фабрика приватных REST-клиентов
   (по образцу collector/exchange_factory.py) для стартовых 3-4 бирж.
2. Контур API-ключей: отдельный untracked `.env.executor`
   (+ .env.executor.example), только executor в docker-compose; guard при
   PAPER=false: отказ старта без валидных ключей; проверка прав ключа где биржа
   отдаёт (право withdraw → отказ старта). Ключи не логировать никогда.
3. Кэш markets: load_markets() при старте + периодический рефреш; гейт фильтров
   после walk-функций: amount_to_precision/price_to_precision, limits.amount.min,
   limits.cost.min ОБЕИХ ног до любой отправки; несоответствие → skip с
   отдельным reason. Работает и в paper (публичные markets) — тестируемо сейчас.
4. Rate limiting REST-пути (enableRateLimit + защита от параллельных всплесков).
5. Время: периодический fetchTime-offset с метрикой и алертом >1s; recvWindow
   в опциях клиентов; chrony на VPS — документировать в отчёте.

## Этап 2B — Движок исполнения

Скилы: ecc:python-patterns, ecc:latency-critical-systems, ecc:tdd-workflow.
Ревью: python.

1. Интерфейс `ExecutionVenue` (место: executor/): единый контракт для
   paper-движка и реального; существующая цепочка гейтов — общий pre-trade этап.
2. Идемпотентность: детерминированный clientOrderId = f(opportunity_id, leg);
   write-ahead intent в `orders` ДО отправки; при неопределённом ответе —
   fetchOrder по clientOrderId, не слепой ретрай.
3. После write-ahead: XAUTOCLAIM-восстановление PEL при рестарте вместо
   безусловного ack (инвариант «redelivery запрещён» переворачивается —
   обработка становится идемпотентной; обнови комментарий и CLAUDE.md).
4. Исполнение ног: одновременная отправка taker-taker, IOC-limit по worst-price
   из walk (не market). Partial fill — штатный режим: вторая нога сайзится по
   факту первой. Leg risk плейбук: ограниченные ретраи с ухудшением цены →
   unwind исполненной ноги → автопауза связки + алерт.
5. settle_trade по фактическим fills (pnl.py остаётся единственной формулой).
6. Реальное исполнение остаётся ВЫКЛЮЧЕННЫМ (PAPER=true); всё покрывается
   тестами со стабами биржи (паттерн test_paper_trading) + интеграционными
   против живого Redis.

## Этап 2C — Экономика и сверка

Скилы: ecc:python-patterns, ecc:tdd-workflow. Ревью: python.

1. Комиссии per-pair: market['taker'] из markets вместо одного скаляра на
   биржу; scanner и executor читают per-pair ставку (источник — collector
   _sync_pairs → tracked_pairs/Redis, либо кэш markets в scanner/executor —
   выбери и обоснуй в отчёте). Приватный fetchTradingFees per-account при
   наличии ключей перекрывает публичные.
2. KuCoin: до per-pair комиссий его немейджорные пары должны быть исключены;
   с per-pair — снимается автоматически. Проверь фактические ставки Class A/B/C.
3. Балансы с биржи: fetch_balance как источник правды в real-режиме; сверка с
   внутренним ledger с допуском; дрифт сверх допуска → kill switch + алерт.
   Сайзинг позиции — от подтверждённого баланса.

## Этап 3 — Риск-контуры

Скилы: ecc:python-patterns, ecc:tdd-workflow. Ревью: python.

1. `daily_loss_limit_pct` (сид уже есть в settings, TZ E-014): периодическая
   проверка дневного P&L по PNL_EVENTS от стартового equity дня; пробой →
   kill switch + алерт. Подключение: код → SettingsUpdate → SETTING_FIELDS.
2. Loss-streak автостоп: N подряд убыточных ИСПОЛНЕННЫХ сделок → пауза/стоп
   (настройка).
3. Абсолютные лимиты: `max_trade_notional_usd` (min с процентным),
   `max_trades_per_minute` (превышение → kill switch), per-symbol дневной кап.
4. Canary: `size_multiplier` (0..1) в settings — множитель notional.
5. Автотриггеры kill switch: staleness данных (нет свежего depth по всем
   парам N сек), дрифт сверки балансов (из этапа 1.5/2C.3), шторм
   ws_watchdog_reconnects.

## Этап 4 — Качество данных

Скилы: ecc:python-patterns, ecc:redis-patterns. Ревью: python.

1. Checksum стакана: включить в collector/exchange_factory.py для бирж, где
   ccxt поддерживает верификацию; ChecksumError → штатный force-reconnect с
   DELete depth-ключей. Для остальных — периодическая REST-сверка топа книги.
2. Метрика detect→execute: гистограмма возраста opportunity в момент
   исполнения (Prometheus) + сохранение в trade.
3. Toxic-сигнал: возраст спреда связки (первое обнаружение — Redis рядом с
   dedup) → в Opportunity; гейт `max_spread_age_sec` в executor (настройка).
4. Идентичность активов: fetch_currencies() в _sync_pairs — сверка
   сетей/контрактов базового актива между биржами; деактивация пар с
   расхождением или deposit/withdraw=false (через tracked_pairs.is_active).
5. Haircut на объём уровней: конфигурируемый коэффициент в walk-функциях
   (shared/depth.py — единая точка; по умолчанию 1.0 = поведение как сейчас).
6. Dedup: ключ с учётом улучшения спреда (лучший спред в окне 5с не должен
   теряться); мониторинг clock-offset (из 2A.5) в /health.

## Этап 5 — Наблюдаемость и эксплуатация

Скилы: ecc:docker-patterns, ecc:deployment-patterns, ecc:security-review.
Ревью: code + security.

1. Alertmanager + rule_files в monitoring/: правила по up,
   trades_skipped_total (аномальный рост), ws_watchdog_reconnects_total,
   XPENDING/lag consumer-groups (нужен экспортёр или задача в сервисах),
   длина telegram_dead_letter, redis_up, дрифт сверок, пробой лимитов.
   Канал доставки — ОТДЕЛЬНЫЙ Telegram-бот/чат (не через notifier).
2. Dead-letter consumer: разгребание telegram_dead_letter (повтор/отчёт).
3. Grafana/Prometheus: закрыть auth (пароль из .env уже есть — включить
   принудительно, убрать anonymous), не публиковать лишние порты.
4. Роли и аудит: is_admin в users; killswitch/settings/DELETE — только admin;
   `_user` в аудит-лог всех мутаций; двухшаговое подтверждение СНЯТИЯ kill
   switch (confirm-token); в Telegram — allowlist user_id (не только chat_id).
5. Тесты live-критичных путей executor: ack-семантика, краш между мутацией
   балансов и персистом, redelivery/XAUTOCLAIM (после 2B), рестарт —
   интеграционно против живого Redis (паттерн test_integration).
6. Supply chain: зафиксировать теги образов (timescale, redis, python),
   non-root в Dockerfile, .dockerignore.

## Этап 6 — Готовность к shadow-прогону

Скилы: ecc:production-audit. Ревью: не требуется (код не меняется, кроме
конфигурации; если код всё же менялся — python-ревью обязательно).

1. Конфигурация целевого запуска: выбрать 3-4 биржи (критерии: качество API,
   комиссии, фактический аптайм фидов из метрик) и топ-10 пар; выключить
   остальное через exchange_configs.is_active / tracked_pairs.
2. Прогнать полный аудит продакшн-готовности (скил ecc:production-audit) по
   всем этапам 0-5: каждый пункт роадмапа — выполнен/нет, со ссылкой на код.
3. Написать `docs/live-trading/go-no-go.md`: чек-лист shadow-месяца
   (0 расхождений сверок; алертинг отработал на учениях — убить collector,
   прилетел алерт; фильтры бирж без реджектов; метрика detect→execute в
   норме), критерии перехода к канарейке (size_multiplier ~0.25, BTC/ETH,
   2 биржи, схождение факт-vs-модель) и ramp-up 25→50→100%.
4. Итоговый отчёт stage-6-report.md: что готово, что осталось руками
   (ротация Telegram-токена, заведение API-ключей с IP allowlist, chrony,
   запуск shadow).
