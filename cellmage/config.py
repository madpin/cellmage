import logging
import os
from pathlib import Path
from typing import List, Optional, Union

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def get_base_dir() -> Path:
    """
    Returns the base directory for all CellMage working files.
    Priority:
    1. CELLMAGE_BASE_DIR environment variable
    2. Current working directory (default)
    """
    base_dir = os.environ.get("CELLMAGE_BASE_DIR")
    if base_dir:
        return Path(os.path.expanduser(base_dir)).resolve()
    return Path.cwd()


class Settings(BaseSettings):
    """
    Configuration settings for the application using Pydantic.

    This class provides strongly-typed configuration settings that are automatically
    loaded from environment variables with the ``CELLMAGE_`` prefix. It also supports
    loading from .env files automatically.
    """

    # Explicitly define __annotations__ to help with sphinx-autodoc-typehints compatibility
    __annotations__ = {
        "default_model": str,
        "default_persona": Optional[str],
        "auto_display": bool,
        "auto_save": bool,
        "autosave_file": str,
        "personas_dir": str,
        "personas_dirs_list": List[str],
        "snippets_dir": str,
        "snippets_dirs_list": List[str],
        "conversations_dir": str,
        "storage_type": str,
        "store_raw_responses": bool,
        "model_mappings_file": Optional[str],
        "auto_find_mappings": bool,
        "request_headers": dict,
        "log_level": str,
        "console_log_level": str,
        "log_file": str,
        # Image settings
        "image_default_width": int,
        "image_default_quality": float,
        "image_formats_allowed": List[str],
        "image_formats_llm_compatible": List[str],
        "image_target_format": str,
        # Google Docs integration settings
        "gdocs_token_path": str,
        "gdocs_credentials_path": str,
        "gdocs_service_account_path": str,
        "gdocs_auth_type": str,
        "gdocs_scopes": List[str],
        "gdocs_search_results_max": int,
        "gdocs_search_content_max": int,
        "gdocs_parallel_fetch_limit": int,
        "gdocs_request_timeout": int,
        "sqlite_path": str,
    }

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

    # Image settings
    image_default_width: int = Field(default=1024, description="Default width for resizing images")
    image_default_quality: float = Field(
        default=0.75, description="Default quality for image compression (0.0-1.0)"
    )
    image_formats_allowed: List[str] = Field(
        default=["jpg", "jpeg", "png", "webp", "gif"],
        description="Image formats supported by the system",
    )
    image_formats_llm_compatible: List[str] = Field(
        default=["jpg", "jpeg", "png", "webp"],
        description="Image formats compatible with LLM providers",
    )
    image_target_format: str = Field(
        default="png", description="Target format for incompatible image formats"
    )
    autosave_file: str = Field(
        default="autosaved_conversation", description="Filename for auto-saved conversations"
    )
    personas_dir: str = Field(
        default=str(get_base_dir() / "llm_personas"),
        description="Primary directory containing persona definitions",
    )
    personas_dirs_list: List[str] = Field(
        default_factory=list,
        alias="personas_dirs",
        description="Additional directories containing persona definitions",
    )
    snippets_dir: str = Field(
        default=str(get_base_dir() / "llm_snippets"),
        description="Primary directory containing snippets",
    )
    snippets_dirs_list: List[str] = Field(
        default_factory=list,
        alias="snippets_dirs",
        description="Additional directories containing snippets",
    )
    conversations_dir: str = Field(
        default=str(get_base_dir() / "llm_conversations"),
        description="Directory for saved conversations",
    )
    storage_type: str = Field(
        default="sqlite", description="Storage backend type ('sqlite', 'memory', or 'file')"
    )
    store_raw_responses: bool = Field(
        default=False, description="Whether to store raw API request/response data"
    )

    # Model mapping settings
    model_mappings_file: Optional[str] = Field(
        default=None, description="Path to YAML file containing model name mappings"
    )
    auto_find_mappings: bool = Field(
        default=True,
        description="Automatically look for .cellmage_models.yml in notebook directory",
    )

    # LLM Request Headers
    request_headers: dict = Field(
        default_factory=dict,
        description="Additional headers to send with LLM requests",
    )

    # Logging settings
    log_level: str = Field(default="INFO", description="Global logging level")
    console_log_level: str = Field(default="WARNING", description="Console logging level")
    log_file: str = Field(default=str(get_base_dir() / "cellmage.log"), description="Log file path")

    # Google Docs integration settings
    gdocs_token_path: str = Field(
        default=str(get_base_dir() / "gdocs_token.pickle:~/.cellmage/gdocs_token.pickle"),
        description="Path to Google Docs OAuth token pickle file (colon-separated for multiple locations)",
    )
    gdocs_credentials_path: str = Field(
        default=str(get_base_dir() / "gdocs_credentials.json:~/.cellmage/gdocs_credentials.json"),
        description="Path to Google Docs OAuth client credentials JSON file (colon-separated for multiple locations)",
    )
    gdocs_service_account_path: str = Field(
        default=str(
            get_base_dir() / "gdocs_service_account.json:~/.cellmage/gdocs_service_account.json"
        ),
        description="Path to Google Docs service account JSON file (colon-separated for multiple locations)",
    )
    gdocs_auth_type: str = Field(
        default="oauth",
        description="Google Docs authentication type (oauth or service_account)",
    )
    gdocs_scopes: List[str] = Field(
        default=[
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
        description="Google Docs OAuth scopes",
    )
    gdocs_search_results_max: int = Field(
        default=100, description="Maximum number of search results to return"
    )
    gdocs_search_content_max: int = Field(
        default=1000, description="Maximum content size to retrieve from search results"
    )
    gdocs_parallel_fetch_limit: int = Field(
        default=1, description="Maximum number of parallel fetch operations for Google Docs"
    )
    gdocs_request_timeout: int = Field(
        default=60, description="Timeout in seconds for Google Docs API requests"
    )
    gdocs_doc_fetch_timeout: int = Field(
        default=60, description="Timeout in seconds for individual document fetch operations"
    )

    sqlite_path: str = Field(
        default="",
        description="Path to SQLite database file. Defaults to ${base_dir}/.data/conversations.db unless CELLMAGE_SQLITE_PATH is set.",
    )

    model_config = SettingsConfigDict(
        env_prefix="CELLMAGE_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
    )

    def __init__(self, **data):
        # Process headers from environment variables
        headers = {}
        for key, value in os.environ.items():
            if key.startswith("CELLMAGE_HEADER_"):
                header_name = key.replace("CELLMAGE_HEADER_", "").lower().replace("_", "-")
                headers[header_name] = value
        if headers:
            data["request_headers"] = headers
            logger.debug(f"Set request_headers from environment: {headers}")

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

        # Process Google Docs environment variables
        env_gdocs_scopes = os.environ.get("CELLMAGE_GDOCS_SCOPES")
        if env_gdocs_scopes:
            scopes = [s.strip() for s in env_gdocs_scopes.replace(";", ",").split(",") if s.strip()]
            data["gdocs_scopes"] = scopes
            logger.debug(f"Set gdocs_scopes from environment: {scopes}")

        # Centralized SQLite path logic
        env_sqlite_path = os.environ.get("CELLMAGE_SQLITE_PATH")
        if env_sqlite_path:
            data["sqlite_path"] = os.path.expanduser(env_sqlite_path)
        elif not data.get("sqlite_path"):
            base_dir = get_base_dir()
            data["sqlite_path"] = str(base_dir / ".data" / "conversations.db")

        # Call parent init
        super().__init__(**data)

        # Ensure .data directory exists if using default
        if self.sqlite_path and not os.path.exists(os.path.dirname(self.sqlite_path)):
            os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)

        # For Google Docs paths, expand user paths
        self.gdocs_token_path = os.path.expanduser(self.gdocs_token_path)
        self.gdocs_credentials_path = os.path.expanduser(self.gdocs_credentials_path)
        self.gdocs_service_account_path = os.path.expanduser(self.gdocs_service_account_path)

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

    @property
    def sqlite_path_resolved(self) -> str:
        """
        Returns the resolved SQLite path, always up to date with env/config.
        """
        env_sqlite_path = os.environ.get("CELLMAGE_SQLITE_PATH")
        if env_sqlite_path:
            return os.path.expanduser(env_sqlite_path)
        return self.sqlite_path

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

        # If base_dir or sqlite_path is updated, recalculate sqlite_path
        if "base_dir" in kwargs or "sqlite_path" in kwargs:
            env_sqlite_path = os.environ.get("CELLMAGE_SQLITE_PATH")
            if env_sqlite_path:
                self.sqlite_path = os.path.expanduser(env_sqlite_path)
            else:
                self.sqlite_path = str(get_base_dir() / ".data" / "conversations.db")

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
