import os
import logging
import sys
from typing import TextIO, Optional
import yaml
from datetime import datetime
import textwrap

from smah.settings.settings import Settings
from logging.handlers import RotatingFileHandler

# Constants
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_MAX_BYTES = 10 ** 6
DEFAULT_BACKUP_COUNT = 3
DEFAULT_LOG_DIR = os.path.expanduser("~/.smah/logs")


def configure(
        log_level: int = DEFAULT_LOG_LEVEL,
        log_file: Optional[str] = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
        backup_count: int = DEFAULT_BACKUP_COUNT,
        out_pipe: TextIO = sys.stderr
) -> None:
    """
    Configure logging settings.

    Args:
        log_level (int): The logging level.
        log_file (Optional[str]): The path to the log file.
        max_bytes (int): Maximum size of the log file before rotation.
        backup_count (int): Number of backup files to keep.
        out_pipe (TextIO): The output stream for logging.
    """
    if log_file is None:
        log_file = os.path.join(DEFAULT_LOG_DIR, f"smah.{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    except OSError as e:
        logging.error("Failed to create log directory: %s", e)
        raise

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(pathname)s:%(lineno)d [%(levelname)s] %(message)s',
        handlers=[
            RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            ),
            logging.StreamHandler(out_pipe)
        ]
    )
    logging.info("Logging Configured")


def log_settings(settings: Settings, format: bool = True, print: bool = False) -> None:
    """
    Log current application settings and print them in a configured format.

    Args:
        settings (Settings): Application settings object.
        format (bool): Flag to enable/disable formatting of settings when printing.
        print_settings (bool): Flag to enable/disable printing of settings.
    """
    try:
        settings_yaml = yaml.dump({"settings": settings.to_yaml({"stats": True})}, sort_keys=False)
        logging.debug("Settings YAML: %s", settings_yaml)
        if print:
            formatted_settings = textwrap.dedent(
                """
                Settings
                ========
                ```yaml
                {c}
                ```
                """
            ).strip().format(c=settings_yaml)
            #std_console.print(Markdown(formatted_settings) if format else formatted_settings)
    except Exception as e:
        logging.error("Exception raised while logging settings: %s", str(e))