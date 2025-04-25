import os
import logging
from typing import Dict, Optional, Any

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Configuration settings for the application using Pydantic.
    
    This class provides strongly-typed configuration settings that are automatically
    loaded from environment variables with the CELLMAGE_ prefix. It also supports
    loading from .env files automatically.
    
    Example:
        # Access settings
        from cellmage.config import settings
        model_name = settings.default_model
        
        # Update settings
        settings.update(default_model="gpt-4")
    """
    # Default settings
    default_model: str = Field(
        default="gpt-4.1-nano",
        description="Default LLM model to use for chat"
    )
    default_persona: Optional[str] = Field(
        default=None,
        description="Default persona to use for chat"
    )
    auto_display: bool = Field(
        default=True,
        description="Whether to automatically display chat messages"
    )
    auto_save: bool = Field(
        default=False,
        description="Whether to automatically save conversations"
    )
    autosave_file: str = Field(
        default="autosaved_conversation",
        description="Filename for auto-saved conversations"
    )
    personas_dir: str = Field(
        default="llm_personas",
        description="Directory containing persona definitions"
    )
    snippets_dir: str = Field(
        default="snippets",
        description="Directory containing snippets"
    )
    conversations_dir: str = Field(
        default="llm_conversations",
        description="Directory for saved conversations"
    )
    
    # Logging settings
    log_level: str = Field(
        default="INFO",
        description="Global logging level"
    )
    console_log_level: str = Field(
        default="WARNING",
        description="Console logging level"
    )
    log_file: str = Field(
        default="cellmage.log",
        description="Log file path"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="CELLMAGE_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
    )
    
    @field_validator("log_level", "console_log_level")
    @classmethod
    def uppercase_log_levels(cls, v):
        """Ensure log levels are uppercase."""
        return v.upper() if isinstance(v, str) else v
    
    @property
    def save_dir(self) -> str:
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
        
        # Validate after update
        object.__setattr__(self, "__dict__", self.model_validate(self.__dict__).model_dump())

# Create a global settings instance
try:
    settings = Settings()
    logger.info("Settings loaded successfully using Pydantic")
except Exception as e:
    logger.exception(f"Error loading settings: {e}")
    # Fallback to default settings
    settings = Settings.model_construct()
    logger.warning("Using default settings due to configuration error")

