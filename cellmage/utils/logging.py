import logging
import os
from typing import Optional

from ..config import settings  # Import settings to get log level from environment


def setup_logging(
    log_file: Optional[str] = None, debug: bool = False, console_level: Optional[int] = None
) -> logging.Logger:
    """
    Set up logging for the cellmage library.

    Args:
        log_file: Path to the log file
        debug: Whether to enable debug mode (more verbose logging)
        console_level: Optional specific level for console logging

    Returns:
        Root logger configured with handlers
    """
    # Use log_file from settings if not provided
    if log_file is None:
        log_file = settings.log_file

    # Set up root logger
    logger = logging.getLogger("cellmage")
    logger.handlers = []  # Clear existing handlers to prevent duplicates

    # Get log level from settings - convert string to logging level
    log_level_str = settings.log_level.upper()
    configured_level = getattr(
        logging, log_level_str, logging.INFO
    )  # Default to INFO for file logs

    # Get console log level from settings - convert string to logging level
    console_level_str = settings.console_log_level.upper()
    configured_console_level = getattr(
        logging, console_level_str, logging.WARNING
    )  # Default to WARNING for console

    # Determine log levels, respecting both debug flag and configured level
    file_level = logging.DEBUG if debug else configured_level
    if console_level is None:
        console_level = logging.DEBUG if debug else configured_console_level

    logger.setLevel(min(file_level, console_level))  # Set to the more verbose of the two

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # File Handler
    try:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(
            logging.INFO if not debug else logging.DEBUG
        )  # Always INFO or DEBUG if debug=True
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception as e:
        print(f"CRITICAL: Failed to create file logger at {log_file}: {e}")

        # Set up a basic console handler as a fallback
        fallback = logging.StreamHandler()
        fallback.setLevel(logging.WARNING)  # Change fallback to WARNING
        fallback.setFormatter(formatter)
        logger.addHandler(fallback)

        # Log the error
        logger.error(f"File logging failed. Using console fallback. Error: {e}")

    # Console Handler
    ch = logging.StreamHandler()
    if console_level is not None:
        ch.setLevel(console_level)
    else:
        ch.setLevel(logging.WARNING)  # Changed default from INFO to WARNING
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    logger.propagate = False  # Prevent duplicate logging by parent loggers

    # Log startup message (at INFO level so it will be suppressed if level is WARNING+)
    logger.info("Cellmage logging initialized")
    if debug:
        logger.debug("Debug logging enabled")

    return logger
