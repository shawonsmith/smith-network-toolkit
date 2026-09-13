"""Logging utility for Smith Network Diagnostic Toolkit."""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

_LOGGER: Optional[logging.Logger] = None
_PRIVACY_ENABLED: bool = False
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "toolkit.log"


class PrivacyLogFormatter(logging.Formatter):
    """Custom formatter with %H:%M:%S timestamp and optional privacy masking."""
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        msg = record.getMessage()
        if _PRIVACY_ENABLED:
            from src.utils.privacy import mask_text
            msg = mask_text(msg)
        return f"{timestamp} {msg}"


def setup_logger(privacy: bool = False) -> logging.Logger:
    """Initialize toolkit file logger."""
    global _LOGGER, _PRIVACY_ENABLED
    _PRIVACY_ENABLED = privacy

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("smith_toolkit")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if setup_logger is called multiple times
    if not logger.handlers:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(PrivacyLogFormatter())
        logger.addHandler(file_handler)

    _LOGGER = logger
    return logger


def set_logger_privacy(privacy: bool) -> None:
    """Toggle privacy masking on the logger."""
    global _PRIVACY_ENABLED
    _PRIVACY_ENABLED = privacy


def log_event(message: str, level: str = "info") -> None:
    """Convenience helper to record a log line."""
    global _LOGGER
    if _LOGGER is None:
        setup_logger()
    
    lvl = level.lower()
    if lvl == "warning":
        _LOGGER.warning(message)
    elif lvl == "error":
        _LOGGER.error(message)
    else:
        _LOGGER.info(message)
