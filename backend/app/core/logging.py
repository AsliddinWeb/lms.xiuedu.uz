import logging
import sys

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """Strukturlangan logging — console (dev) yoki JSON (prod)."""
    level = getattr(logging, settings.LOG_LEVEL)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        timestamper,
    ]

    if settings.LOG_JSON or settings.is_production:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # stdlib logging ni shu konfiguratsiyaga yo'naltirish
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Uvicorn access loglari shovqin qiladi — INFO darajasiga
    for noisy in ("uvicorn.access", "watchfiles"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
