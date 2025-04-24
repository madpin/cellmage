from typing import List, Dict, Any
import logging

from ..interfaces import PersonaLoader, SnippetProvider
from ..models import PersonaConfig
from ..exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)

class MemoryLoader(PersonaLoader, SnippetProvider):
    """In-memory implementation for loading Personas and Snippets, useful for testing."""

    def __init__(
        self,
        personas: Dict[str, PersonaConfig] | None = None,
        snippets: Dict[str, str] | None = None
    ):
        """
        Initializes the MemoryLoader with predefined personas and snippets.

        Args:
            personas: A dictionary mapping persona names to PersonaConfig objects.
            snippets: A dictionary mapping snippet names to their string content.
        """
        self._personas = personas or {}
        self._snippets = snippets or {}
        logger.info(f"MemoryLoader initialized with {len(self._personas)} personas and {len(self._snippets)} snippets.")

    # --- PersonaLoader Implementation ---

    def load(self, name: str) -> PersonaConfig:
        """Loads a persona from the internal dictionary."""
        logger.debug(f"Attempting to load persona '{name}' from memory.")
        if name not in self._personas:
            raise ResourceNotFoundError("persona", name)
        return self._personas[name]

    def list_available(self) -> List[str]:
        """Lists available persona names from the internal dictionary."""
        return sorted(list(self._personas.keys()))

    # --- SnippetProvider Implementation ---

    def get(self, name: str) -> str:
        """Gets the content of a snippet from the internal dictionary."""
        logger.debug(f"Attempting to load snippet '{name}' from memory.")
        if name not in self._snippets:
            raise ResourceNotFoundError("snippet", name)
        return self._snippets[name]

    def list_available(self) -> List[str]:
        """Lists available snippet names from the internal dictionary."""
        return sorted(list(self._snippets.keys()))

    # --- Helper methods for testing ---
    def add_persona(self, persona: PersonaConfig):
        """Adds or updates a persona in memory."""
        self._personas[persona.name] = persona
        logger.debug(f"Added/Updated persona '{persona.name}' in memory.")

    def add_snippet(self, name: str, content: str):
        """Adds or updates a snippet in memory."""
        self._snippets[name] = content
        logger.debug(f"Added/Updated snippet '{name}' in memory.")
