import logging
import os
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    import yaml
else:
    import yaml  # type: ignore

from ..interfaces import PersonaLoader, SnippetProvider
from ..models import PersonaConfig


class FileLoader(PersonaLoader, SnippetProvider):
    """
    Loads personas and snippets from markdown files.

    Implements both PersonaLoader and SnippetProvider interfaces.
    """

    def __init__(self, personas_dir: str = "llm_personas", snippets_dir: str = "llm_snippets"):
        """
        Initialize the FileLoader.

        Args:
            personas_dir: Directory containing persona markdown files
            snippets_dir: Directory containing snippet markdown files
        """
        self.personas_dir = personas_dir or "llm_personas"  # Ensure non-empty value
        self.snippets_dir = snippets_dir or "llm_snippets"  # Ensure non-empty value
        self.logger = logging.getLogger(__name__)

        # Ensure directories exist
        for directory in [self.personas_dir, self.snippets_dir]:
            if not directory.strip():  # Skip empty strings
                self.logger.warning("Skipping empty directory path")
                continue

            try:
                os.makedirs(directory, exist_ok=True)
                self.logger.info(f"Directory setup: {os.path.abspath(directory)}")
            except OSError as e:
                self.logger.error(f"Error creating directory '{directory}': {e}")

    def list_personas(self) -> List[str]:
        """
        List available personas.

        Returns:
            List of persona names (without .md extension)
        """
        try:
            if not os.path.isdir(self.personas_dir):
                self.logger.warning(
                    f"Personas directory not found: {os.path.abspath(self.personas_dir)}"
                )
                return []

            personas = []
            for filename in os.listdir(self.personas_dir):
                if filename.lower().endswith(".md"):
                    name = os.path.splitext(filename)[0]
                    personas.append(name)
            return sorted(personas)
        except Exception as e:
            self.logger.error(f"Error listing personas: {e}")
            return []

    def get_persona(self, name: str) -> Optional[PersonaConfig]:
        """
        Load a persona configuration from a markdown file.

        Args:
            name: Name of the persona (without .md extension) or path to a .md file
                 If name starts with '/' or '.', it will be treated as file path

        Returns:
            PersonaConfig object or None if not found
        """
        # Check if name represents a file path (starts with '/' or '.')
        if name.startswith("/") or name.startswith("."):
            # Direct file path case - ensure it has .md extension
            if not name.lower().endswith(".md"):
                filepath = f"{name}.md"
            else:
                filepath = name

            # Extract the base name for use as original_name
            original_name = os.path.splitext(os.path.basename(filepath))[0]

            # Try to load directly from the given path
            if os.path.isfile(filepath):
                self.logger.debug(f"Loading persona from direct path: {filepath}")
                return self._load_persona_file(filepath, original_name)

            self.logger.warning(f"Persona file not found at path: {filepath}")
            return None

        # Standard case - search in configured directory
        # Case insensitive matching
        name_lower = name.lower()

        # First try exact filename match
        filepath = os.path.join(self.personas_dir, f"{name}.md")
        if os.path.isfile(filepath):
            return self._load_persona_file(filepath, name)

        # Otherwise try case-insensitive match
        try:
            if not os.path.isdir(self.personas_dir):
                self.logger.warning(
                    f"Personas directory not found: {os.path.abspath(self.personas_dir)}"
                )
                return None

            for filename in os.listdir(self.personas_dir):
                if filename.lower().endswith(".md"):
                    file_name_base = os.path.splitext(filename)[0]
                    if file_name_base.lower() == name_lower:
                        filepath = os.path.join(self.personas_dir, filename)
                        return self._load_persona_file(filepath, file_name_base)

            self.logger.warning(f"Persona '{name}' not found in {self.personas_dir}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting persona '{name}': {e}")
            return None

    def _load_persona_file(self, filepath: str, original_name: str) -> Optional[PersonaConfig]:
        """
        Parse a markdown file into a PersonaConfig object.

        Args:
            filepath: Path to the markdown file
            original_name: Original name of the persona

        Returns:
            PersonaConfig object or None if parsing fails
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Manual YAML frontmatter parsing
            config: dict[str, Any] = {}
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
                        self.logger.error(f"Error parsing YAML frontmatter: {yaml_err}")
                        system_message = content.strip()
                else:
                    # No closing --- found, treat whole content as system message
                    system_message = content.strip()
            else:
                # No frontmatter, treat whole content as system message
                system_message = content.strip()

            abs_filepath = os.path.abspath(filepath)
            self.logger.debug(f"Loaded persona '{original_name}' from {abs_filepath}")

            # Make sure 'name' is in the config
            if "name" not in config:
                # Set the name to the original filename (without extension)
                config["name"] = original_name
                self.logger.info(
                    f"Persona name not found in frontmatter. Using filename '{original_name}' as persona name."
                )

            # Make sure 'model' is in the config - this is crucial for external personas
            if "model" not in config:
                # Import settings to get the default model
                from ..config import settings

                config["model"] = settings.default_model
                self.logger.info(
                    f"Model not specified in persona '{original_name}'. Using default model: {settings.default_model}"
                )

            try:
                # Create PersonaConfig using only the fields in the model definition
                return PersonaConfig(
                    name=config["name"],  # Required field
                    system_message=system_message,  # Required field
                    config=config,  # Optional config dictionary
                    source_path=abs_filepath,  # Optional source path (renamed from source_file)
                )
            except Exception as validation_err:
                # Provide a helpful error message with a template and debugging info
                self.logger.error(f"Error creating PersonaConfig: {validation_err}")
                self.logger.debug(f"Config data: {config}")
                self.logger.debug(f"System message: {system_message[:100]}...")

                template = f"""---
