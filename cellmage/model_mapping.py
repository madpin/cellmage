import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    import yaml
else:
    import yaml  # type: ignore

logger = logging.getLogger(__name__)


class ModelMapper:
    """
    Handles model name mapping between aliases and full model names.

    Supports loading mappings from YAML files and managing multiple mapping sets.
    """

    def __init__(self, mapping_file: Optional[str] = None):
        """
        Initialize the model mapper.

        Args:
            mapping_file: Path to YAML file containing model mappings
        """
        self._mappings: Dict[str, str] = {}
        if mapping_file:
            self.load_mappings(mapping_file)

    def load_mappings(self, file_path: str) -> bool:
        """
        Load model mappings from a YAML file.

        Args:
            file_path: Path to the YAML file

        Returns:
            True if mappings were loaded successfully
        """
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                logger.error(f"Invalid mapping file format in {file_path}")
                return False

            # Update mappings
            self._mappings.update(data)
            logger.info(f"Loaded {len(data)} model mappings from {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error loading model mappings from {file_path}: {e}")
            return False

    def get_full_name(self, alias: str) -> str:
        """
        Get the full model name for an alias.

        Args:
            alias: Short alias for the model

        Returns:
            Full model name or the original alias if no mapping exists
        """
        return self._mappings.get(alias, alias)

    def add_mapping(self, alias: str, full_name: str) -> None:
        """
        Add a new model mapping.

        Args:
            alias: Short alias for the model
            full_name: Full model name
        """
        self._mappings[alias] = full_name

    def remove_mapping(self, alias: str) -> bool:
        """
        Remove a model mapping.

        Args:
            alias: Alias to remove

        Returns:
            True if mapping was removed
        """
        if alias in self._mappings:
            del self._mappings[alias]
            return True
        return False

    def get_mappings(self) -> Dict[str, str]:
        """
        Get all current model mappings.

        Returns:
            Dictionary of alias to full name mappings
        """
        return self._mappings.copy()

    @staticmethod
    def find_mapping_file(notebook_dir: Optional[str] = None) -> Optional[str]:
        """
        Find the model mapping file in the notebook directory or parent directories.

        Args:
            notebook_dir: Directory containing the notebook

        Returns:
            Path to mapping file if found, None otherwise
        """
        if notebook_dir:
            current_dir = Path(notebook_dir)
        else:
            current_dir = Path.cwd()

        # Files to look for, in order of preference
        mapping_files = [
            ".cellmage_models.yml",
            "cellmage_models.yml",
            ".config/cellmage_models.yml",
            "config/cellmage_models.yml",
        ]

        # Look in current and parent directories
        while current_dir != current_dir.parent:
            for filename in mapping_files:
                mapping_file = current_dir / filename
                if mapping_file.exists():
                    return str(mapping_file)
            current_dir = current_dir.parent

        return None
