"""Единая настройка логирования для всех микросервисов.

Каждый сервис при старте вызывает :func:`setup_logging("<service>")`. Это:

- настраивает ``structlog`` поверх stdlib ``logging`` через ``ProcessorFormatter``,
  так что и наши ``log.info(...)``, и сторонние логгеры (uvicorn, ccxt, aiogram,
  asyncio) проходят через одни и те же обработчики;
- пишет **JSON-строки** в ротируемый файл ``${LOG_DIR}/<service>.log`` (по умолчанию
  ``/app/logs/<service>.log``) — этот каталог пробрасывается из контейнера наружу
  (bind-mount ``./logs``) и читается Promtail → Loki → Grafana;
- дублирует человекочитаемый вывод в stdout (виден в ``docker logs``).

Порядок запуска uvicorn важен: uvicorn выполняет ``configure_logging()`` ДО импорта
``main:app``, поэтому ``setup_logging`` (вызванная при импорте ``main``) выполняется
последней и корректно перехватывает логгеры uvicorn. Поскольку uvicorn использует
``disable_existing_loggers=False``, наши хендлеры не сбрасываются.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

import structlog

# Лимиты ротации файлового лога: 10 МБ × 5 файлов на сервис.
_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5

# Сторонние логгеры, которые нужно «завернуть» в наш root (их сообщения — это и есть
# каждый HTTP-запрос/ошибка API и события сети/бирж).
_THIRD_PARTY_LOGGERS = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "fastapi",
    "aiogram",
    "aiogram.event",
    "ccxt",
    "ccxtpro",
    "asyncio",
    "websockets",
    "websockets.client",
    "redis",
    "asyncpg",
)


def setup_logging(service_name: str) -> None:
    """Сконфигурировать logging/structlog для сервиса ``service_name``.

    Идемпотентна: повторный вызов пересоздаёт хендлеры, а не плодит их.
    """
    log_dir = Path(os.getenv("LOG_DIR", "/app/logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    level = os.getenv("LOG_LEVEL", "INFO").upper()

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    def add_service_name(_logger, _method_name, event_dict):
        """Проставить имя сервиса в каждую запись (и наши, и сторонние)."""
        event_dict.setdefault("service", service_name)
        return event_dict

    # Процессоры, общие для записей structlog и stdlib (foreign_pre_chain).
    shared_processors = [
        add_service_name,
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        structlog.processors.StackInfoRenderer(),
    ]

    # structlog отдаёт записи в stdlib logging, рендеринг — на стороне ProcessorFormatter.
    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # JSON — в файл (удобно для Loki). Трейсбеки разворачиваются в структуру.
    file_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
    )
    # Человекочитаемо — в stdout (docker logs).
    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
    )

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / f"{service_name}.log",
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    root.setLevel(level)

    # Перехватываем сторонние логгеры: убираем их собственные хендлеры и заставляем
    # пропагировать в root (uvicorn по умолчанию ставит propagate=False на access/error).
    for name in _THIRD_PARTY_LOGGERS:
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
        lg.setLevel(level)

    structlog.get_logger(service_name).info(
        "logging_initialised", log_file=str(log_dir / f"{service_name}.log"), level=level
    )
