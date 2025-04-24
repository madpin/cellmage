import os
import logging
from typing import Optional

def setup_logging(
    log_file: str = "cellmage.log",
    debug: bool = False,
    console_level: Optional[int] = None
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
    # Set up root logger
    logger = logging.getLogger("cellmage")
    logger.handlers = []  # Clear existing handlers to prevent duplicates
    
    # Determine log levels
    file_level = logging.DEBUG if debug else logging.INFO
    if console_level is None:
        console_level = logging.DEBUG if debug else logging.INFO
        
    logger.setLevel(min(file_level, console_level))  # Set to the more verbose of the two
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # File Handler
    try:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(file_level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception as e:
        print(f"CRITICAL: Failed to create file logger at {log_file}: {e}")
        
        # Set up a basic console handler as a fallback
        fallback = logging.StreamHandler()
        fallback.setLevel(logging.INFO)
        fallback.setFormatter(formatter)
        logger.addHandler(fallback)
        
        # Log the error
        logger.error(f"File logging failed. Using console fallback. Error: {e}")
    
    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    logger.propagate = False  # Prevent duplicate logging by parent loggers
    
    # Log startup message
    logger.info("Cellmage logging initialized")
    if debug:
        logger.debug("Debug logging enabled")
        
    return logger

