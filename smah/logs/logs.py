import os
import logging
import sys
from typing import TextIO, Optional
from datetime import datetime

from smah.settings.settings import Settings
from logging.handlers import RotatingFileHandler

# Constants
DEFAULT_LOG_LEVEL = logging.DEBUG
DEFAULT_CONSOLE_LOG_LEVEL = logging.WARN
DEFAULT_MAX_BYTES = 10 ** 6
DEFAULT_BACKUP_COUNT = 3
DEFAULT_LOG_DIR = os.path.expanduser("~/.smah/logs")


def configure(
        log_level: int = DEFAULT_LOG_LEVEL,
        console_log_level: Optional[int] = DEFAULT_CONSOLE_LOG_LEVEL,
        log_file: Optional[str] = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
        backup_count: int = DEFAULT_BACKUP_COUNT,
        console_out: TextIO = sys.stderr
) -> None:
    """
    Configure logging settings.

    Args:
        log_level (int): The logging level.
        log_file (Optional[str]): The path to the log file.
        max_bytes (int): Maximum size of the log file before rotation.
        backup_count (int): Number of backup files to keep.
        console_out (TextIO): The output stream for logging.
    """
    console_log_level = console_log_level or log_level
    if log_file is None:
        log_file = os.path.join(DEFAULT_LOG_DIR, f"smah.{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    except OSError as e:
        logging.error("Failed to create log directory: %s", e)
        raise

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(pathname)s:%(lineno)d %(message)s',
        handlers=[
            RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            ),
            logging.StreamHandler(console_out)
        ]
    )

    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(console_log_level)
        elif isinstance(handler, RotatingFileHandler):
            handler.setLevel(log_level)


    logging.info("Logging Configured")
