"""
Integration utilities with external services and APIs.

This module contains utilities for integrating with external services like Jira, Confluence,
GitHub, GitLab, Google Docs, and image processing tools.
"""

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


# Import GitHub, GitLab and Confluence utils
try:
    from .github_utils import GitHubUtils

    _GITHUB_AVAILABLE = True
except ImportError:

    class GitHubUtils:
        """Placeholder for GitHubUtils when GitHub dependencies are not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "GitHub dependencies are required to use GitHubUtils. "
                "Install them with 'pip install cellmage[github]'"
            )

    _GITHUB_AVAILABLE = False

try:
    from .gitlab_utils import GitLabUtils

    _GITLAB_AVAILABLE = True
except ImportError:

    class GitLabUtils:
        """Placeholder for GitLabUtils when GitLab dependencies are not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "GitLab dependencies are required to use GitLabUtils. "
                "Install them with 'pip install cellmage[gitlab]'"
            )

    _GITLAB_AVAILABLE = False

try:
    from .confluence_utils import ConfluenceUtils

    _CONFLUENCE_AVAILABLE = True
except ImportError:

    class ConfluenceUtils:
        """Placeholder for ConfluenceUtils when Confluence dependencies are not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "Confluence dependencies are required to use ConfluenceUtils. "
                "Install them with 'pip install cellmage[confluence]'"
            )

    _CONFLUENCE_AVAILABLE = False

try:
    from .webcontent_utils import WebContentUtils

    _WEBCONTENT_AVAILABLE = True
except ImportError:

    class WebContentUtils:
        """Placeholder for WebContentUtils when web scraping dependencies are not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "Web scraping dependencies are required to use WebContentUtils. "
                "Install them with 'pip install cellmage[web]'"
            )

    _WEBCONTENT_AVAILABLE = False

__all__ = [
    "JiraUtils",
    "GoogleDocsUtils",
    "GitHubUtils",
    "GitLabUtils",
    "ConfluenceUtils",
    "WebContentUtils",
    "ImageProcessor",
    "format_image_for_llm",
    "format_image_info_for_display",
    "format_processed_image_info",
    "get_image_processor",
    "is_image_processing_available",
]
