from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import DirectoryPath, Field, HttpUrl
from typing import Optional
import warnings
from pathlib import Path

class Settings(BaseSettings):
    """Manages application settings via environment variables, .env file, or defaults."""
    api_key: Optional[str] = Field(None, validation_alias='NBLLM_API_KEY')
    api_base: Optional[str] = Field(None, validation_alias='NBLLM_API_BASE') # Changed to str to avoid early validation issues if URL is complex/local
    log_level: str = Field("INFO", validation_alias='NBLLM_LOG_LEVEL')
    personas_dir: Path = Field("llm_personas", validation_alias='NBLLM_PERSONAS_DIR')
    save_dir: Path = Field("llm_conversations", validation_alias='NBLLM_SAVE_DIR')
    snippets_dir: Path = Field("snippets", validation_alias='NBLLM_SNIPPETS_DIR')

    # Default model to use if not specified by persona, override, or call
    default_model_name: Optional[str] = Field(None, validation_alias='NBLLM_DEFAULT_MODEL')

    # Configuration for Pydantic Settings
    model_config = SettingsConfigDict(
        env_file='.env',          # Load .env file if present
        env_file_encoding='utf-8',
        extra='ignore'            # Ignore extra fields from env/file
    )

# Singleton instance, loaded once on import
try:
    settings = Settings()

    # Create directories if they don't exist after loading settings
    settings.personas_dir.mkdir(parents=True, exist_ok=True)
    settings.save_dir.mkdir(parents=True, exist_ok=True)
    settings.snippets_dir.mkdir(parents=True, exist_ok=True)

except Exception as e:
    warnings.warn(f"Could not automatically create settings directories: {e}")
    # Allow execution to continue, components should handle missing dirs later if needed
    settings = Settings() # Load again to have a default object

