"""Request-correlated structured logging configuration."""

from __future__ import annotations

import logging
from contextvars import ContextVar

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Inject the active request identifier into each application log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


def configure_logging(log_level: str) -> None:
    """Configure the application logger once at service startup."""
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"
        )
    )
    logger = logging.getLogger("agentic_ai_api")
    logger.handlers = [handler]
    logger.setLevel(log_level.upper())
    logger.propagate = False
