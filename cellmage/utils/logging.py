import logging
import sys
from ..config import settings # Import settings to get log level

_initialized = False

def setup_logging():
    """Configures logging for the application based on settings."""
    global _initialized
    if _initialized:
        return

    log_level_str = settings.log_level.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Basic configuration - modify formatter and handlers as needed
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Configure root logger or specific package logger
    # Configuring root logger can affect other libraries, be careful
    # logger = logging.getLogger("notebook_llm") # Get package-specific logger
    logger = logging.getLogger() # Get root logger
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates if called multiple times (though _initialized prevents this)
    # for handler in logger.handlers[:]:
    #     logger.removeHandler(handler)

    # Add a handler (e.g., StreamHandler to stderr/stdout)
    # Avoid adding handlers if they already exist from a parent logger setup
    if not logger.hasHandlers():
        handler = logging.StreamHandler(sys.stderr) # Log to stderr by default
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.info(f"Root logger configured with level {log_level_str}.")
    else:
         logger.info(f"Logger already has handlers. Ensuring level is {log_level_str}.")

    # Propagate settings to libraries like LiteLLM if desired
    try:
         import litellm
         # LiteLLM verbose maps roughly to DEBUG
         litellm.set_verbose = (log_level <= logging.DEBUG)
         logger.debug(f"Set litellm.set_verbose to {litellm.set_verbose}")
    except ImportError:
         pass # LiteLLM not installed
    except Exception as e:
         logger.warning(f"Could not configure LiteLLM logging: {e}")

    _initialized = True

def get_logger(name: str) -> logging.Logger:
    """Gets a logger instance, ensuring setup_logging has been called."""
    if not _initialized:
        setup_logging()
    return logging.getLogger(name)

# Call setup automatically when the module is imported?
# Or rely on explicit call from __init__.py or application entry point.
# Calling it here ensures logging is set up whenever get_logger is first called.
# setup_logging() # Optional: uncomment to auto-setup on import

