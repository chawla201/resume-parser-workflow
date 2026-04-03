"""Structured JSON logging configuration shared by CLI and API entrypoints."""

from __future__ import annotations

import contextvars
import logging
import os
from pythonjsonlogger import jsonlogger

REQUEST_ID: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

_CONFIGURED: bool = False


class _RequestIdFilter(logging.Filter):
    """Inject the current REQUEST_ID context variable into every log record.

    Attributes:
        None beyond the standard Filter state.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach the active request_id to *record* before emission.

        Args:
            record: The log record being processed.

        Returns:
            Always ``True`` — this filter never suppresses records.
        """
        record.request_id = REQUEST_ID.get("-")
        return True


def configure_logging(level: str | None = None) -> None:
    """Configure root logger to emit structured JSON log lines.

    Idempotent — subsequent calls are no-ops so that importing multiple
    modules does not re-configure the logger.

    Output format (one JSON object per line)::

        {"timestamp": "...", "level": "INFO", "name": "src.parser",
         "message": "...", "request_id": "abc123"}

    Args:
        level: Override log level string (e.g. ``"DEBUG"``). Falls back to
            the ``LOG_LEVEL`` environment variable, then ``"INFO"``.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    effective_level = (level or LOG_LEVEL).upper()

    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(_RequestIdFilter())

    root = logging.getLogger()
    root.setLevel(effective_level)
    root.handlers.clear()
    root.addHandler(handler)

    _CONFIGURED = True
