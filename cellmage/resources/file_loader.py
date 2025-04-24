import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging
import re

from ..interfaces import PersonaLoader, SnippetProvider
from ..models import PersonaConfig
from ..exceptions import ResourceNotFoundError, ConfigurationError

logger = logging.getLogger(__name__)

# Regex to find YAML frontmatter
YAML_FRONT_MATTER_REGEX = re.compile(r"^\s*---\s*\n(.*?\n?)\s*---\s*\n", re.DOTALL | re.MULTILINE)

def _parse_markdown_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extracts YAML frontmatter and main content from markdown text."""
    match = YAML_FRONT_MATTER_REGEX.match(content)
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1))
            if not isinstance(frontmatter, dict):
                frontmatter = {} # Ignore if YAML is not a dictionary
            main_content = content[match.end():].strip()
            return frontmatter, main_content
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML frontmatter: {e}. Treating as plain text.")
            # Fall through to return empty frontmatter and original content
    return {}, content.strip() # No frontmatter found or parse error

class FileLoader(PersonaLoader, SnippetProvider):
    """Loads Personas and Snippets from files in specified directories."""

    def __init__(self, personas_base_dir: Path, snippets_base_dir: Path):
        """
        Initializes the FileLoader.

        Args:
            personas_base_dir: The directory containing persona markdown files.
            snippets_base_dir: The directory containing snippet files (markdown or text).
        """
        self.personas_dir = Path(personas_base_dir)
        self.snippets_dir = Path(snippets_base_dir)

        if not self.personas_dir.is_dir():
            logger.warning(f"Personas directory not found: {self.personas_dir}. Creating it.")
            self.personas_dir.mkdir(parents=True, exist_ok=True) # Attempt to create
            # raise ConfigurationError(f"Personas directory not found: {self.personas_dir}")

        if not self.snippets_dir.is_dir():
            logger.warning(f"Snippets directory not found: {self.snippets_dir}. Creating it.")
            self.snippets_dir.mkdir(parents=True, exist_ok=True) # Attempt to create
            # raise ConfigurationError(f"Snippets directory not found: {self.snippets_dir}")

        logger.info(f"FileLoader initialized. Personas: '{self.personas_dir}', Snippets: '{self.snippets_dir}'")

    # --- PersonaLoader Implementation ---

    def load(self, name: str) -> PersonaConfig:
        """
        Loads a persona from a markdown file.
        The filename (without extension) is used as the name.
        YAML frontmatter provides llm_params, the rest is the system_prompt.
        """
        persona_path = self.personas_dir / f"{name}.md"
        logger.debug(f"Attempting to load persona '{name}' from {persona_path}")

        if not persona_path.is_file():
            raise ResourceNotFoundError("persona", name)

        try:
            content = persona_path.read_text(encoding='utf-8')
            frontmatter, system_prompt = _parse_markdown_frontmatter(content)

            # Ensure system_prompt is not None if file is empty after frontmatter
            system_prompt = system_prompt or ""

            # Basic validation (can be expanded)
            if not isinstance(frontmatter, dict):
                 logger.warning(f"Invalid frontmatter format in {persona_path}, expected dict, got {type(frontmatter)}. Ignoring params.")
                 frontmatter = {}

            persona_config = PersonaConfig(
                name=name,
                system_prompt=system_prompt,
                llm_params=frontmatter, # Pass the whole dict
                source_path=str(persona_path)
            )
            logger.info(f"Successfully loaded persona '{name}'.")
            return persona_config

        except FileNotFoundError: # Should be caught by is_file() check, but defensive
             raise ResourceNotFoundError("persona", name) from None
        except Exception as e:
            logger.exception(f"Failed to load or parse persona file: {persona_path}")
            raise ConfigurationError(f"Error loading persona '{name}': {e}") from e

    def list_available(self) -> List[str]:
        """Lists available persona names (markdown filenames without extension)."""
        if not self.personas_dir.exists():
             logger.warning(f"Cannot list personas, directory does not exist: {self.personas_dir}")
             return []
        try:
            return sorted([p.stem for p in self.personas_dir.glob("*.md") if p.is_file()])
        except Exception as e:
             logger.exception(f"Failed to list files in personas directory: {self.personas_dir}")
             return []

    # --- SnippetProvider Implementation ---

    def get(self, name: str) -> str:
        """
        Gets the content of a snippet file. Tries .md then .txt extension.
        """
        snippet_path_md = self.snippets_dir / f"{name}.md"
        snippet_path_txt = self.snippets_dir / f"{name}.txt"
        snippet_path = None

        if snippet_path_md.is_file():
             snippet_path = snippet_path_md
        elif snippet_path_txt.is_file():
             snippet_path = snippet_path_txt
        else:
             # Check for name without extension directly
             direct_path = self.snippets_dir / name
             if direct_path.is_file():
                  snippet_path = direct_path
             else:
                  raise ResourceNotFoundError("snippet", name)

        logger.debug(f"Attempting to load snippet '{name}' from {snippet_path}")
        try:
            content = snippet_path.read_text(encoding='utf-8')
            logger.info(f"Successfully loaded snippet '{name}'.")
            return content.strip() # Return stripped content
        except FileNotFoundError: # Defensive
             raise ResourceNotFoundError("snippet", name) from None
        except Exception as e:
            logger.exception(f"Failed to read snippet file: {snippet_path}")
            raise ConfigurationError(f"Error loading snippet '{name}': {e}") from e

    def list_available(self) -> List[str]:
        """Lists available snippet names (filenames without extension)."""
        if not self.snippets_dir.exists():
             logger.warning(f"Cannot list snippets, directory does not exist: {self.snippets_dir}")
             return []
        try:
            # List both .md and .txt files, removing extension
            md_files = {p.stem for p in self.snippets_dir.glob("*.md") if p.is_file()}
            txt_files = {p.stem for p in self.snippets_dir.glob("*.txt") if p.is_file()}
            # Consider listing files without extensions too? For now, stick to .md/.txt
            # other_files = {p.name for p in self.snippets_dir.glob("*") if p.is_file() and not p.suffix in ['.md', '.txt']}
            return sorted(list(md_files.union(txt_files))) # .union(other_files)
        except Exception as e:
             logger.exception(f"Failed to list files in snippets directory: {self.snippets_dir}")
             return []

