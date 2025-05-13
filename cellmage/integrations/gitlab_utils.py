"""
GitLab utility for interacting with the GitLab API.

This module provides the GitLabUtils class for fetching repositories, code, and merge requests.
"""

import logging
import os
import shutil
import tempfile
import zipfile
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

# Import token utilities
from cellmage.utils.token_utils import default_token_counter

# Flag to check if python-gitlab is available
_GITLAB_AVAILABLE = False

try:
    from gitlab import Gitlab
    from gitlab.exceptions import (
        GitlabAuthenticationError,
        GitlabGetError,
        GitlabHttpError,
    )
    from gitlab.v4.objects import MergeRequest, Project

    _GITLAB_AVAILABLE = True
except ImportError:
    # Define placeholder types for type checking when gitlab package is not available
    Gitlab = object
    Project = object
    MergeRequest = object
    GitlabAuthenticationError = Exception
    GitlabGetError = Exception
    GitlabHttpError = Exception

# --- Constants ---
DEFAULT_GITLAB_URL = "https://gitlab.com"
DEFAULT_MAX_FILES = 200
DEFAULT_MAX_MR_CHANGES = 100
DEFAULT_MAX_FILE_SIZE = 1024 * 1024  # 1MB limit for individual files
DEFAULT_ENCODING_MODEL = "cl100k_base"  # Default encoding for GPT-4 and recent models
CODE_EXTENSIONS = (
    ".py",
    ".js",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".rb",
    ".go",
    ".php",
    ".cs",
    ".html",
    ".css",
    ".sh",
    ".ts",
    ".jsx",
    ".tsx",
    ".md",
    ".yml",
    ".yaml",
    ".json",
    ".sql",
)

# --- Setup Logging ---
logger = logging.getLogger(__name__)


# Helper function to make arguments hashable for LRU cache
def _make_hashable(arg: Any) -> Any:
    """Make an argument hashable for LRU cache."""
    if isinstance(arg, list):
        try:
            return tuple(sorted(arg))
        except TypeError:
            return tuple(arg)
    if isinstance(arg, set):
        return tuple(sorted(list(arg)))
    if isinstance(arg, dict):
        return tuple(sorted(arg.items()))
    return arg


# Custom cache decorator to handle unhashable arguments
def hashable_lru_cache(maxsize=128, typed=False):
    """LRU cache decorator that can handle unhashable arguments."""

    def decorator(func):
        cached_func = lru_cache(maxsize=maxsize, typed=typed)(func)

        def wrapper(*args, **kwargs):
            hashable_args = tuple(_make_hashable(arg) for arg in args)
            hashable_kwargs = {k: _make_hashable(v) for k, v in kwargs.items()}
            return cached_func(*hashable_args, **hashable_kwargs)

        wrapper.cache_info = cached_func.cache_info
        wrapper.cache_clear = cached_func.cache_clear
        return wrapper

    return decorator


