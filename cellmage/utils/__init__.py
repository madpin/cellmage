"""
Utility functions and helpers.

This module contains utility functions used throughout the cellmage library.
"""

from .date_utils import parse_date_input
from .file_utils import (
    display_directory,
    display_files_as_table,
    display_files_paginated,
    list_directory_files,
)
from .logging import setup_logging

# Import JiraUtils conditionally since it requires optional dependencies
try:
    from .jira_utils import JiraUtils

    _JIRA_AVAILABLE = True
except ImportError:
    # Define a placeholder for better error messages when the dependency is missing
    class JiraUtils:
        """Placeholder for JiraUtils class when jira package is not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "The 'jira' package is required to use JiraUtils. "
                "Install it with 'pip install cellmage[jira]'"
            )

    _JIRA_AVAILABLE = False

# Import GoogleDocsUtils conditionally since it requires optional dependencies
try:
    from .gdocs_utils import GoogleDocsUtils

    _GDOCS_AVAILABLE = True
except ImportError:
    # Define a placeholder for better error messages when the dependency is missing
    class GoogleDocsUtils:
        """Placeholder for GoogleDocsUtils class when Google API packages are not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "The Google API packages are required to use GoogleDocsUtils. "
                "Install them with 'pip install cellmage[gdocs]'"
            )

    _GDOCS_AVAILABLE = False

# Import ImageProcessor conditionally since it requires optional dependencies
try:
    from .image_utils import (
        ImageProcessor,
        format_image_for_llm,
        format_image_info_for_display,
        format_processed_image_info,
        get_image_processor,
        is_image_processing_available,
    )

    _IMAGE_PROCESSING_AVAILABLE = is_image_processing_available()
except ImportError:
    # Define a placeholder for better error messages when the dependency is missing
    class ImageProcessor:
        """Placeholder for ImageProcessor class when PIL is not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "The 'PIL' package is required to use ImageProcessor. "
                "Install it with 'pip install pillow'"
            )

    _IMAGE_PROCESSING_AVAILABLE = False

    def format_image_info_for_display(*args, **kwargs):
        raise ImportError("PIL is required for image processing")

    def format_processed_image_info(*args, **kwargs):
        raise ImportError("PIL is required for image processing")

    def format_image_for_llm(*args, **kwargs):
        raise ImportError("PIL is required for image processing")

    def is_image_processing_available():
        return False

    def get_image_processor():
        return None


__all__ = [
    "setup_logging",
    "display_files_as_table",
    "display_files_paginated",
    "list_directory_files",
    "display_directory",
    "JiraUtils",
    "GoogleDocsUtils",
    "parse_date_input",
]