name: {original_name}
description: A brief description of this persona
model: gpt-4.1-nano
# Optional parameters:
# temperature: 0.7
---
{system_message}"""
                print(f"\n❌ Error loading persona '{original_name}': {validation_err}")
                print(
                    f"Your persona file might have incorrect frontmatter. Please check '{os.path.basename(filepath)}' and ensure it has the following format:"
                )
                print("\n" + "-" * 60)
                print(template[: template.find("---", 3) + 3])
                print("-" * 60 + "\n")
                return None
        except Exception as e:
            self.logger.error(f"Error loading persona file '{filepath}': {e}")
            print(f"\n❌ Error reading persona file '{original_name}': {e}")
            return None

    def list_snippets(self) -> List[str]:
        """
        List available snippets.

        Returns:
            List of snippet names (without .md extension)
        """
        try:
            if not os.path.isdir(self.snippets_dir):
                self.logger.warning(
                    f"Snippets directory not found: {os.path.abspath(self.snippets_dir)}"
                )
                return []

            snippets = []
            for filename in os.listdir(self.snippets_dir):
                if filename.lower().endswith(".md"):
                    name = os.path.splitext(filename)[0]
                    snippets.append(name)
            return sorted(snippets)
        except Exception as e:
            self.logger.error(f"Error listing snippets: {e}")
            return []

    def get_snippet(self, name: str) -> Optional[str]:
        """
        Load a snippet from a markdown file.

        Args:
            name: Name of the snippet (without .md extension) or path to a file
                 If name starts with '/' or '.', it will be treated as file path

        Returns:
            Snippet content as string or None if not found
        """
        # Check if name represents a file path (starts with '/' or '.')
        if name.startswith("/") or name.startswith("."):
            # Direct file path case
            filepath = name

            # Try to load directly from the given path
            try:
                if not os.path.isfile(filepath):
                    self.logger.warning(f"Snippet file not found at path: {filepath}")
                    return None

                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                self.logger.debug(f"Loaded snippet from direct path: {filepath}")
                return content
            except Exception as e:
                self.logger.error(f"Error loading snippet from path '{filepath}': {e}")
                return None

        # Standard case - search in configured directory
        # Add .md extension if not provided and we're using the default directory lookup
        if not name.lower().endswith(".md"):
            name += ".md"

        filepath = os.path.join(self.snippets_dir, name)

        try:
            if not os.path.isfile(filepath):
                self.logger.warning(f"Snippet '{name}' not found at {filepath}")
                return None

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            self.logger.debug(f"Loaded snippet '{name}' from {filepath}")
            return content
        except Exception as e:
            self.logger.error(f"Error loading snippet '{name}': {e}")
            return None


class MultiFileLoader(PersonaLoader, SnippetProvider):
    """
    Loads personas and snippets from multiple directories.

    This class allows searching for resources across multiple directories,
    returning the first match found.
    """

    def __init__(
        self, personas_dirs: Optional[List[str]] = None, snippets_dirs: Optional[List[str]] = None
    ):
        """
        Initialize the MultiFileLoader.

        Args:
            personas_dirs: List of directories containing persona markdown files
            snippets_dirs: List of directories containing snippet markdown files
        """
        # Filter out empty directory paths
        self.personas_dirs = [d for d in (personas_dirs or ["llm_personas"]) if d and d.strip()]
        if not self.personas_dirs:
            self.personas_dirs = ["llm_personas"]  # Fallback to default if all were empty

        self.snippets_dirs = [d for d in (snippets_dirs or ["llm_snippets"]) if d and d.strip()]
        if not self.snippets_dirs:
            self.snippets_dirs = ["llm_snippets"]  # Fallback to default if all were empty

        self.logger = logging.getLogger(__name__)

        # Create individual loaders for each directory
        self.persona_loaders = [
            FileLoader(personas_dir=d, snippets_dir="") for d in self.personas_dirs
        ]
        self.snippet_loaders = [
            FileLoader(personas_dir="", snippets_dir=d) for d in self.snippets_dirs
        ]

        # Log configuration
        self.logger.info(
            f"MultiFileLoader initialized with persona directories: {self.personas_dirs}"
        )
        self.logger.info(
            f"MultiFileLoader initialized with snippet directories: {self.snippets_dirs}"
        )

    def list_personas(self) -> List[str]:
        """
        List available personas from all directories.

        Returns:
            Combined list of persona names (without .md extension)
        """
        all_personas = set()
        for loader in self.persona_loaders:
            all_personas.update(loader.list_personas())
        return sorted(list(all_personas))

    def get_persona(self, name: str) -> Optional[PersonaConfig]:
        """
        Load a persona configuration, searching across all directories.

        Args:
            name: Name of the persona (without .md extension) or path to a .md file
                 If name starts with '/' or '.', it will be treated as file path

        Returns:
            First matching PersonaConfig object or None if not found
        """
        # Check if name represents a file path (starts with '/' or '.')
        if name.startswith("/") or name.startswith("."):
            # For direct file paths, use the first loader to handle it
            # (any loader can handle direct paths)
            if self.persona_loaders:
                return self.persona_loaders[0].get_persona(name)
            else:
                self.logger.warning("No persona loaders available to handle direct file path")
                return None

        # Standard case - search through configured directories
        for loader in self.persona_loaders:
            persona = loader.get_persona(name)
            if persona:
                self.logger.debug(f"Found persona '{name}' in {loader.personas_dir}")
                return persona

        self.logger.warning(f"Persona '{name}' not found in any directory: {self.personas_dirs}")
        return None

    def list_snippets(self) -> List[str]:
        """
        List available snippets from all directories.

        Returns:
            Combined list of snippet names (without .md extension)
        """
        all_snippets = set()
        for loader in self.snippet_loaders:
            all_snippets.update(loader.list_snippets())
        return sorted(list(all_snippets))

    def get_snippet(self, name: str) -> Optional[str]:
        """
        Load a snippet, searching across all directories.

        Args:
            name: Name of the snippet (without .md extension) or path to a file
                 If name starts with '/' or '.', it will be treated as file path

        Returns:
            Snippet content as string or None if not found
        """
        # Check if name represents a file path (starts with '/' or '.')
        if name.startswith("/") or name.startswith("."):
            # For direct file paths, use the first loader to handle it
            # (any loader can handle direct paths)
            if self.snippet_loaders:
                return self.snippet_loaders[0].get_snippet(name)
            else:
                self.logger.warning("No snippet loaders available to handle direct file path")
                return None

        # Standard case - search through configured directories
        for loader in self.snippet_loaders:
            snippet = loader.get_snippet(name)
            if snippet:
                self.logger.debug(f"Found snippet '{name}' in {loader.snippets_dir}")
                return snippet

        self.logger.warning(f"Snippet '{name}' not found in any directory: {self.snippets_dirs}")
        return None
