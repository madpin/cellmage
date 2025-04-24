This is the original code "all-in-one" the origin of the project. It is not the current version of the project.
The current version is in the README.md file.

````python
import os
import frontmatter
import litellm
import yaml
import uuid
import copy
import logging  # Added
import time  # Added for status bar timing
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
import sys  # Added for transformer function

# Try importing IPython specifics safely
try:
    from IPython import get_ipython
    from IPython.display import display, Markdown, HTML

    _IPYTHON_AVAILABLE = True
except ImportError:
    _IPYTHON_AVAILABLE = False

    # Define dummy display/Markdown if not available for graceful failure
    def display(*args, **kwargs):
        # Use print as fallback ONLY if IPython isn't available
        # Logging should handle general output otherwise
        print("DISPLAY (fallback):", *args)

    class Markdown:
        def __init__(self, data):
            self.data = data

        def __str__(self):
            return str(self.data)

        def __repr__(self):
            return repr(self.data)


# Try importing pandas safely for get_history_df
try:
    import pandas as pd

    _PANDAS_AVAILABLE = True
except ImportError:
    _PANDAS_AVAILABLE = False


class NotebookLLMv6:
    """
    Manages LLM interactions in Jupyter/Notebook environments (v6).

    Features:
    - Automatic history rollback on cell rerun (if cell ID detected).
    - Loads personalities from markdown files.
    - Optional default personality & switching (`switch_persona`).
    - Optional default model name set during initialization.
    - Callable instance (`llm("prompt")`).
    - Layered configuration (Personality < Init < Instance < Call).
    - Logs interactions to a file (and optionally console if debug=True).
    - Streaming responses enabled by default (`stream=True`).
    - Manual history management (`revert_last`, `get/set_history`).
    - Optional automatic display (`auto_display`).
    - Saves conversations (`save`).
    - Tags history with execution count and cell ID (if available).
    - Connect to remote LiteLLM/OpenAI-compatible endpoints via overrides.
    - Fetches available models and model details from the endpoint.

    NOTE: The automatic rollback feature DEPENDS on the Jupyter frontend
    injecting a unique, persistent cell identifier into kernel message metadata.
    This may not work in all environments.

    Logging:
    - By default, logs INFO level messages and above to a file (e.g., 'llm_notebook.log').
    - If `debug=True`, logs DEBUG level messages and above to *both* the file and the console.

    Configuration Priority (Lowest to Highest):
    1. Personality File (`config` section)
    2. `default_model_name` provided during `__init__`
    3. Instance Overrides (`set_override`)
    4. Call-specific Keyword Arguments (`chat(..., model="...")`)

    Connecting to Remote Endpoints:
    Use `set_override` or call-specific kwargs to configure LiteLLM:
    ```python
    llm = NotebookLLMv6(default_model_name="fallback_model", debug=True) # Example init
    # Example for a local OpenAI-compatible server
    llm.set_override("api_base", "http://localhost:8000/v1")
    llm.set_override("api_key", "your_api_key_if_needed") # Optional for some servers
    llm.set_override("model", "override_model") # Instance override

    # This call uses "override_model" due to instance override
    response = llm("Hello from remote model!")

    # This call uses "call_specific_model" due to call kwarg
    response = llm("Hi again", model="call_specific_model")

    # If no overrides/kwargs, it would try `default_model_name`
    llm.remove_override("model")
    response = llm("Trying default model") # Uses "fallback_model"

    # Get models from the configured endpoint
    models = llm.get_available_models()
    if models:
        print(f"Available models: {[m['id'] for m in models]}")
        info = llm.get_model_info(models[0]['id'])
        print(f"Info for {models[0]['id']}: {info}")
    ```

    Environment Variables:
    - NBLLM_API_KEY: API key for the LLM service
    - NBLLM_API_BASE: Base URL for the LLM API
    """

    DEFAULT_PERSONAS_DIR = "llm_personas"
    DEFAULT_LOG_FILE = "llm_notebook.log"
    _POTENTIAL_CELL_ID_KEYS = [
        "cellId",
        "vscode_cell_id",
        "google_colab_cell_id",
        "metadata",
    ]

    def __init__(
        self,
        personalities_folder: str = DEFAULT_PERSONAS_DIR,
        default_personality_name: Optional[str] = None,
        default_model_name: Optional[str] = None,  # <<< New: Default model
        save_dir: Optional[str] = "llm_conversations",
        auto_display: bool = True,
        auto_save: bool = False,  # <<< New: Auto-save after each interaction
        autosave_file: Optional[str] = None,  # <<< New: Specific file for auto-saving
        debug: bool = False,  # <<< New: Controls console logging + level
        log_file: str = DEFAULT_LOG_FILE,  # <<< New: Log file path
        api_key: Optional[str] = None,  # New: API key for the LLM service
        api_base: Optional[str] = None,  # New: Base URL for the LLM API
        snippet_folder: str = "snippet",  # <<< New snippet folder parameter
        include_datetime_in_autosave: bool = False,  # <<< New parameter
    ):
        """
        Initializes the NotebookLLMv6 helper.

        Args:
            personalities_folder (str): Path to personality files.
            default_personality_name (Optional[str]): Default personality name.
            default_model_name (Optional[str]): Default model name to use if not
                specified elsewhere (personality, override, call).
            save_dir (Optional[str]): Directory to save conversation logs.
                Set to None to disable saving. Defaults to "llm_conversations".
            auto_display (bool): Automatically call `display_last()` after successful
                interactions. Defaults to True.
            auto_save (bool): Automatically save conversation after each interaction.
                Defaults to False.
            autosave_file (Optional[str]): Base filename (without extension) to use for
                auto-saving. If provided, all auto-saves will update this single file
                rather than creating new files. Defaults to None, which generates a new
                filename on first save.
            debug (bool): If True, enable DEBUG level logging to both file and console.
                          If False (default), enable INFO level logging to file only.
            log_file (str): Path to the log file. Defaults to "llm_notebook.log".
            api_key (Optional[str]): API key for the LLM service. If not provided,
                                    looks for NBLLM_API_KEY environment variable.
            api_base (Optional[str]): Base URL for the LLM API. If not provided,
                                     looks for NBLLM_API_BASE environment variable.
            snippet_folder (str): Path to snippet files. Defaults to "snippet".
            include_datetime_in_autosave (bool): Include datetime in autosave filename.
        """
        self.personalities_folder = personalities_folder
        self.log_file = log_file
        self.debug_mode = debug  # Store debug flag
        self.logger = self._setup_logging(log_file, debug)  # Setup logger first
        self.logger.info("--- Initializing NotebookLLMv6 ---")
        self.logger.debug(f"Debug mode: {debug}")
        self.logger.debug(f"Log file: {log_file}")

        self.auto_display = auto_display
        self.auto_save = auto_save  # Store auto_save setting
        self.autosave_file = autosave_file  # Store fixed filename for auto-saving
        self.include_datetime_in_autosave = (
            include_datetime_in_autosave  # Store the setting
        )

        # If auto_save is enabled and no autosave_file specified, generate a default name
        if auto_save and not autosave_file and save_dir:
            # Generate a fixed autosave filename
            base_filename = "autosave_conversation"
            if self.include_datetime_in_autosave:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename += f"_{timestamp}"
            self.autosave_file = base_filename
            self.logger.info(
                f"Auto-save enabled with default filename: '{self.autosave_file}.md'"
            )
        elif auto_save and autosave_file:
            self.logger.info(
                f"Auto-save enabled with specified filename: '{autosave_file}.md'"
            )
        elif auto_save:
            self.logger.warning(
                "Auto-save enabled but save_dir is None. Auto-save will not work."
            )

        self.default_model_name = default_model_name  # Store default model
        if default_model_name:
            self.logger.info(f"Default model name set: {default_model_name}")
        if auto_save:
            if autosave_file:
                self.logger.info(
                    f"Auto-save enabled: Conversations will be saved to '{autosave_file}.md'"
                )
            else:
                self.logger.info(
                    "Auto-save enabled: Conversations will be saved to auto-generated file"
                )

        self._instance_overrides: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.cell_last_history_index: Dict[str, int] = {}
        self.current_save_file: Optional[str] = None

        # Initialize API credentials from parameters or environment variables
        self._init_api_credentials(api_key, api_base)

        # --- Setup (Personalities, Save Dir) ---
        if not os.path.isdir(self.personalities_folder):
            self.logger.warning(
                f"Personalities folder not found: {os.path.abspath(self.personalities_folder)}. "
                "No personalities loaded."
            )
            self.personalities: Dict[str, Dict[str, Any]] = {}
        else:
            self.personalities = self._load_personalities()

        self.default_personality_name: Optional[str] = None
        if default_personality_name:
            self.set_default_personality(default_personality_name)  # Uses logger inside
        else:
            self.logger.info(
                "No default personality set. Model must be provided via init, overrides, or calls."
            )

        self.save_dir = save_dir
        if self.save_dir:
            try:
                os.makedirs(self.save_dir, exist_ok=True)
                self.logger.info(f"Save directory set to: {self.save_dir}")
            except OSError as e:
                self.save_dir = None
                self.logger.error(
                    f"Error creating save directory '{save_dir}': {e}. Saving disabled.",
                    exc_info=True,  # Add exception details to log
                )
        else:
            self.logger.info("Saving is disabled (save_dir=None).")

        # --- New: Setup Snippet Folder ---
        self.snippet_folder = snippet_folder
        try:
            os.makedirs(self.snippet_folder, exist_ok=True)
            self.logger.info(
                f"Snippet folder set to: {os.path.abspath(self.snippet_folder)}"
            )
        except Exception as e:
            self.logger.error(
                f"Error creating snippet folder '{self.snippet_folder}': {e}"
            )

        self.logger.info("--- Initialization Complete ---")

    def _setup_logging(self, log_file: str, debug: bool) -> logging.Logger:
        """Configures the logger for file and optional console output."""
        logger = logging.getLogger(
            f"NotebookLLMv6_{uuid.uuid4()}"
        )  # Unique logger name
        logger.handlers.clear()  # Prevent duplicate handlers if re-initialized

        log_level = logging.DEBUG if debug else logging.INFO
        logger.setLevel(log_level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # File Handler (always active)
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setLevel(log_level)  # File logs at the determined level
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception as e:
            # Fallback: Log error to stderr if file handler fails
            print(f"CRITICAL: Failed to create file logger at {log_file}: {e}")
            # Set up a basic console handler as a fallback
            ch_fallback = logging.StreamHandler()
            ch_fallback.setLevel(logging.INFO)
            ch_fallback.setFormatter(formatter)
            logger.addHandler(ch_fallback)
            logger.error(
                f"File logging failed. Using console fallback. Error: {e}",
                exc_info=True,
            )

        # Console Handler (only if debug is True)
        if debug:
            ch = logging.StreamHandler()  # Defaults to stderr
            ch.setLevel(logging.DEBUG)  # Console shows DEBUG level if debug is on
            ch.setFormatter(formatter)
            logger.addHandler(ch)

        logger.propagate = False  # Prevent root logger from handling messages again
        return logger

    def _get_context_identifiers(self) -> Tuple[Optional[int], Optional[str]]:
        """Safely gets execution count and attempts to find a persistent cell ID."""
        exec_count: Optional[int] = None
        cell_id: Optional[str] = None

        if not _IPYTHON_AVAILABLE:
            self.logger.debug("IPython not available, cannot get execution context.")
            return exec_count, cell_id

        try:
            ipython = get_ipython()
            if not ipython:
                self.logger.debug("Not running in an IPython environment.")
                return exec_count, cell_id  # Not in IPython

            # Get Execution Count
            if hasattr(ipython, "execution_count"):
                exec_count = ipython.execution_count

            # Get Cell ID
            if (
                hasattr(ipython, "kernel")
                and hasattr(ipython.kernel, "shell")
                and hasattr(ipython.kernel.shell, "parent_header")
                and isinstance(ipython.kernel.shell.parent_header, dict)
            ):
                metadata = ipython.kernel.shell.parent_header.get("metadata", {})
                search_pools = [ipython.kernel.shell.parent_header, metadata]
                if isinstance(metadata.get("metadata"), dict):
                    search_pools.append(metadata["metadata"])
                if isinstance(metadata.get("colab"), dict):
                    search_pools.append(metadata["colab"])

                found_id = False
                for pool in search_pools:
                    if not isinstance(pool, dict):
                        continue
                    for key in self._POTENTIAL_CELL_ID_KEYS:
                        potential_id = pool.get(key)
                        if isinstance(potential_id, str) and potential_id:
                            cell_id = potential_id
                            found_id = True
                            break
                    if found_id:
                        break
                    if not found_id:
                        for value in pool.values():
                            if isinstance(value, str) and value.startswith(
                                "vscode-notebook-cell:"
                            ):
                                cell_id = value
                                found_id = True
                                break
                    if found_id:
                        break

                if cell_id:
                    self.logger.debug(f"Detected Cell ID: {cell_id}")
                else:
                    self.logger.debug(
                        f"Could not detect cell ID from parent_header: {ipython.kernel.shell.parent_header}"
                    )
            else:
                self.logger.debug(
                    "Could not access kernel.shell.parent_header for cell ID."
                )

        except Exception as e:
            self.logger.warning(
                f"Error fetching execution context: {e}", exc_info=self.debug_mode
            )
        # Don't fail, just return None for IDs

        self.logger.debug(
            f"Context Identifiers - Exec Count: {exec_count}, Cell ID: {cell_id}"
        )
        return exec_count, cell_id

    def _load_personalities(self) -> Dict[str, Dict[str, Any]]:
        """Loads personalities from markdown files in the specified folder."""
        loaded = {}
        abs_folder_path = os.path.abspath(self.personalities_folder)
        self.logger.info(f"Loading personalities from: {abs_folder_path}")
        try:
            for filename in os.listdir(self.personalities_folder):
                if filename.lower().endswith(".md"):  # Case-insensitive
                    name = os.path.splitext(filename)[0]
                    filepath = os.path.join(self.personalities_folder, filename)
                    abs_filepath = os.path.abspath(filepath)
                    try:
                        # Read the file content first
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()

                        # Log the raw file content for debugging
                        self.logger.debug(
                            f"Raw file content for '{name}':\n{content[:200]}..."
                        )

                        # Manual YAML frontmatter parsing since we have issues with frontmatter library
                        config = {}
                        system_message = ""

                        if content.startswith("---"):
                            # Find the closing --- marker
                            parts = content[3:].split("---", 1)
                            if len(parts) >= 2:
                                yaml_part = parts[0].strip()
                                try:
                                    config = yaml.safe_load(yaml_part) or {}
                                    system_message = parts[1].strip()
                                except Exception as yaml_err:
                                    self.logger.error(
                                        f"Error parsing YAML frontmatter: {yaml_err}"
                                    )
                            else:
                                # No closing --- found, treat whole content as system message
                                system_message = content.strip()
                        else:
                            # No frontmatter, treat whole content as system message
                            system_message = content.strip()

                        # Log what we extracted
                        self.logger.debug(f"Extracted from '{name}':")
                        self.logger.debug(f"  - Config: {config}")
                        self.logger.debug(
                            f"  - System message ({len(system_message)} chars): {system_message[:50]}..."
                        )

                        name_key = (
                            name.lower()
                        )  # Store with lowercase name for case-insensitive lookup
                        loaded[name_key] = {
                            "config": config,
                            "system_message": system_message,
                            "source_file": abs_filepath,
                            "original_name": name,  # Keep original name for display
                        }
                        self.logger.debug(
                            f"  - Loaded '{name}' (Config: {'Yes' if config else 'No'}, "
                            f"System Msg: {'Yes' if system_message else 'No'}) from {abs_filepath}"
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Error loading personality '{name}' from {abs_filepath}: {e}",
                            exc_info=self.debug_mode,
                        )
        except FileNotFoundError:
            self.logger.warning(f"Personalities directory not found: {abs_folder_path}")
        except Exception as e:
            self.logger.error(
                f"Error listing personalities directory {abs_folder_path}: {e}",
                exc_info=self.debug_mode,
            )

        if not loaded:
            self.logger.info("No personalities were loaded.")
        return loaded

    # --- Personality & Config ---
    def list_personalities(self) -> List[str]:
        """Returns a sorted list of available personality names."""
        # Return original names if available, otherwise the keys
        original_names = [
            p.get("original_name", k) for k, p in self.personalities.items()
        ]
        return sorted(original_names)

    def get_personality_details(self, name: str) -> Optional[Dict[str, Any]]:
        """Gets the configuration and system message for a personality."""
        name_lower = name.lower()  # Case-insensitive lookup
        if name_lower not in self.personalities:
            self.logger.error(f"Personality '{name}' not found.")
            return None
        # Return a copy to prevent external modification
        result = copy.deepcopy(self.personalities.get(name_lower))
        return result

    def set_default_personality(self, name: Optional[str]):
        """Sets the default personality name used by __call__."""
        if name is None:
            self.default_personality_name = None
            self.logger.info("Default personality cleared.")
            return

        name_lower = name.lower()  # Case-insensitive lookup
        if name_lower not in self.personalities:
            abs_folder_path = os.path.abspath(self.personalities_folder)
            self.logger.error(
                f"Personality '{name}' not found in `{abs_folder_path}`. Default not set."
            )
            print(f"Error: Personality '{name}' not found in `{abs_folder_path}`.")
            print(f"Available personalities: {', '.join(self.list_personalities())}")
        else:
            original_name = self.personalities[name_lower].get("original_name", name)
            self.default_personality_name = original_name
            self.logger.info(
                f"Default personality set to: {self.default_personality_name}"
            )

    def switch_persona(self, name: Optional[str]):
        """Alias for set_default_personality."""
        self.set_default_personality(name)

    def set_override(self, key: str, value: Any):
        """Sets an instance-level override for LiteLLM parameters."""
        # Mask secrets: if the secret string is longer than 12 characters,
        # show the first 4 and the last 4 characters; otherwise, show the full string.
        if key in ["api_key", "aws_secret_access_key"] and isinstance(value, str):
            value_repr = value if len(value) <= 16 else value[:4] + "..." + value[-4:]
        else:
            value_repr = value
        self.logger.info(f"[Override] Setting '{key}' = {value_repr}")
        self._instance_overrides[key] = value

    def remove_override(self, key: str):
        """Removes an instance-level override."""
        removed_value = self._instance_overrides.pop(key, None)
        if removed_value is not None:
            self.logger.info(f"[Override] Removed '{key}'")
        else:
            self.logger.debug(f"[Override] Key '{key}' not found, nothing removed.")

    def clear_overrides(self):
        """Removes all instance-level overrides."""
        self._instance_overrides = {}
        self.logger.info("[Override] All instance overrides cleared.")

    def _init_api_credentials(self, api_key: Optional[str], api_base: Optional[str]):
        """Initialize API credentials from parameters or environment variables."""
        # Get API key from parameter or environment variable
        if api_key:
            self.logger.info("Using API key provided in initialization")
            self.set_override("api_key", api_key)
        elif "NBLLM_API_KEY" in os.environ:
            self.logger.info("Using API key from NBLLM_API_KEY environment variable")
            self.set_override("api_key", os.environ["NBLLM_API_KEY"])

        # Get API base from parameter or environment variable
        if api_base:
            self.logger.info(f"Using API base provided in initialization: {api_base}")
            self.set_override("api_base", api_base)
        elif "NBLLM_API_BASE" in os.environ:
            api_base_val = os.environ["NBLLM_API_BASE"]
            self.logger.info(
                f"Using API base from NBLLM_API_BASE environment variable: {api_base_val}"
            )
            self.set_override("api_base", api_base_val)

    def _ensure_model_has_provider(self, model_name: Optional[str]) -> Optional[str]:
        """
        Ensure the model name includes a provider prefix if needed.
        This helps LiteLLM properly identify which provider to use.

        Args:
            model_name: The model name to check and possibly modify

        Returns:
            The model name with provider prefix if needed, or None if input is None
        """
        if not model_name:
            return None

        # Common provider prefixes that LiteLLM recognizes
        known_prefixes = [
            "openai/",
            "anthropic/",
            "google/",
            "azure/",
            "claude/",
            "gpt/",
            "text/",
            "llama/",
            "mistral/",
            "gemini/",
        ]

        # Check if model already has a recognized provider prefix
        if any(model_name.startswith(prefix) for prefix in known_prefixes):
            return model_name

        # Some models like gpt-4, gpt-3.5-turbo don't need prefixes
        # LiteLLM will assume OpenAI for these
        if not any(model_name.startswith(prefix) for prefix in known_prefixes):
            model_name = "openai/" + model_name
            return model_name
        return model_name

    def _determine_model_and_config(
        self, personality_name: Optional[str], call_overrides: Dict
    ) -> Tuple[Optional[str], Dict, Optional[str]]:
        """
        Determines the final model name, configuration dict, and system message
        based on the priority: Call > Instance > Init > Personality.

        Returns:
            Tuple[Optional[str], Dict, Optional[str]]:
                (final_model_name, final_config_dict, system_message_content)
        """
        base_cfg = {}
        personality_model = None
        system_message_content = None

        # 1. Start with Personality (if specified and exists)
        if personality_name:
            # Convert to lowercase for case-insensitive comparison if we modified _load_personalities
            personality_name_lower = personality_name.lower()

            if personality_name_lower not in self.personalities:
                abs_folder_path = os.path.abspath(self.personalities_folder)
                error_msg = f"Personality '{personality_name}' not found in `{abs_folder_path}`."
                self.logger.error(error_msg)
                print(f"Error: {error_msg}")
                raise ValueError(error_msg)  # Raise error to stop chat

            personality_data = self.personalities[personality_name_lower]
            base_cfg = personality_data.get("config", {}).copy()
            personality_model = base_cfg.get(
                "model"
            )  # Get model from personality config
            system_message_content = personality_data.get("system_message")

            # Debug the system message
            self.logger.debug(
                f"Loaded personality '{personality_name}'. System message: '{system_message_content if system_message_content else 'None'}'"
            )
            self.logger.debug(
                f"Loaded base config from personality '{personality_name}'. Model: {personality_model}"
            )

        # 2. Layer configurations (Personality -> Init Model -> Instance -> Call)
        final_config = base_cfg  # Start with personality config
        final_config.update(self._instance_overrides)  # Layer instance overrides
        final_config.update(call_overrides)  # Layer call overrides

        # 3. Determine final model name using priority
        final_model = (
            call_overrides.get("model")  # Highest: Call kwarg
            or self._instance_overrides.get("model")  # Next: Instance override
            or self.default_model_name  # Next: Init default model
            or personality_model  # Lowest: Personality config
        )

        # Ensure the model has a provider prefix if needed
        final_model = self._ensure_model_has_provider(final_model)

        self.logger.debug(
            f"Model Resolution: Call='{call_overrides.get('model')}', Instance='{self._instance_overrides.get('model')}', Init='{self.default_model_name}', Personality='{personality_model}' -> Final='{final_model}'"
        )

        # Remove model from the config dict as it's passed separately to litellm
        final_config.pop("model", None)

        return final_model, final_config, system_message_content

    def chat(
        self,
        prompt: str,
        personality_name: Optional[str] = None,
        **kwargs,
    ) -> Optional[str]:
        """
        Sends a prompt to the LLM and updates history. Handles cell reruns.

        Args:
            prompt (str): The user's message.
            personality_name (Optional[str]): The name of the personality to use.
                If None, uses no specific personality/system message. Relies on
                init `default_model_name`, overrides, or call kwargs for model.
            **kwargs: Additional parameters passed directly to `litellm.completion`,
                      overriding other settings.
                      Special kwargs:
                        - use_history (bool, default True): Send previous messages.
                        - add_to_history (bool, default True): Add this turn to history.
                        - print_config (bool, default False): Log final config before call (at INFO level).
                        - stream (bool, default True): Use streaming response.
                        - auto_save_override (bool): Temporarily override auto_save setting for this call.

        Returns:
            Optional[str]: The assistant's response, or None on error.
        """
        # Start timer for status bar
        start_time = time.time()

        # Pop control kwargs
        use_history = kwargs.pop("use_history", True)
        add_to_history = kwargs.pop("add_to_history", True)
        print_config = kwargs.pop(
            "print_config", False
        )  # Keep for explicit logging trigger
        stream = kwargs.pop("stream", True)  # <<< Default to True
        auto_save_override = kwargs.pop("auto_save_override", None)  # New control param
        call_overrides = kwargs  # Remaining kwargs are for litellm

        self.logger.debug(
            f"Chat called with prompt: '{prompt[:50]}...', personality: {personality_name}, stream: {stream}, use_history: {use_history}, add_to_history: {add_to_history}"
        )
        self.logger.debug(
            f"Call overrides: { {k: v for k, v in call_overrides.items() if k not in ['api_key']} }"
        )  # Avoid logging key

        # *** Cell ID Handling & Rollback ***
        exec_count, cell_id = self._get_context_identifiers()
        history_rolled_back = False
        if cell_id is not None and cell_id in self.cell_last_history_index:
            previous_end_index = self.cell_last_history_index[cell_id]
            if (
                0 <= previous_end_index < len(self.history)
                and self.history[previous_end_index]["role"] == "assistant"
            ):
                start_index_of_previous_turn = previous_end_index - 1
                if start_index_of_previous_turn >= 0:
                    self.logger.info(
                        f"Cell Rerun Detected (ID: ...{cell_id[-20:]}). Previous turn ended at index {previous_end_index}."
                    )
                    self.logger.info(
                        f"Rolling back history to before index {start_index_of_previous_turn}."
                    )
                    self.history = self.history[:start_index_of_previous_turn]
                    del self.cell_last_history_index[cell_id]  # Remove cell tracking
                    history_rolled_back = True
                    self.current_save_file = None  # History changed
                else:
                    self.logger.warning(
                        f"Invalid calculated start index {start_index_of_previous_turn} for cell {cell_id}. Not rolling back."
                    )
            else:
                self.logger.warning(
                    f"Stored history index {previous_end_index} for cell {cell_id} is invalid or role mismatch. Clearing tracking."
                )
                del self.cell_last_history_index[cell_id]
        # *** End Rollback Logic ***

        try:
            # --- Determine Model, Config, System Message ---
            # This method handles the priority logic and potential errors
            final_model, final_config, system_message_content = (
                self._determine_model_and_config(personality_name, call_overrides)
            )

            # --- Validate Final Model ---
            if not final_model:
                error_msg = "LLM model name is missing. Specify via 'default_model_name' in init, personality, 'set_override', or call arguments."
                self.logger.error(error_msg)
                return None

            self.logger.debug(f"Final model for call: {final_model}")

            # --- Prepare messages list ---
            messages = []
            if system_message_content:
                messages.append({"role": "system", "content": system_message_content})
                self.logger.debug(
                    f"Added system message: {system_message_content[:50]}..."
                )
            else:
                self.logger.debug("No system message added (none provided)")

            # Modified: Include snippet messages even if role is "system"
            history_to_use = [
                msg
                for msg in self.history
                if msg["role"] != "system" or msg.get("is_snippet")
            ]
            if use_history and history_to_use:
                messages.extend(history_to_use)
                self.logger.debug(f"Added {len(history_to_use)} messages from history.")

            messages.append({"role": "user", "content": prompt})
            self.logger.debug("Added current user prompt.")
            # --- End Prepare ---

            if (
                print_config or self.debug_mode
            ):  # Log config if requested or if debugging
                self._log_config_details(
                    final_model,
                    final_config,
                    system_message_content,
                    len(messages)
                    - (1 if system_message_content else 0)
                    - 1,  # History msgs count
                )

            # --- Call LangChain Chat Model ---
            self.logger.info(
                f"Calling model '{final_model}' with {len(messages)} total messages (stream={stream})..."
            )

            try:
                from langchain_core.messages import (
                    AIMessage,
                    HumanMessage,
                    SystemMessage,
                )
                from langchain_community.chat_models import ChatLiteLLM

                # Get API key and base from instance overrides, or environment variables
                api_key = final_config.pop("api_key", os.environ.get("NBLLM_API_KEY"))
                api_base = final_config.pop(
                    "api_base", os.environ.get("NBLLM_API_BASE")
                )

                # Convert our messages to LangChain message objects
                converted_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        converted_messages.append(SystemMessage(content=msg["content"]))
                    elif msg["role"] == "user":
                        converted_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        converted_messages.append(AIMessage(content=msg["content"]))

                # Create a ChatLiteLLM instance using the final model name and overrides.
                llm_kwargs = {}
                if api_key:
                    llm_kwargs["api_key"] = api_key  # Standardize to OpenAI key name
                if api_base:
                    llm_kwargs["api_base"] = api_base  # Standardize to OpenAI base name

                # Pass remaining parameters to the llm
                llm_kwargs.update(final_config)

                chat_client = ChatLiteLLM(model=final_model, **llm_kwargs)

                # Invoke the model with our converted messages.
                if stream:
                    self.logger.debug("Processing stream...")
                    full_response = ""
                    chunk_count = 0
                    live_display_active = False

                    # Setup display area only if IPython available and auto_display is on
                    if _IPYTHON_AVAILABLE and self.auto_display:
                        try:
                            # Initial display before content arrives
                            output_area = display(
                                Markdown("**Assistant (Streaming):**\n"),
                                display_id=True,
                            )
                            live_display_active = True
                            self.logger.debug(
                                "IPython display area created for streaming."
                            )
                        except Exception as ipy_e:
                            self.logger.warning(
                                f"Failed to create IPython display area: {ipy_e}",
                                exc_info=self.debug_mode,
                            )
                            # Fallback to console/log streaming if display fails
                            if not self.debug_mode:  # Only print fallback if not debugging (debug logs to console anyway)
                                print("Assistant (Streaming): ", end="", flush=True)

                    elif (
                        not self.debug_mode
                    ):  # Not debugging and IPython unavailable/auto_display off
                        # Print stream start indicator to console if not debugging
                        print("Assistant (Streaming): ", end="", flush=True)

                    try:
                        for chunk in chat_client.stream(converted_messages):
                            chunk_count += 1
                            content_chunk = chunk.content or ""
                            full_response += content_chunk

                            if live_display_active and output_area:
                                try:
                                    output_area.update(
                                        Markdown(f"**Assistant:**\n{full_response}")
                                    )  # Update display
                                except Exception as ipy_e:
                                    self.logger.warning(
                                        f"Failed to update IPython display: {ipy_e}. Disabling live display.",
                                        exc_info=self.debug_mode,
                                    )
                                    live_display_active = (
                                        False  # Stop trying to update display
                                    )
                                    if (
                                        chunk_count == 1
                                    ):  # If first chunk failed display, print indicator
                                        print(
                                            "Assistant (Streaming - Display Failed): ",
                                            end="",
                                            flush=True,
                                        )
                                    print(
                                        content_chunk, end="", flush=True
                                    )  # Print current chunk

                            elif not self.debug_mode:  # No live display, not debugging -> print chunk to console
                                print(content_chunk, end="", flush=True)
                            # If debugging, chunks are implicitly logged via StreamHandler, no need to print here

                        # Add a newline if we were printing directly to the console
                        if (
                            not _IPYTHON_AVAILABLE or not live_display_active
                        ) and not self.debug_mode:
                            print()

                        ai_response = full_response.strip()
                        self.logger.debug(
                            f"Stream finished ({chunk_count} chunks). Total length: {len(ai_response)}"
                        )

                    except Exception as e:
                        self.logger.exception(f"Error during streaming: {e}")
                        return None

                else:
                    response_obj = chat_client.invoke(converted_messages)
                    ai_response = (
                        response_obj.content.strip()
                        if response_obj and hasattr(response_obj, "content")
                        else None
                    )

                self.logger.debug("LangChain chat call returned.")
            except Exception as e:
                self.logger.exception(f"Error during LangChain chat call: {e}")
                return None

            # --- Process Response ---
            if ai_response is None:
                self.logger.warning(
                    "LLM interaction resulted in None response after processing."
                )
                return None  # Propagate None if processing failed

            # --- Update History (if enabled) ---
            if add_to_history:
                user_msg_id = str(uuid.uuid4())
                assistant_msg_id = str(uuid.uuid4())
                start_index_for_turn = len(self.history)

                user_msg = {
                    "role": "user",
                    "content": prompt,
                    "id": user_msg_id,
                    "execution_count": exec_count,
                    "cell_id": cell_id,
                }
                assistant_msg = {
                    "role": "assistant",
                    "content": ai_response,
                    "id": assistant_msg_id,
                    "execution_count": exec_count,
                    "cell_id": cell_id,
                }
                self.history.append(user_msg)
                self.history.append(assistant_msg)
                self.logger.debug(
                    f"Added user/assistant pair to history (indices {start_index_for_turn}, {start_index_for_turn + 1})."
                )

                # *** Update Cell Tracking ***
                if cell_id is not None:
                    current_end_index = len(self.history) - 1
                    self.cell_last_history_index[cell_id] = current_end_index
                    self.logger.debug(
                        f"Updated tracking for Cell ID ...{cell_id[-20:]} to history index {current_end_index}."
                    )

                self.current_save_file = None  # History modified, invalidate save link

                # Auto-display if enabled
                if self.auto_display:
                    self.display_last()

                # Auto-save if enabled (and save_dir exists)
                should_auto_save = (
                    self.auto_save if auto_save_override is None else auto_save_override
                )
                if should_auto_save and self.save_dir:
                    saved_path = self.save(
                        filename=self.autosave_file
                    )  # Use autosave_file if provided
                    if saved_path:
                        self.logger.info(f"Auto-saved conversation to: {saved_path}")
                    else:
                        self.logger.warning("Auto-save failed")

            self.logger.info(f"Chat completed. Response length: {len(ai_response)}")

            # --- Display Status Bar ---
            end_time = time.time()
            duration = end_time - start_time
            token_in = len(prompt.split())
            token_out = len(ai_response.split())
            # Calculate cost in millicents (1 token = 1 millicent)
            cost_mili_cents = token_out

            # Determine display unit based on the cost value
            if cost_mili_cents < 100000:
                cost_str = f"{cost_mili_cents / 1000:.2f} cents"
            else:
                cost_str = f"{cost_mili_cents / 100000:.2f} USD"

            succeeded = True  # Chat succeeded if we reached here
            if succeeded:
                status_text = (
                    f"✅ Success! Ran in {duration:.2f}s. "
                    f"Tokens In: {token_in}, Tokens Out: {token_out}, Cost: {cost_str}"
                )
                bg_color = "#2e7d32"  # Dark green background
                border_color = "#1b5e20"  # Darker green border
                text_color = "#ffffff"  # White text
            else:
                status_text = (
                    f"⚠️ Warning! Ran in {duration:.2f}s. "
                    f"Tokens In: {token_in}, Tokens Out: {token_out}, Cost: {cost_str}"
                )
                bg_color = "#c62828"  # Dark red background
                border_color = "#8e0000"  # Darker red border
                text_color = "#ffffff"  # White text

            status_html = f"""
            <div style="
                background-color: {bg_color};
                border: 1px solid {border_color};
                color: {text_color};
                padding: 8px;
                margin-top: 10px;
                border-radius: 4px;
                font-family: sans-serif;
            ">
                {status_text}
            </div>
            """
            if _IPYTHON_AVAILABLE:
                display(HTML(status_html))
            else:
                print(status_text)
            # --- End Display Status Bar ---

            return ai_response

        except ValueError as e:  # Catch specific error from _determine_model_and_config
            self.logger.error(f"Configuration error: {e}")
            return None
        except litellm.exceptions.AuthenticationError as e:
            self.logger.error(
                f"LiteLLM Authentication Error: {e}. Check API key/base.",
                exc_info=self.debug_mode,
            )
            return None
        except litellm.exceptions.APIConnectionError as e:
            self.logger.error(
                f"LiteLLM Connection Error: {e}. Check API base/network.",
                exc_info=self.debug_mode,
            )
            return None
        except litellm.exceptions.NotFoundError as e:
            self.logger.error(
                f"LiteLLM Not Found Error (likely model): {e}. Model='{final_model}'",
                exc_info=self.debug_mode,
            )
            return None
        except litellm.exceptions.RateLimitError as e:
            self.logger.error(
                f"LiteLLM Rate Limit Error: {e}", exc_info=self.debug_mode
            )
            return None
        except litellm.exceptions.APIError as e:  # Catch broader API errors
            self.logger.error(
                f"LiteLLM API Response Error: Status={e.status_code}, Message={e}",
                exc_info=self.debug_mode,
            )
            return None
        except Exception as e:
            self.logger.exception(
                f"Unexpected error during chat: {e}"
            )  # Logs traceback if debug
            return None

    def __call__(self, prompt: str, **kwargs) -> Optional[str]:
        kwargs.setdefault("use_history", True)
        kwargs.setdefault("add_to_history", True)
        # strip prompt to remove leading/trailing whitespace and break lines
        prompt = prompt.strip()
        result = self.chat(
            prompt=prompt,
            personality_name=self.default_personality_name,  # Pass default (can be None)
            **kwargs,
        )
        try:
            import inspect

            frame = inspect.currentframe().f_back
            code_line = inspect.getframeinfo(frame).code_context[0].strip()
            # If the caller's line does not contain an '=' (i.e. no assignment),
            # assume the value is not being captured and return None.
            if "=" not in code_line:
                return None
        except Exception:
            pass
        return result

    def _log_config_details(
        self, model: str, config: Dict, system_msg: Optional[str], history_len: int
    ):
        """Helper to log configuration details at INFO level."""
        log_level = logging.INFO  # Use INFO so it shows up even if not debugging
        self.logger.log(log_level, "--- LLM Call Configuration ---")
        self.logger.log(log_level, f"Model: {model}")
        self.logger.log(log_level, f"System Message: {'Yes' if system_msg else 'No'}")
        # Mask secrets in logged config
        safe_config = {
            k: v if k not in ["api_key", "aws_secret_access_key"] else "********"
            for k, v in config.items()
        }
        self.logger.log(log_level, f"Effective LiteLLM Params: {safe_config}")
        self.logger.log(log_level, f"History messages sent: {history_len}")
        self.logger.log(log_level, "-----------------------------")

    def _process_response(self, response, stream: bool) -> Optional[str]:
        """Handles both streaming and non-streaming responses from LiteLLM."""
        ai_response_content = None
        output_area = None  # For IPython display updates
        try:
            if stream:
                self.logger.debug("Processing stream...")
                full_response = ""
                chunk_count = 0
                live_display_active = False

                # Setup display area only if IPython available and auto_display is on
                if _IPYTHON_AVAILABLE and self.auto_display:
                    try:
                        # Initial display before content arrives
                        output_area = display(
                            Markdown("**Assistant (Streaming):**\n"), display_id=True
                        )
                        live_display_active = True
                        self.logger.debug("IPython display area created for streaming.")
                    except Exception as ipy_e:
                        self.logger.warning(
                            f"Failed to create IPython display area: {ipy_e}",
                            exc_info=self.debug_mode,
                        )
                        # Fallback to console/log streaming if display fails
                        if not self.debug_mode:  # Only print fallback if not debugging (debug logs to console anyway)
                            print("Assistant (Streaming): ", end="", flush=True)

                elif (
                    not self.debug_mode
                ):  # Not debugging and IPython unavailable/auto_display off
                    # Print stream start indicator to console if not debugging
                    print("Assistant (Streaming): ", end="", flush=True)

                for chunk in response:
                    chunk_count += 1
                    delta = chunk.choices[0].delta
                    content_chunk = delta.content or ""

                    if content_chunk:
                        full_response += content_chunk
                        if live_display_active and output_area:
                            try:
                                output_area.update(
                                    Markdown(f"**Assistant:**\n{full_response}")
                                )  # Update display
                            except Exception as ipy_e:
                                self.logger.warning(
                                    f"Failed to update IPython display: {ipy_e}. Disabling live display.",
                                    exc_info=self.debug_mode,
                                )
                                live_display_active = (
                                    False  # Stop trying to update display
                                )
                                # Print the rest to console if display fails mid-stream
                                if (
                                    chunk_count == 1
                                ):  # If first chunk failed display, print indicator
                                    print(
                                        "Assistant (Streaming - Display Failed): ",
                                        end="",
                                        flush=True,
                                    )
                                print(
                                    content_chunk, end="", flush=True
                                )  # Print current chunk

                        elif (
                            not self.debug_mode
                        ):  # No live display, not debugging -> print chunk to console
                            print(content_chunk, end="", flush=True)
                        # If debugging, chunks are implicitly logged via StreamHandler, no need to print here

                # Add a newline if we were printing directly to the console
                if (
                    not _IPYTHON_AVAILABLE or not live_display_active
                ) and not self.debug_mode:
                    print()

                ai_response_content = full_response.strip()
                self.logger.debug(
                    f"Stream finished ({chunk_count} chunks). Total length: {len(ai_response_content)}"
                )

            else:  # Non-streaming
                self.logger.debug("Processing non-streamed response...")
                if response.choices and response.choices[0].message:
                    ai_response_content = response.choices[0].message.content
                    if ai_response_content:
                        ai_response_content = ai_response_content.strip()
                    self.logger.debug(
                        f"Non-streamed response received. Length: {len(ai_response_content or '')}"
                    )
                else:
                    self.logger.warning(
                        f"Non-streamed response structure unexpected: {response}"
                    )
                    try:  # Defensive attempt
                        ai_response_content = response.choices[
                            0
                        ].message.content.strip()
                    except (AttributeError, IndexError, TypeError):
                        ai_response_content = str(response)  # Fallback

        except Exception as e:
            self.logger.error(
                f"Error processing LLM response: {e}", exc_info=self.debug_mode
            )
            ai_response_content = None  # Indicate failure

        return ai_response_content

    # --- Display and Saving ---
    def display_last(self):
        """Displays the last user/assistant interaction using IPython Markdown if available."""
        if not self.history or len(self.history) < 2:
            self.logger.debug("History too short to display last turn.")
            return

        last_user_msg = self.history[-2]
        last_assistant_msg = self.history[-1]

        if (
            last_user_msg.get("role") == "user"
            and last_assistant_msg.get("role") == "assistant"
        ):
            last_user = last_user_msg.get("content", "*No content*")
            last_assistant = last_assistant_msg.get("content", "*No content*")
            if _IPYTHON_AVAILABLE:
                try:
                    # Don't display if streaming already handled it (unless stream failed)
                    # Heuristic: Check if last assistant message seems short/incomplete (might indicate stream failure)
                    # This isn't perfect, but avoids double display in most cases.
                    # A better approach might involve passing state from _process_response.
                    # For now, we rely on auto_display=True handling stream output.
                    # We only explicitly display here if auto_display is OFF, or if stream might have failed.
                    # Simpler: Only call display_last if auto_display=False OR stream=False
                    # We can't easily know stream setting here. Let's assume if auto_display=True,
                    # the stream handled it.
                    if not self.auto_display:
                        display(
                            Markdown(
                                f"**You:** {last_user}\n\n**Assistant:**\n{last_assistant}"
                            )
                        )
                        self.logger.debug("Displayed last turn via display_last().")
                    else:
                        self.logger.debug(
                            "Auto-display is True, skipping redundant display_last() call (stream likely handled it)."
                        )

                except Exception as e:
                    self.logger.error(
                        f"Error using IPython display: {e}", exc_info=self.debug_mode
                    )
                    # Fallback print if display fails
                    print(f"You: {last_user}\n\nAssistant:\n{last_assistant}")
            else:
                # Fallback print if IPython not available
                print(f"You: {last_user}\n\nAssistant:\n{last_assistant}")
        else:
            self.logger.debug("Last two history entries are not a user/assistant pair.")

    def show_history(
        self, n: int = 0, show_exec_count: bool = False, show_cell_id: bool = False
    ):
        """
        Displays the chat history using IPython Markdown (or print).

        Args:
            n (int): Show the last 'n' turns (user + assistant). 0 shows all.
            show_exec_count (bool): Include execution count in output.
            show_cell_id (bool): Include truncated cell ID in output.
        """
        if not self.history:
            print("History is empty.")  # Use print for direct user feedback here
            self.logger.info("show_history called but history is empty.")
            return

        num_messages_to_show = n * 2 if n > 0 else len(self.history)
        display_history = self.history[-num_messages_to_show:]
        self.logger.info(f"Displaying last {len(display_history)} messages ({n=}).")

        output_parts = ["## Chat History\n"]
        for i, msg in enumerate(display_history):
            role = msg.get("role", "Unknown").capitalize()
            content = msg.get("content", "*No content*")
            context = []

            if show_exec_count and msg.get("execution_count") is not None:
                context.append(f"Exec: {msg['execution_count']}")
            if show_cell_id and msg.get("cell_id"):
                cell_id_short = (
                    f"...{msg['cell_id'][-20:]}"
                    if len(msg["cell_id"]) > 20
                    else msg["cell_id"]
                )
                context.append(f"Cell: {cell_id_short}")

            context_str = f" ({', '.join(context)})" if context else ""
            role_prefix = "**You**" if role == "User" else f"**{role}**"

            if role == "User":
                output_parts.append(f"> {role_prefix}{context_str}: {content}\n")
            else:
                output_parts.append(f"{role_prefix}{context_str}:\n{content}\n")

            if role == "Assistant" and i < len(display_history) - 1:
                output_parts.append("---\n")  # Separator after assistant

        full_output = "\n".join(output_parts)

        if _IPYTHON_AVAILABLE:
            try:
                display(Markdown(full_output))
            except Exception as e:
                self.logger.error(
                    f"Error using IPython display for history: {e}",
                    exc_info=self.debug_mode,
                )
                print(full_output)  # Fallback print
        else:
            print(full_output)  # Print if no IPython

    def save(
        self, filename: Optional[str] = None, include_config: bool = True
    ) -> Optional[str]:
        """
        Saves the conversation history to a Markdown file with YAML frontmatter.
        If auto_save is enabled or a filename is provided, it will overwrite
        any existing file with the same name.

        Args:
            filename (Optional[str]): Base filename (no extension). Auto-generates if None.
                Reuses autosave_file if available and filename is None.
            include_config (bool): Include default personality's config in frontmatter.

        Returns:
            Optional[str]: Full path to the saved file, or None on error.
        """
        if not self.save_dir:
            self.logger.error("Save failed: Saving is disabled (save_dir not set).")
            return None
        if not self.history:
            self.logger.warning("Save skipped: History is empty.")
            return None

        # Determine filename
        if filename is None:
            # Use the autosave_file if it exists
            if self.autosave_file:
                filename = self.autosave_file
                self.logger.debug(f"Using autosave filename: {filename}")
            # Otherwise generate a new one (for manual saves)
            else:
                now = datetime.now().strftime("%Y%m%d_%H%M%S")
                first_words = "_".join(self.history[0]["content"].split()[:5])
                safe_first_words = "".join(
                    c if c.isalnum() or c in ["_"] else "" for c in first_words
                )
                filename = (
                    f"chat_{now}_{safe_first_words if safe_first_words else 'empty'}"
                )
                self.logger.debug(f"Generated filename base: {filename}")

        base_filename = filename
        full_path = os.path.join(self.save_dir, f"{base_filename}.md")

        # Prepare frontmatter
        metadata = {
            "saved_at": datetime.now().isoformat(),
            "total_messages": len(self.history),
            "turns": len(self.history) // 2,
            "default_model_used_in_init": self.default_model_name,
            "default_personality_name": self.default_personality_name,
        }
        if include_config and self.default_personality_name:
            p_details = self.get_personality_details(self.default_personality_name)
            if p_details and p_details.get("config"):
                metadata["personality_config"] = p_details["config"]
            else:
                self.logger.debug(
                    f"Default personality '{self.default_personality_name}' has no config to save."
                )

        exec_counts = sorted(
            list(
                set(
                    m.get("execution_count")
                    for m in self.history
                    if m.get("execution_count") is not None
                )
            )
        )
        cell_ids = sorted(
            list(
                set(
                    m.get("cell_id")
                    for m in self.history
                    if m.get("cell_id") is not None
                )
            )
        )
        if exec_counts:
            metadata["execution_counts"] = exec_counts
        if cell_ids:
            metadata["cell_ids_present"] = len(cell_ids)

        # Prepare content
        content_parts = []
        # Prepend system message from default personality if available
        if self.default_personality_name:
            p_details = self.get_personality_details(self.default_personality_name)
            system_message = (
                p_details.get("system_message", "").strip() if p_details else ""
            )
            if system_message:
                content_parts.append("**System:**\n" + system_message + "\n\n---\n")

        for msg in self.history:
            role = msg.get("role", "unknown").capitalize()
            text = msg.get("content", "*No content*")
            prefix = f"**{role}:**"
            if role == "User":
                prefix = "**You:**"  # Friendlier alias

            content_parts.append(f"{prefix}\n{text}\n")
            if role != "User":  # Add separator after assistant/system
                content_parts.append("---\n")

        content = "\n".join(content_parts)

        try:
            # Direct writing instead of using potentially problematic frontmatter library
            with open(full_path, "w", encoding="utf-8") as f:
                # Write YAML frontmatter
                f.write("---\n")
                yaml.dump(metadata, f, default_flow_style=False)
                f.write("---\n\n")

                # Write content
                f.write(content.strip())

            self.current_save_file = full_path
            self.logger.info(f"Conversation saved successfully to: {full_path}")
            return full_path

        except Exception as e:
            self.logger.error(
                f"Error saving conversation to {full_path}: {e}",
                exc_info=self.debug_mode,
            )
            return None

    def get_history_df(self) -> Optional["pd.DataFrame"]:
        """
        Returns history as a pandas DataFrame (if pandas is available).
        """
        if not _PANDAS_AVAILABLE:
            self.logger.error(
                "pandas library is required for get_history_df(). Please install pandas."
            )
            return None
        if not self.history:
            self.logger.info("History is empty, returning empty DataFrame.")
            return pd.DataFrame(
                columns=["execution_count", "cell_id", "role", "content", "id"]
            )

        history_copy = self.get_history()
        df = pd.DataFrame(history_copy)
        for col in ["execution_count", "cell_id", "role", "content", "id"]:
            if col not in df.columns:
                df[col] = None
        df = df[["execution_count", "cell_id", "role", "content", "id"]]
        return df

    # --- New Model Information Methods ---

    def get_available_models(self, **kwargs) -> Optional[List[Dict]]:
        """
        Fetches the list of available models from the configured LiteLLM endpoint.

        Makes a direct API call to the /v1/models endpoint of the configured API base.
        Uses instance overrides (like api_base, api_key) if they are set.
        Any additional kwargs are passed to the request.

        Returns:
            Optional[List[Dict]]: A list of model dictionaries from the server,
                                 or None if an error occurs.
        """
        self.logger.info("Attempting to fetch available models from endpoint...")

        # Get configuration using instance overrides + call kwargs
        config = self._instance_overrides.copy()
        config.update(kwargs)

        # Extract critical parameters for API call
        api_base = config.get("api_base")
        api_key = config.get("api_key")

        if not api_base:
            self.logger.error("Cannot fetch models: No API base URL configured")
            return None

        # Ensure the api_base ends with /v1 for OpenAI compatibility
        if not api_base.endswith("/v1"):
            if api_base.endswith("/"):
                api_base = f"{api_base}v1"
            else:
                api_base = f"{api_base}/v1"

        # Construct the models endpoint URL
        models_url = f"{api_base}/models"
        self.logger.debug(f"Requesting models from: {models_url}")

        try:
            import requests

            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            response = requests.get(models_url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise exception for non-200 responses

            models_data = response.json()

            if "data" in models_data and isinstance(models_data["data"], list):
                self.logger.info(
                    f"Successfully fetched {len(models_data['data'])} models from endpoint."
                )
                self.logger.debug(f"Available models data: {models_data['data']}")
                return models_data["data"]
            else:
                self.logger.warning(
                    f"Unexpected response format from models endpoint: {models_data}"
                )
                return None

        except requests.RequestException as e:
            self.logger.error(
                f"Error fetching models from endpoint: {e}", exc_info=self.debug_mode
            )
            return None
        except Exception as e:
            self.logger.exception(f"Unexpected error fetching available models: {e}")
            return None

    def get_model_info(self, model_name: str, **kwargs) -> Optional[Dict]:
        """
        Fetches detailed information for a specific model from the configured endpoint.

        Uses instance overrides (like api_base, api_key) if they are set.
        Any additional kwargs are passed to litellm.get_model_info.

        Args:
            model_name (str): The name of the model to query.
            **kwargs: Additional keyword arguments for litellm.get_model_info.

        Returns:
            Optional[Dict]: A dictionary containing model information, or None on error.
        """
        self.logger.info(f"Attempting to fetch info for model: {model_name}")
        # Prepare config using instance overrides + call kwargs
        config = self._instance_overrides.copy()
        config.update(kwargs)
        # Ensure 'model' is not passed in the config dict itself for get_model_info
        config.pop("model", None)
        self.logger.debug(
            f"Using config for get_model_info: { {k: v for k, v in config.items() if k != 'api_key'} }"
        )

        try:
            model_info = litellm.get_model_info(model=model_name, **config)
            self.logger.info(f"Successfully fetched info for model '{model_name}'.")
            # Ensure it's a dictionary before returning
            if isinstance(model_info, dict):
                self.logger.debug(f"Model info for '{model_name}': {model_info}")
                return model_info
            else:
                self.logger.warning(
                    f"litellm.get_model_info returned unexpected type: {type(model_info)}. Converting to string."
                )
                return {"info": str(model_info)}  # Basic fallback
        except (
            litellm.exceptions.BadRequestError,
            litellm.exceptions.APIError,
            litellm.exceptions.AuthenticationError,
            litellm.exceptions.RateLimitError,
            litellm.exceptions.ServiceUnavailableError,
        ) as e:
            # Use specific litellm exception types instead of LiteLLMException
            self.logger.error(
                f"LiteLLM error fetching info for model '{model_name}': {e}",
                exc_info=self.debug_mode,
            )
            return None
        except Exception as e:
            self.logger.exception(
                f"Unexpected error fetching info for model '{model_name}': {e}"
            )
            return None

    def add_snippet_message(self, snippet_filename: str, role: str = "system") -> bool:
        """
        Loads a snippet file from the snippet folder and adds its content as a message to history.
        Role must be one of "system", "user", or "assistant".
        If the filename does not have an extension, it is assumed to be a .md file.

        Returns:
            True if snippet added successfully, False otherwise.
        """
        valid_roles = {"system", "user", "assistant"}
        if role not in valid_roles:
            self.logger.error(
                f"Invalid role '{role}' for snippet. Valid roles are: {valid_roles}."
            )
            return False

        # If no extension is provided, assume .md
        if not os.path.splitext(snippet_filename)[1]:
            snippet_filename += ".md"

        full_path = os.path.join(self.snippet_folder, snippet_filename)
        if not os.path.isfile(full_path):
            self.logger.error(f"Snippet file not found: {full_path}.")
            return False

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self.logger.error(f"Error reading snippet file '{full_path}': {e}")
            return False

        message = {
            "role": role,
            "content": content,
            "id": str(uuid.uuid4()),
            "execution_count": None,
            "cell_id": None,
            "is_snippet": True,  # Added flag to identify snippet messages
        }
        # Insert the snippet at the beginning of history so it is included in the conversation context
        self.history.insert(0, message)
        self.logger.info(
            f"Added snippet from '{snippet_filename}' as a {role} message to history."
        )
        return True


import os
import sys  # Make sure sys is imported if used in generated code
from IPython.core.magic import Magics, magics_class, cell_magic, line_magic
from IPython.core.magic_arguments import magic_arguments, argument, parse_argstring
from IPython.display import (
    display,
    Markdown,
)  # Assuming these are needed by NotebookLLMv6/display

# ==============================================================
# Transformer Function (Stays OUTSIDE the class)
# ==============================================================


def _auto_magic_transformer(lines):
    """
    Input transformer injects Python code to find the Magics instance
    and call its _perform_auto_processing method. Uses repr() for safe
    code embedding.
    """
    if not lines:
        return lines  # Empty cell

    # Don't transform if it's already a magic command
    first_line_stripped = lines[0].lstrip()
    if first_line_stripped.startswith("%"):
        return lines

    original_code = "\n".join(lines)

    # Use repr() to create a safe, escaped string literal representation
    # This handles all special characters correctly for Python syntax.
    escaped_code_literal = repr(original_code)

    # Line arguments are not typically used in this implicit scenario, pass empty
    line_args = ""  # Keep as an empty string

    # Generate Python code to find the registered instance and call its method
    # Pass the repr()'d string directly - it includes the necessary quotes and escapes.
    # Ensure 'sys' is imported within the generated code if stderr is used.
    # Use double curly braces {{e}} to escape the f-string evaluation for the exception message.
    new_lines = [
        f"""
try:
    # Make imports available inside the executed code block if needed
    import sys
    ip_shell = get_ipython()
    magics_instance = ip_shell.magics_manager.registry.get('NotebookLLMMagics')
    if magics_instance:
        # Pass the result of repr() directly. It's already a valid string literal.
        # Also pass line_args safely (it's just an empty string here).
        magics_instance._perform_auto_processing(ip_shell, {escaped_code_literal}, '{line_args}')
    else:
        print('Error: Could not find registered NotebookLLMMagics instance.', file=sys.stderr)
except Exception as e:
    # Ensure sys is available here too
    import sys
    print(f'Error during auto-processing lookup/call: {{e}}', file=sys.stderr)"""
    ]
    # print(
    #     f"[Transformer injecting code using repr()]", file=sys.stderr
    # ) # Debug msg
    return new_lines


@magics_class
class NotebookLLMMagics(Magics):
    def __init__(self, shell):
        super(NotebookLLMMagics, self).__init__(shell)

        default_model = os.getenv("DEFAULT_MODEL", "fallback-model")
        # Instantiate NotebookLLM with a default model from env (or fallback) and default debug False
        self.llm = NotebookLLMv6(default_model_name=default_model, debug=False)

    def _perform_auto_processing(self, ipython_shell, cell_content, line_args=""):
        """
        The actual processing logic, now an instance method.
        Calls self.llm with the cell content using current defaults.
        """
        stream = True
        if self.llm is None:
            print(
                "Error: LLM object not initialized. Cannot auto-process.",
                file=sys.stderr,
            )
            return

        # print(f"--- Auto Processing Cell (Instance Method) ---")
        # # print(f"Args received by helper: '{line_args}'") # Usually empty here
        # print("Processing Content:\n---")
        # print(cell_content)
        # print("---")
        prompt = cell_content.strip()
        if not prompt:
            print("Skipping empty prompt.", file=sys.stderr)
            return

        # Mimic the core logic of the %%llm magic, but without parsing 'line' args
        # Use default settings stored in self.llm, assume streaming display
        try:
            # Store and set debug state specifically for this implicit call if needed
            # original_debug = self.llm.debug
            # self.llm.debug = False # Or True, depending on desired implicit behavior

            # Call the llm instance (assuming it's callable like in %%llm)
            # Use default stream=True for display
            result = self.llm(prompt, stream=stream)

            # Reset debug state if changed
            # self.llm.debug = original_debug

            # Display result
            if result is not None and not stream:
                # Ensure result is string before passing to Markdown
                display(Markdown(str(result)))

        except Exception as e:
            print(f"Error during LLM call in auto-processing: {e}", file=sys.stderr)

    @magic_arguments()
    @argument(
        "--default_model", type=str, help="Set default model for NotebookLLM instance"
    )
    @argument(
        "--persona", type=str, help="Set default personality for NotebookLLM instance"
    )
    @argument("--personas_folder", type=str, help="Set the personalities folder")
    @argument("--save_dir", type=str, help="Set the save directory for conversations")
    @argument("--auto_display", action="store_true", help="Enable auto display")
    @argument("--auto_save", action="store_true", help="Enable auto save")
    @argument("--autosave_file", type=str, help="Specify autosave file name")
    @argument("--log_file", type=str, help="Specify log file for logging")
    @argument("--api_key", type=str, help="Set API key for LLM service")
    @argument("--api_base", type=str, help="Set base URL for LLM API")
    @argument("--snippet_folder", type=str, help="Set the snippet folder")
    @argument(
        "--include_datetime_in_autosave",
        action="store_true",
        help="Include datetime in autosave file name",
    )
    @argument(
        "--debug",
        action="store_true",
        help="Enable debug mode for NotebookLLM instance",
    )
    @argument(
        "--snippets",
        nargs="*",
        default=[],
        help="Snippet file(s) to add; if the last value is one of 'system', 'assistant', or 'user', that role is applied to all snippets (default role: system)",
    )
    @line_magic
    def llm_setup(self, line):
        args = parse_argstring(NotebookLLMMagics.llm_setup, line)
        if args.default_model:
            self.llm.default_model_name = args.default_model.strip('"')
        if args.persona:
            self.llm.set_default_personality(args.persona)
        if args.personas_folder:
            self.llm.personalities_folder = args.personas_folder
        if args.save_dir:
            self.llm.save_dir = args.save_dir
        if args.auto_display:
            self.llm.auto_display = True
        if args.auto_save:
            self.llm.auto_save = True
        if args.autosave_file:
            self.llm.autosave_file = args.autosave_file
        if args.log_file:
            self.llm.log_file = args.log_file
        if args.api_key:
            self.llm.api_key = args.api_key
        if args.api_base:
            self.llm.api_base = args.api_base
        if args.snippet_folder:
            self.llm.snippet_folder = args.snippet_folder
        if args.include_datetime_in_autosave:
            self.llm.include_datetime_in_autosave = True
        self.llm.debug = args.debug
        if args.snippets:
            allowed_roles = {"system", "assistant", "user"}
            if args.snippets[-1].lower() in allowed_roles:
                role = args.snippets[-1].lower()
                snippet_files = args.snippets[:-1]
            else:
                role = "system"
                snippet_files = args.snippets
            for snippet in snippet_files:
                self.llm.add_snippet_message(snippet, role=role)
        print("LLM configuration updated.")
        return None

    @magic_arguments()
    @argument("--model", type=str, help="Override the model for this execution")
    @argument(
        "--persona", type=str, help="Select a default personality for this execution"
    )
    @argument(
        "--debug",
        action="store_true",
        help="Turn on debug mode for this cell execution",
    )
    @argument(
        "--nostream",
        action="store_false",
        help="Do not print output, only return value",
    )
    @cell_magic
    def llm(self, line, cell):
        args = parse_argstring(NotebookLLMMagics.llm, line)
        if args.model:
            self.llm.set_override("model", args.model.strip('"'))
        if args.persona:
            self.llm.set_default_personality(args.persona)
        # Toggle debug flag based on cell argument
        self.llm.debug = args.debug
        prompt = cell.strip()
        result = self.llm(prompt, stream=args.nostream)
        if result is not None and not args.nostream:
            display(Markdown(result))
        return None

    @magic_arguments()
    @argument(
        "--default_model", type=str, help="Set default model for NotebookLLM instance"
    )
    @argument(
        "--persona", type=str, help="Set default personality for NotebookLLM instance"
    )
    @argument("--personas_folder", type=str, help="Set the personalities folder")
    @argument("--save_dir", type=str, help="Set the save directory for conversations")
    @argument("--auto_display", action="store_true", help="Enable auto display")
    @argument("--auto_save", action="store_true", help="Enable auto save")
    @argument("--autosave_file", type=str, help="Specify autosave file name")
    @argument("--log_file", type=str, help="Specify log file for logging")
    @argument("--api_key", type=str, help="Set API key for LLM service")
    @argument("--api_base", type=str, help="Set base URL for LLM API")
    @argument("--snippet_folder", type=str, help="Set the snippet folder")
    @argument(
        "--include_datetime_in_autosave",
        action="store_true",
        help="Include datetime in autosave file name",
    )
    @argument(
        "--debug",
        action="store_true",
        help="Enable debug mode for NotebookLLM instance",
    )
    @argument(
        "--snippets",
        nargs="*",
        default=[],
        help="Snippet file(s) to add; if the last value is one of 'system', 'assistant', or 'user', that role is applied to all snippets (default role: system)",
    )
    @line_magic
    def llm_setup_forever(self, line):
        args = parse_argstring(NotebookLLMMagics.llm_setup_forever, line)
        if args.default_model:
            self.llm.default_model_name = args.default_model.strip('"')
        if args.persona:
            self.llm.set_default_personality(args.persona)
        if args.personas_folder:
            self.llm.personalities_folder = args.personas_folder
        if args.save_dir:
            self.llm.save_dir = args.save_dir
        if args.auto_display:
            self.llm.auto_display = True
        if args.auto_save:
            self.llm.auto_save = True
        if args.autosave_file:
            self.llm.autosave_file = args.autosave_file
        if args.log_file:
            self.llm.log_file = args.log_file
        if args.api_key:
            self.llm.api_key = args.api_key
        if args.api_base:
            self.llm.api_base = args.api_base
        if args.snippet_folder:
            self.llm.snippet_folder = args.snippet_folder
        if args.include_datetime_in_autosave:
            self.llm.include_datetime_in_autosave = True
        self.llm.debug = args.debug
        if args.snippets:
            allowed_roles = {"system", "assistant", "user"}
            if args.snippets[-1].lower() in allowed_roles:
                role = args.snippets[-1].lower()
                snippet_files = args.snippets[:-1]
            else:
                role = "system"
                snippet_files = args.snippets
            for snippet in snippet_files:
                self.llm.add_snippet_message(snippet, role=role)
        print("LLM configuration updated for setup_forever.")

        ip = get_ipython()
        transformer_func = _auto_magic_transformer  # Module-level func
        transformer_list = ip.input_transformers_cleanup
        if transformer_func not in transformer_list:
            transformer_list.append(transformer_func)
            # Updated message to reflect the change
            print("✅ Auto-processing Transformer ENABLED (cleanup phase).")
            print("   Run '%disable_llm_setup_forever' to disable.")
        else:
            print("ℹ️ Auto-processing Transformer already active (cleanup phase).")
        return None

    @line_magic
    def disable_llm_setup_forever(self, line):
        """Deactivates the input transformation."""
        ip = get_ipython()
        transformer_func = _auto_magic_transformer  # Module-level func

        transformer_list = ip.input_transformers_cleanup

        try:
            # Remove all instances just in case it was added multiple times
            while transformer_func in transformer_list:
                transformer_list.remove(transformer_func)
            # Updated message to reflect the change
            print("❌ Auto-processing Transformer DISABLED (cleanup phase).")
        except ValueError:
            # This part might not be strictly necessary if using while loop,
            # but keep for clarity.
            print("ℹ️ Auto-processing Transformer was not active (cleanup phase).")
        return None


def load_ipython_extension(ipython):
    ipython.register_magics(NotebookLLMMagics)
````