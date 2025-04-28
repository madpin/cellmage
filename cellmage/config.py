import logging
import os
from typing import List, Optional, Union

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Configuration settings for the application using Pydantic.

    This class provides strongly-typed configuration settings that are automatically
    loaded from environment variables with the CELLMAGE_ prefix. It also supports
    loading from .env files automatically.
    """

    # Default settings
    default_model: str = Field(
        default="gpt-4.1-nano", description="Default LLM model to use for chat"
    )
    default_persona: Optional[str] = Field(
        default=None, description="Default persona to use for chat"
    )
    auto_display: bool = Field(
        default=True, description="Whether to automatically display chat messages"
    )
    auto_save: bool = Field(default=True, description="Whether to automatically save conversations")
    autosave_file: str = Field(
        default="autosaved_conversation", description="Filename for auto-saved conversations"
    )
    personas_dir: str = Field(
        default="llm_personas", description="Primary directory containing persona definitions"
    )
    personas_dirs_list: List[str] = Field(
        default_factory=list,
        alias="personas_dirs",
        description="Additional directories containing persona definitions",
    )
    snippets_dir: str = Field(
        default="llm_snippets", description="Primary directory containing snippets"
    )
    snippets_dirs_list: List[str] = Field(
        default_factory=list,
        alias="snippets_dirs",
        description="Additional directories containing snippets",
    )
    conversations_dir: str = Field(
        default="llm_conversations", description="Directory for saved conversations"
    )

    # Model mapping settings
    model_mappings_file: Optional[str] = Field(
        default=None, description="Path to YAML file containing model name mappings"
    )
    auto_find_mappings: bool = Field(
        default=True,
        description="Automatically look for .cellmage_models.yml in notebook directory",
    )

    # Logging settings
    log_level: str = Field(default="INFO", description="Global logging level")
    console_log_level: str = Field(default="WARNING", description="Console logging level")
    log_file: str = Field(default="cellmage.log", description="Log file path")

    model_config = SettingsConfigDict(
        env_prefix="CELLMAGE_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
    )

    def __init__(self, **data):
        # Process environment variables before initialization
        env_personas_dirs = os.environ.get("CELLMAGE_PERSONAS_DIRS")
        if env_personas_dirs:
            dirs = [d.strip() for d in env_personas_dirs.replace(";", ",").split(",") if d.strip()]
            data["personas_dirs"] = dirs
            logger.debug(f"Set personas_dirs from environment: {dirs}")

        env_snippets_dirs = os.environ.get("CELLMAGE_SNIPPETS_DIRS")
        if env_snippets_dirs:
            dirs = [d.strip() for d in env_snippets_dirs.replace(";", ",").split(",") if d.strip()]
            data["snippets_dirs"] = dirs
            logger.debug(f"Set snippets_dirs from environment: {dirs}")

        # Call parent init
        super().__init__(**data)

        # Check if conversations_dir exists and enable auto_save if it does
        if os.path.exists(self.conversations_dir) and os.path.isdir(self.conversations_dir):
            self.auto_save = True
            logger.info(
                f"Found '{self.conversations_dir}' folder. Auto-save enabled automatically."
            )

    @property
    def personas_dirs(self) -> List[str]:
        """Get additional persona directories"""
        return self.personas_dirs_list

    @personas_dirs.setter
    def personas_dirs(self, value: Union[List[str], str]) -> None:
        """Set additional persona directories"""
        if isinstance(value, str):
            self.personas_dirs_list = [
                d.strip() for d in value.replace(";", ",").split(",") if d.strip()
            ]
        else:
            self.personas_dirs_list = value

    @property
    def snippets_dirs(self) -> List[str]:
        """Get additional snippet directories"""
        return self.snippets_dirs_list

    @snippets_dirs.setter
    def snippets_dirs(self, value: Union[List[str], str]) -> None:
        """Set additional snippet directories"""
        if isinstance(value, str):
            self.snippets_dirs_list = [
                d.strip() for d in value.replace(";", ",").split(",") if d.strip()
            ]
        else:
            self.snippets_dirs_list = value

    @property
    def all_personas_dirs(self) -> List[str]:
        """Get all persona directories including the primary one."""
        dirs = [self.personas_dir]
        for dir in self.personas_dirs:
            if dir and dir not in dirs:
                dirs.append(dir)
        return dirs

    @property
    def all_snippets_dirs(self) -> List[str]:
        """Get all snippet directories including the primary one."""
        dirs = [self.snippets_dir]
        for dir in self.snippets_dirs:
            if dir and dir not in dirs:
                dirs.append(dir)
        return dirs

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
