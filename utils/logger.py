"""Application-wide logging configuration.

Provides a factory function that returns configured logger
instances with both rotating file and console output.

The rotating log file is written to *logs/application.log* with
a maximum size of 10 MB and up to 5 backup copies.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

from config.constants import LOG_BACKUP_COUNT, LOG_FILENAME, LOG_MAX_BYTES
from config.settings import LOGS_DIR


def setup_logger(name: str) -> logging.Logger:
    """Create and return a logger with rotating-file and console handlers.

    The logger writes ``DEBUG``-level messages to the rotating log file
    and ``INFO``-level messages to the console (stdout).

    Args:
        name: Dot-separated logger name, typically ``__name__``.

    Returns:
        A fully configured ``logging.Logger`` instance.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger: logging.Logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter: logging.Formatter = logging.Formatter(
        "%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler: RotatingFileHandler = RotatingFileHandler(
        LOGS_DIR / LOG_FILENAME,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
