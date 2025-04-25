import os
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class Settings:
    """
    Configuration settings for the application.
    
    Loads settings from environment variables with the CELLMAGE_ prefix.
    """
    
    def __init__(self):
        """Initialize settings from environment."""
        # Try to load from .env file if available and not skipped
        if os.environ.get("CELLMAGE_SKIP_DOTENV") != "1":
            try:
                from dotenv import load_dotenv
                if load_dotenv():
                    logger.info("Loaded environment variables from .env file")
                else:
                    logger.info("No .env file found or it was empty")
            except ImportError:
                logger.info("python-dotenv not installed, skipping .env file loading")
        
        # Default settings
        self.default_model = os.environ.get("CELLMAGE_DEFAULT_MODEL", "gpt-4.1-nano")
        self.default_persona = os.environ.get("CELLMAGE_DEFAULT_PERSONA")
        self.auto_display = self._parse_bool(os.environ.get("CELLMAGE_AUTO_DISPLAY", "true"))
        self.auto_save = self._parse_bool(os.environ.get("CELLMAGE_AUTO_SAVE", "false"))
        self.autosave_file = os.environ.get("CELLMAGE_AUTOSAVE_FILE", "autosaved_conversation")
        self.personas_dir = os.environ.get("CELLMAGE_PERSONAS_DIR", "llm_personas")
        self.snippets_dir = os.environ.get("CELLMAGE_SNIPPETS_DIR", "snippets")
        self.conversations_dir = os.environ.get("CELLMAGE_CONVERSATIONS_DIR", "llm_conversations")
        
        # Logging settings
        self.log_level = os.environ.get("CELLMAGE_LOG_LEVEL", "INFO").upper()
        self.console_log_level = os.environ.get("CELLMAGE_CONSOLE_LOG_LEVEL", "WARNING").upper()
        self.log_file = os.environ.get("CELLMAGE_LOG_FILE", "cellmage.log")
    
    @property
    def save_dir(self):
        """
        For compatibility with code that expects save_dir instead of conversations_dir.
        
        Returns:
            The conversations directory path
        """
        return self.conversations_dir
    
    def update(self, **kwargs) -> None:
        """
        Update settings with new values.
        
        Args:
            **kwargs: Settings to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.debug(f"Updated setting {key} = {value}")
            else:
                logger.warning(f"Unknown setting: {key}")
    
    def _parse_bool(self, value: Optional[str]) -> bool:
        """
        Parse a string as a boolean.
        
        Args:
            value: String value to parse
            
        Returns:
            Boolean value
        """
        if value is None:
            return False
        return value.lower() in ("true", "1", "yes", "y", "t")


# Create a global settings instance
settings = Settings()

