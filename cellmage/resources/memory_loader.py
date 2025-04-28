import logging
from typing import Any, Dict, List, Optional

from ..interfaces import PersonaLoader, SnippetProvider
from ..models import PersonaConfig


class MemoryLoader(PersonaLoader, SnippetProvider):
    """
    In-memory implementation of persona and snippet loading.

    This class stores and provides personas and snippets from memory,
    allowing for programmatic creation and modification at runtime.
    """

    def __init__(self):
        """Initialize the memory loader with empty collections."""
        self.logger = logging.getLogger(__name__)
        self.personas: Dict[str, PersonaConfig] = {}
        self.snippets: Dict[str, str] = {}
        self.logger.debug("MemoryLoader initialized with empty collections")

    # --- PersonaLoader implementation ---
    def list_personas(self) -> List[str]:
        """
        List available personas.

        Returns:
            List of persona names
        """
        return sorted(list(self.personas.keys()))

    def get_persona(self, name: str) -> Optional[PersonaConfig]:
        """
        Get a persona by name.

        Args:
            name: Name of the persona to retrieve

        Returns:
            Persona configuration or None if not found
        """
        # Case insensitive search
        name_lower = name.lower()
        for persona_name, persona in self.personas.items():
            if persona_name.lower() == name_lower:
                return persona

        self.logger.warning(f"Persona '{name}' not found")
        return None

    def add_persona(
        self, name: str, system_message: str, config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a persona to the in-memory collection.

        Args:
            name: Name of the persona
            system_message: System message for the persona
            config: Optional configuration for the persona
        """
        # Fix: use 'name' parameter instead of 'original_name' which doesn't exist
        self.personas[name] = PersonaConfig(
            name=name,  # Correctly passing the name parameter
            system_message=system_message,
            config=config or {},
        )
        self.logger.info(f"Added persona '{name}' to memory")

    def remove_persona(self, name: str) -> bool:
        """
        Remove a persona from the in-memory collection.

        Args:
            name: Name of the persona to remove

        Returns:
            True if the persona was removed, False if not found
        """
        name_lower = name.lower()
        for persona_name in list(self.personas.keys()):
            if persona_name.lower() == name_lower:
                del self.personas[persona_name]
                self.logger.info(f"Removed persona '{persona_name}' from memory")
                return True

        self.logger.warning(f"Cannot remove: Persona '{name}' not found")
        return False

    # --- SnippetProvider implementation ---
    def list_snippets(self) -> List[str]:
        """
        List available snippets.

        Returns:
            List of snippet names
        """
        return sorted(list(self.snippets.keys()))

    def get_snippet(self, name: str) -> Optional[str]:
        """
        Get a snippet by name.

        Args:
            name: Name of the snippet to retrieve

        Returns:
            Snippet content or None if not found
        """
        # Case insensitive search
        name_lower = name.lower()
        for snippet_name, content in self.snippets.items():
            if snippet_name.lower() == name_lower:
                return content

        self.logger.warning(f"Snippet '{name}' not found")
        return None

    def add_snippet(self, name: str, content: str) -> None:
        """
        Add a snippet to the in-memory collection.

        Args:
            name: Name of the snippet
            content: Content of the snippet
        """
        self.snippets[name] = content
        self.logger.info(f"Added snippet '{name}' to memory")

    def remove_snippet(self, name: str) -> bool:
        """
        Remove a snippet from the in-memory collection.

        Args:
            name: Name of the snippet to remove

        Returns:
            True if the snippet was removed, False if not found
        """
        name_lower = name.lower()
        for snippet_name in list(self.snippets.keys()):
            if snippet_name.lower() == name_lower:
                del self.snippets[snippet_name]
                self.logger.info(f"Removed snippet '{snippet_name}' from memory")
                return True

        self.logger.warning(f"Cannot remove: Snippet '{name}' not found")
        return False