class GitLabUtils:
    """
    Utility class for interacting with the GitLab API.

    Fetches and processes GitLab repositories, merge requests, and code content,
    preparing data for analysis or LLM input.
    """

    _client: Optional[Any] = None

    def __init__(
        self,
        private_token: Optional[str] = None,
        gitlab_url: Optional[str] = None,
        max_files: int = DEFAULT_MAX_FILES,
        max_mr_changes: int = DEFAULT_MAX_MR_CHANGES,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
    ):
        """Initialize GitLabUtils.

        Args:
            private_token: GitLab Personal Access Token.
                Falls back to GITLAB_PAT or GITLAB_PRIVATE_TOKEN env var.
            gitlab_url: URL of the GitLab instance. Falls back to GITLAB_URL env var
                or DEFAULT_GITLAB_URL.
            max_files: Maximum number of files to process.
            max_mr_changes: Maximum number of changes to include from a merge request.
            max_file_size: Maximum file size in bytes to process.

        Raises:
            ValueError: If required authentication details are missing.
        """
        if not _GITLAB_AVAILABLE:
            raise ImportError(
                "The 'python-gitlab' package is required but not installed. "
                "Please install it with 'pip install python-gitlab'."
            )

        # Try to load from .env using dotenv if available
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass  # Continue without dotenv

        self.private_token = (
            private_token or os.getenv("GITLAB_PAT") or os.getenv("GITLAB_PRIVATE_TOKEN")
        )
        self.gitlab_url = gitlab_url or os.getenv("GITLAB_URL") or DEFAULT_GITLAB_URL
        self.max_files = max_files
        self.max_mr_changes = max_mr_changes
        self.max_file_size = max_file_size
        self.temp_dir = None

        # Validate essential configuration
        if not self.private_token:
            raise ValueError(
                "GitLab private token is required (provide via arg or GITLAB_PAT env var)."
            )

        logger.info(f"GitLabUtils initialized for URL: {self.gitlab_url}")
        # Client is initialized lazily via the 'client' property

    @property
    def client(self) -> Gitlab:
        """Lazy-initialized, authenticated gitlab.Gitlab client."""
        if self._client is None:
            logger.info(f"Connecting to GitLab at {self.gitlab_url}...")
            try:
                self._client = Gitlab(self.gitlab_url, private_token=self.private_token)
                self._client.auth()  # Test authentication
                logger.info("Successfully connected to GitLab.")
            except GitlabAuthenticationError as e:
                logger.error(f"GitLab authentication failed: {str(e)}", exc_info=True)
                raise RuntimeError(f"Failed to authenticate with GitLab: {str(e)}") from e
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred during GitLab connection: {e}", exc_info=True
                )
                raise RuntimeError(f"Unexpected error connecting to GitLab: {str(e)}") from e
        return self._client

    @hashable_lru_cache(maxsize=256)
    def get_project(self, project_identifier: str) -> Project:
        """Get a GitLab project by ID or path.

        Args:
            project_identifier: The project ID (numeric) or path (namespace/project-name)

        Returns:
            A GitLab Project object

        Raises:
            RuntimeError: If the project cannot be found or accessed
        """
        logger.info(f"Fetching GitLab project: {project_identifier}")
        try:
            project = self.client.projects.get(project_identifier)
            logger.info(
                f"Successfully fetched project: {project.name_with_namespace} (ID: {project.id})"
            )
            return project
        except GitlabGetError as e:
            logger.error(f"Failed to get project '{project_identifier}': {str(e)}")
            raise RuntimeError(
                f"Project '{project_identifier}' not found or insufficient permissions."
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error getting GitLab project: {e}", exc_info=True)
            raise RuntimeError(f"Unexpected error fetching GitLab project: {str(e)}") from e

    def download_repository(self, project: Project) -> str:
        """Download and extract repository files to a temporary directory.

        Args:
            project: A GitLab Project object

        Returns:
            Path to the directory containing extracted repository content

        Raises:
            RuntimeError: If the repository download or extraction fails
        """
        logger.info(f"Downloading repository archive for project '{project.name}'...")

        # Create a temporary directory for this project
        self.temp_dir = tempfile.mkdtemp(prefix=f"gitlab_repo_{project.path}_")

        try:
            # Get the archive as bytes (zip format)
            archive_data = project.repository_archive(format="zip", streamed=False)

            if not archive_data:
                raise ValueError("Downloaded archive data is empty.")

            # Write bytes to a temporary zip file
            zip_path = os.path.join(self.temp_dir, f"{project.name}-archive.zip")
            logger.debug(f"Saving archive to {zip_path}...")
            with open(zip_path, "wb") as f:
                f.write(archive_data)

            logger.debug(f"Extracting archive to {self.temp_dir}...")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # Extract all contents
                zip_ref.extractall(self.temp_dir)

            os.remove(zip_path)  # Clean up the zip file
            logger.info("Repository extraction complete.")

            # Find the actual code directory (often inside a folder named like project-name-branchname-commitsha)
            extracted_items = os.listdir(self.temp_dir)
            if len(extracted_items) == 1 and os.path.isdir(
                os.path.join(self.temp_dir, extracted_items[0])
            ):
                code_root = os.path.join(self.temp_dir, extracted_items[0])
                logger.debug(f"Code appears to be in subdirectory: {code_root}")
                return code_root
            else:
                # If multiple items or just files, assume code is at the root of temp_dir
                logger.debug(
                    f"Code assumed to be at the root of the extraction directory: {self.temp_dir}"
                )
                return self.temp_dir

        except GitlabHttpError as e:
            logger.error(
                f"GitLab API Error downloading archive: {e.response_code} - {e.error_message}"
            )
            self.cleanup_temp_dir()
            raise RuntimeError(f"Failed to download repository archive: {e.error_message}") from e
        except zipfile.BadZipFile:
            logger.error("Downloaded file is not a valid ZIP archive.")
            self.cleanup_temp_dir()
            raise RuntimeError("Downloaded file is not a valid ZIP archive.") from None
        except Exception as e:
            logger.error(f"An error occurred during download/extraction: {e}", exc_info=True)
            self.cleanup_temp_dir()
            raise RuntimeError(f"Failed to download or extract repository: {str(e)}") from e

    def get_merge_request(self, project: Project, mr_id: Union[int, str]) -> Dict[str, Any]:
        """Fetch a single merge request and its changes.

        Args:
            project: A GitLab Project object
            mr_id: The ID of the merge request

        Returns:
            Dictionary with merge request details and changes

        Raises:
            RuntimeError: If the merge request cannot be found or accessed
        """
        logger.info(f"Fetching merge request {mr_id} for project ID {project.id}")

        try:
            # Convert string ID to int if necessary
            mr_id_int = int(mr_id)
            mr = project.mergerequests.get(mr_id_int)

            # Get basic MR information
            mr_info = {
                "id": mr.iid,
                "title": mr.title,
                "description": mr.description,
                "state": mr.state,
                "created_at": mr.created_at,
                "updated_at": mr.updated_at,
                "source_branch": mr.source_branch,
                "target_branch": mr.target_branch,
                "author": {"name": mr.author["name"], "username": mr.author["username"]},
                "web_url": mr.web_url,
                "changes": [],
            }

            # Try to get assignee information if available
            if hasattr(mr, "assignee") and mr.assignee:
                mr_info["assignee"] = {
                    "name": mr.assignee["name"],
                    "username": mr.assignee["username"],
                }

            # Get changes (diffs)
            if hasattr(mr, "changes") and callable(mr.changes):
                try:
                    changes = mr.changes()
                    mr_info["changes_count"] = len(changes.get("changes", []))

                    # Process the changes
                    for i, change in enumerate(changes.get("changes", [])):
                        if i >= self.max_mr_changes:
                            break

                        change_info = {
                            "old_path": change.get("old_path"),
                            "new_path": change.get("new_path"),
                            "diff": change.get("diff"),
                        }
                        mr_info["changes"].append(change_info)

                except Exception as e:
                    logger.error(f"Error fetching MR changes: {e}")
                    mr_info["changes_error"] = str(e)

            return mr_info

        except GitlabGetError as e:
            logger.error(f"Failed to get merge request {mr_id}: {str(e)}")
            raise RuntimeError(f"Merge request {mr_id} not found or inaccessible.") from e
        except Exception as e:
            logger.error(f"Unexpected error getting merge request {mr_id}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to fetch merge request details: {str(e)}") from e

    def get_repository_summary(
        self,
        project_identifier: str,
        full_code: bool = False,
        contributors_months: int = 6,
        exclusion_patterns: Dict[str, List[str]] = None,
    ) -> Dict[str, Any]:
        """Get a complete summary of a repository.

        This is the main method to fetch all relevant information about a GitLab repository.

        Args:
            project_identifier: The project ID (numeric) or path (namespace/project-name)
            full_code: Whether to include full code content from the repository
            contributors_months: How many months of contributor history to include
            exclusion_patterns: Dictionary with exclusion patterns for directories, files, extensions, and regex patterns

        Returns:
            Dictionary with complete repository information

        Raises:
            RuntimeError: If any part of the process fails
        """
        logger.info(f"Generating complete repository summary for: {project_identifier}")

        try:
            # Initialize the result dictionary
            result = {
                "project_info": {},
                "repository_contents": {},
                "last_commit": None,
                "contributors": [],
                "estimated_tokens": 0,
            }

            # 1. Get the project
            project = self.get_project(project_identifier)

            # 2. Store project information
            result["project_info"] = {
                "id": project.id,
                "name": project.name,
                "path": project.path,
                "name_with_namespace": project.name_with_namespace,
                "description": project.description,
                "default_branch": project.default_branch,
                "web_url": project.web_url,
                "visibility": project.visibility,
                "star_count": project.star_count if hasattr(project, "star_count") else None,
                "fork_count": project.forks_count if hasattr(project, "forks_count") else None,
                "created_at": project.created_at if hasattr(project, "created_at") else None,
                "last_activity_at": (
                    project.last_activity_at if hasattr(project, "last_activity_at") else None
                ),
            }

            # 3. Get the latest commit information
            try:
                commits = project.commits.list(all=False, per_page=1)
                if commits:
                    result["last_commit"] = {
                        "id": commits[0].id,
                        "short_id": commits[0].short_id,
                        "title": commits[0].title,
                        "author_name": commits[0].author_name,
                        "authored_date": commits[0].authored_date,
                        "committer_name": commits[0].committer_name,
                        "committed_date": commits[0].committed_date,
                        "message": commits[0].message,
                    }
            except Exception as e:
                logger.warning(f"Could not fetch latest commit: {e}")

            # 4. Get contributors with commit activity
            try:
                # Calculate date from N months ago
                import datetime

                today = datetime.datetime.now()
                months_ago = today - datetime.timedelta(days=30 * contributors_months)
                months_ago_str = months_ago.strftime("%Y-%m-%d")

                # Get commits since that date to find active contributors
                all_commits = project.commits.list(all=True, since=months_ago_str, per_page=100)

                # Process the contributors from commits
                contributors_dict = {}
                for commit in all_commits:
                    name = commit.author_name
                    email = commit.author_email

                    if name not in contributors_dict:
                        contributors_dict[name] = {
                            "name": name,
                            "email": email,
                            "commits": 0,
                            "last_commit_date": commit.committed_date,
                        }

                    contributors_dict[name]["commits"] += 1

                    # Update last commit date if this one is more recent
                    if (
                        contributors_dict[name]["last_commit_date"] is None
                        or commit.committed_date > contributors_dict[name]["last_commit_date"]
                    ):
                        contributors_dict[name]["last_commit_date"] = commit.committed_date

                # Convert to list and sort by commit count
                result["contributors"] = sorted(
                    list(contributors_dict.values()), key=lambda x: x["commits"], reverse=True
                )

                # Add contributor metadata
                result["contributors_metadata"] = {
                    "period_months": contributors_months,
                    "since_date": months_ago_str,
                    "total_contributors": len(result["contributors"]),
                    "total_commits": sum(c["commits"] for c in result["contributors"]),
                }

            except Exception as e:
                logger.warning(f"Could not fetch contributors: {e}")
                result["contributors"] = []

            # 5. Download and process the repository content
            repo_path = self.download_repository(project)
            result["repository_contents"] = self.process_repository_contents(
                repo_path, include_full_code=full_code, exclusion_patterns=exclusion_patterns
            )

            # 6. Estimate token size
            code_tokens_estimate = self._estimate_tokens_from_repo_contents(
                result["repository_contents"]
            )
            metadata_tokens_estimate = (
                self._estimate_tokens_from_dict(result["project_info"])
                + self._estimate_tokens_from_dict(result.get("last_commit", {}))
                + self._estimate_tokens_from_list(result["contributors"], max_items=10)
            )

            result["estimated_tokens"] = {
                "code": code_tokens_estimate,
                "metadata": metadata_tokens_estimate,
                "total": code_tokens_estimate + metadata_tokens_estimate,
            }

            logger.info(f"Successfully generated repository summary for {project_identifier}")
            return result

        except Exception as e:
            logger.error(f"Failed to generate repository summary: {e}", exc_info=True)
            raise
        finally:
            # Clean up temporary files
            self.cleanup_temp_dir()

    def _estimate_tokens_from_dict(self, data: Dict[str, Any]) -> int:
        """Estimate the number of tokens in a dictionary."""
        return default_token_counter.count_tokens_in_dict(data)

    def _estimate_tokens_from_list(self, data: List[Any], max_items: Optional[int] = None) -> int:
        """Estimate the number of tokens in a list."""
        if not data:
            return 0

        items_to_count = data[:max_items] if max_items else data
        return default_token_counter.count_tokens_in_list(items_to_count)

    def _estimate_tokens_from_repo_contents(self, repo_contents: Dict[str, Any]) -> int:
        """Estimate the number of tokens from repository contents using tiktoken or fallback method."""
        token_count = 0

        # Count files metadata using the regular dictionary counting
        metadata_token_count = default_token_counter.count_tokens_in_dict(
            {
                "file_count": repo_contents.get("file_count", 0),
                "code_file_count": repo_contents.get("code_file_count", 0),
                "total_lines": repo_contents.get("total_lines", 0),
                "file_breakdown": repo_contents.get("file_breakdown", {}),
            }
        )

        # Count actual content from files
        content_token_count = 0
        processed_files = repo_contents.get("processed_files", [])

        for file in processed_files:
            if "content" in file and isinstance(file["content"], str):
                # Skip files that are binary or too large
                if file["content"].startswith("[Binary file:") or file["content"].startswith(
                    "[File too large:"
                ):
                    # Just count the message itself
                    content_token_count += default_token_counter.count_tokens(file["content"])
                else:
                    # For actual code content, use the code-specific counting method
                    content_token_count += default_token_counter.count_tokens_in_code(
                        file["content"]
                    )

        token_count = metadata_token_count + content_token_count

        logger.debug(
            f"Estimated token count: {token_count} "
            + f"(metadata: {metadata_token_count}, content: {content_token_count})"
        )

        return token_count

    def process_repository_contents(
        self,
        repo_dir: str,
        include_full_code: bool = False,
        exclusion_patterns: Dict[str, List[str]] = None,
    ) -> Dict[str, Any]:
        """Process the downloaded repository contents.

        Args:
            repo_dir: Path to the directory containing the extracted repository
            include_full_code: Whether to include full code content in the results
            exclusion_patterns: Dictionary with exclusion patterns for directories, files, extensions, and regex patterns

        Returns:
            Dictionary with processed repository information
        """
        import fnmatch
        import re

        logger.info(f"Processing repository content from {repo_dir}")

        # Initialize exclusion patterns
        exclude_dirs = []
        exclude_files = []
        exclude_exts = []
        exclude_regexes = []

        if exclusion_patterns:
            exclude_dirs = exclusion_patterns.get("dirs", [])
            exclude_files = exclusion_patterns.get("files", [])
            exclude_exts = exclusion_patterns.get("extensions", [])
            exclude_regexes = [
                re.compile(pattern) for pattern in exclusion_patterns.get("regexes", [])
            ]

        result = {
            "file_count": 0,
            "code_file_count": 0,
            "total_lines": 0,
            "file_breakdown": {},
            "top_files": [],
            "processed_files": [],
            "excluded_files_count": 0,
        }

        all_files = []

        # Walk the directory and collect files
        for root, _, files in os.walk(repo_dir):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repo_dir)

                # Check if file should be excluded
                skip_file = False

                # Apply standard exclusion rules for non-full-code mode
                if not include_full_code:
                    # In regular mode, skip hidden files and common dependency directories
                    if any(segment.startswith(".") for segment in relative_path.split(os.sep)):
                        skip_file = True
                    if any(
                        ignored in relative_path
                        for ignored in ["node_modules/", "__pycache__/", "venv/", ".tox/", "dist/"]
                    ):
                        skip_file = True

                # Apply custom exclusion patterns
                if not skip_file:
                    # Check directory exclusion patterns (simplified glob matching)
                    for pattern in exclude_dirs:
                        if fnmatch.fnmatch(os.path.dirname(relative_path), pattern):
                            skip_file = True
                            result["excluded_files_count"] += 1
                            break

                    # Check file exclusion patterns (simplified glob matching)
                    if not skip_file:
                        for pattern in exclude_files:
                            if fnmatch.fnmatch(os.path.basename(relative_path), pattern):
                                skip_file = True
                                result["excluded_files_count"] += 1
                                break

                    # Check extension exclusion
                    if not skip_file:
                        file_ext = os.path.splitext(file)[1].lower()
                        if file_ext and file_ext[1:] in exclude_exts:  # Remove leading dot
                            skip_file = True
                            result["excluded_files_count"] += 1

                    # Check regex patterns
                    if not skip_file:
                        for regex in exclude_regexes:
                            if regex.search(relative_path):
                                skip_file = True
                                result["excluded_files_count"] += 1
                                break

                if not skip_file:
                    is_code_file = file.lower().endswith(CODE_EXTENSIONS)
                    file_size = os.path.getsize(file_path)

                    all_files.append(
                        {
                            "path": relative_path,
                            "is_code": is_code_file,
                            "size": file_size,
                            "lines": 0,  # Will be populated later
                        }
                    )

                    result["file_count"] += 1
                    if is_code_file:
                        result["code_file_count"] += 1

                    # Track file types
                    ext = os.path.splitext(file)[1].lower()
                    result["file_breakdown"][ext] = result["file_breakdown"].get(ext, 0) + 1

        # Sort files
        if include_full_code:
            # For full code mode, sort alphabetically by path for consistency
            all_files.sort(key=lambda f: f["path"])
        else:
            # For summary mode, sort by size (largest first)
            all_files.sort(key=lambda f: f["size"], reverse=True)

        # When full_code is True, process ALL files, otherwise limit to max_files
        files_to_process = all_files if include_full_code else all_files[: self.max_files]

        # Process files
        for file_info in files_to_process:
            try:
                file_path = os.path.join(repo_dir, file_info["path"])

                # Special handling for very large files regardless of mode
                if file_info["size"] > 10 * 1024 * 1024:  # 10MB safety limit
                    file_info["content"] = (
                        f"[File too large to process: {file_info['size'] / (1024 * 1024):.2f} MB]"
                    )
                    file_info["lines"] = 0
                    logger.warning(
                        f"Skipping very large file: {file_info['path']} ({file_info['size'] / (1024 * 1024):.2f} MB)"
                    )
                    continue

                if include_full_code:
                    # In full code mode, try to read everything without truncation
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            lines = content.splitlines()
                            file_info["lines"] = len(lines)
                            file_info["content"] = content  # No truncation in full code mode
                            if file_info["is_code"]:
                                result["total_lines"] += len(lines)
                    except UnicodeDecodeError:
                        # For binary files, just note that it's binary
                        file_info["content"] = f"[Binary file: {file_info['size'] / 1024:.2f} KB]"
                        file_info["lines"] = 0
                        logger.debug(f"Binary file detected: {file_info['path']}")
                else:
                    # In regular mode, apply more filtering and truncation
                    if file_info["size"] > self.max_file_size:
                        file_info["content"] = (
                            f"File too large: {file_info['size'] / (1024 * 1024):.2f} MB"
                        )
                        continue

                    if file_info["is_code"]:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            lines = content.splitlines()
                            file_info["lines"] = len(lines)
                            file_info["content"] = (
                                content[:10000] + "..." if len(content) > 10000 else content
                            )
                            result["total_lines"] += len(lines)
                    else:
                        file_info["content"] = f"Non-code file: {file_info['path']}"

            except Exception as e:
                file_info["content"] = f"Error reading file: {str(e)}"
                logger.warning(f"Error processing file {file_info['path']}: {e}")

        # Store all processed files in the result
        result["processed_files"] = files_to_process

        # Create a list of top files by lines (for display purposes only)
        code_files = [f for f in all_files if f["is_code"] and "lines" in f]
        result["top_files"] = sorted(code_files, key=lambda f: f["lines"], reverse=True)[:20]

        logger.info(
            f"Processed {result['file_count']} files, {result['code_file_count']} code files with {result['total_lines']} lines"
        )
        if result["excluded_files_count"] > 0:
            logger.info(
                f"Excluded {result['excluded_files_count']} files based on exclusion patterns"
            )

        return result

    def format_repository_for_llm(self, repo_summary: Dict[str, Any]) -> str:
        """Format repository summary into Markdown for LLM consumption.

        Args:
            repo_summary: Repository summary dictionary from get_repository_summary

        Returns:
            A Markdown-formatted string for the LLM
        """
        output_lines = []

        # Project header
        project = repo_summary["project_info"]
        output_lines.append(f"# GitLab Repository: {project['name_with_namespace']}")
        output_lines.append("")

        # Basic information
        output_lines.append("## Repository Overview")
        output_lines.append(f"* **URL:** {project['web_url']}")
        output_lines.append(f"* **Description:** {project.get('description', 'No description')}")
        output_lines.append(f"* **Default Branch:** {project.get('default_branch', 'main')}")
        output_lines.append(f"* **Visibility:** {project.get('visibility', 'unknown')}")
        if project.get("star_count") is not None:
            output_lines.append(f"* **Stars:** {project['star_count']}")
        if project.get("fork_count") is not None:
            output_lines.append(f"* **Forks:** {project['fork_count']}")
        if project.get("created_at"):
            output_lines.append(f"* **Created:** {project['created_at']}")
        if project.get("last_activity_at"):
            output_lines.append(f"* **Last Activity:** {project['last_activity_at']}")
        output_lines.append("")

        # Contributors
        if repo_summary.get("contributors"):
            output_lines.append("## Contributors")
            for c in repo_summary["contributors"]:
                output_lines.append(f"* {c['name']} ({c['email']}) - {c['commits']} commits")
            output_lines.append("")

        # Last commit
        if repo_summary.get("last_commit"):
            commit = repo_summary["last_commit"]
            output_lines.append("## Latest Commit")
            output_lines.append(f"* **ID:** {commit['short_id']}")
            output_lines.append(f"* **Author:** {commit['author_name']}")
            output_lines.append(f"* **Date:** {commit['committed_date']}")
            output_lines.append(f"* **Message:** {commit['message']}")
            output_lines.append("")

        # Repository stats
        contents = repo_summary.get("repository_contents", {})
        output_lines.append("## Repository Statistics")
        output_lines.append(f"* **Total Files:** {contents.get('file_count', 'Unknown')}")
        output_lines.append(f"* **Code Files:** {contents.get('code_file_count', 'Unknown')}")
        output_lines.append(f"* **Total Lines:** {contents.get('total_lines', 'Unknown')}")

        # File breakdown by extension
        if contents.get("file_breakdown"):
            output_lines.append("\n### File Types")
            for ext, count in sorted(
                contents.get("file_breakdown", {}).items(), key=lambda x: x[1], reverse=True
            )[:10]:
                output_lines.append(f"* {ext or 'no extension'}: {count} files")

        # Top files by line count
        if contents.get("top_files"):
            output_lines.append("\n### Top Files by Line Count")
            for file in contents.get("top_files", [])[:10]:
                output_lines.append(f"* {file['path']} - {file['lines']} lines")

        # Complete source code section - include all files
        all_files = contents.get("processed_files", [])

        if all_files:
            output_lines.append("\n## Source Code")
            output_lines.append(
                f"This section contains all {len(all_files)} files from the repository."
            )

            for file in all_files:
                output_lines.append(f"\n### {file['path']} ({file.get('lines', 0)} lines)")

                # Get file extension for syntax highlighting
                ext = os.path.splitext(file["path"])[1][1:]  # Get extension without dot
                if ext:
                    lang = ext
                    # Map common extensions to their language names
                    if ext in ["py", "pyx", "pyw"]:
                        lang = "python"
                    elif ext in ["js", "jsx"]:
                        lang = "javascript"
                    elif ext in ["ts", "tsx"]:
                        lang = "typescript"
                    elif ext in ["md", "markdown"]:
                        lang = "markdown"
                    elif ext in ["yml", "yaml"]:
                        lang = "yaml"
                    # Add code fence with language
                    output_lines.append(f"```{lang}")
                else:
                    # No extension, use plain code fence
                    output_lines.append("```")

                # Add file content
                content = file.get("content", "")
                if content.startswith("[Binary file:") or content.startswith("[File too large:"):
                    # For binary files or very large files, just show the notice
                    output_lines.append(content)
                else:
                    # For text files, add the content
                    output_lines.append(content)

                output_lines.append("```")

        return "\n".join(output_lines)

    def format_merge_request_for_llm(self, mr_data: Dict[str, Any]) -> str:
        """Format merge request information into Markdown for LLM consumption.

        Args:
            mr_data: Merge request data from get_merge_request

        Returns:
            A Markdown-formatted string for the LLM
        """
        output_lines = []

        # MR header
        output_lines.append(f"# GitLab Merge Request: {mr_data['title']}")
        output_lines.append(f"**ID:** !{mr_data['id']}")
        output_lines.append(f"**URL:** {mr_data['web_url']}")
        output_lines.append("")

        # Basic information
        output_lines.append("## Merge Request Details")
        output_lines.append(f"* **State:** {mr_data['state']}")
        output_lines.append(
            f"* **Source → Target:** `{mr_data['source_branch']}` → `{mr_data['target_branch']}`"
        )
        output_lines.append(
            f"* **Author:** {mr_data['author']['name']} (@{mr_data['author']['username']})"
        )
        if mr_data.get("assignee"):
            output_lines.append(
                f"* **Assignee:** {mr_data['assignee']['name']} (@{mr_data['assignee']['username']})"
            )
        output_lines.append(f"* **Created:** {mr_data['created_at']}")
        output_lines.append(f"* **Updated:** {mr_data['updated_at']}")
        output_lines.append("")

        # Description
        if mr_data.get("description"):
            output_lines.append("## Description")
            output_lines.append(mr_data["description"])
            output_lines.append("")

        # Changes
        output_lines.append("## Changes")
        changes_count = mr_data.get("changes_count", len(mr_data.get("changes", [])))
        if changes_count:
            output_lines.append(f"This merge request contains {changes_count} changed files.")

            if mr_data.get("changes_error"):
                output_lines.append(f"Error fetching changes: {mr_data['changes_error']}")
            elif not mr_data.get("changes"):
                output_lines.append("No change details available.")
            else:
                output_lines.append("")

                # Show each change with diff
                for i, change in enumerate(mr_data["changes"]):
                    new_path = change.get("new_path")
                    old_path = change.get("old_path")
                    diff = change.get("diff", "")

                    if new_path == old_path:
                        output_lines.append(f"### {i + 1}. Modified: {new_path}")
                    elif old_path == "/dev/null":
                        output_lines.append(f"### {i + 1}. Added: {new_path}")
                    elif new_path == "/dev/null":
                        output_lines.append(f"### {i + 1}. Deleted: {old_path}")
                    else:
                        output_lines.append(f"### {i + 1}. Renamed: {old_path} → {new_path}")

                    # Format diff
                    if diff:
                        # Determine language for syntax highlighting
                        ext = os.path.splitext(new_path or old_path)[1].lower()
                        lang = ""
                        if ext in (".py", ".pyx"):
                            lang = "python"
                        elif ext in (".js", ".jsx"):
                            lang = "javascript"
                        elif ext in (".ts", ".tsx"):
                            lang = "typescript"
                        elif ext in (".go"):
                            lang = "go"
                        elif ext in (".java"):
                            lang = "java"
                        elif ext in (".rb"):
                            lang = "ruby"
                        elif ext in (".php"):
                            lang = "php"
                        elif ext in (".html", ".htm"):
                            lang = "html"
                        elif ext in (".css"):
                            lang = "css"
                        elif ext in (".md"):
                            lang = "markdown"
                        elif ext in (".json"):
                            lang = "json"
                        elif ext in (".yml", ".yaml"):
                            lang = "yaml"

                        output_lines.append(f"```{lang}")

                        # Limit diff size
                        if len(diff) > 5000:
                            diff = diff[:5000] + "\n... [diff truncated] ..."

                        output_lines.append(diff)
                        output_lines.append("```")

                    output_lines.append("")
        else:
            output_lines.append("No changes found in this merge request.")

        return "\n".join(output_lines)

    def cleanup_temp_dir(self) -> None:
        """Clean up the temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.debug(f"Cleaned up temporary directory: {self.temp_dir}")
                self.temp_dir = None
            except Exception as e:
                logger.warning(f"Error cleaning up temporary directory {self.temp_dir}: {e}")

    def close(self) -> None:
        """Close resources and clean up."""
        self._client = None
        self.cleanup_temp_dir()

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.close()
