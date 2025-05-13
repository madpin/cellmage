"""
GitHub utility for interacting with the GitHub API.

This module provides the GitHubUtils class for fetching repositories, code, and pull requests.
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

# Flag to check if PyGithub is available
_GITHUB_AVAILABLE = False

try:
    from github import Auth, Github
    from github.GithubException import GithubException
    from github.PullRequest import PullRequest
    from github.Repository import Repository

    _GITHUB_AVAILABLE = True
except ImportError:
    # Define placeholder types for type checking when PyGithub package is not available
    Github = object
    Repository = object
    PullRequest = object
    GithubException = Exception

# --- Constants ---
DEFAULT_MAX_FILES = 200
DEFAULT_MAX_PR_CHANGES = 100
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
    if isinstance(arg, dict):
        return tuple(sorted((k, _make_hashable(v)) for k, v in arg.items()))
    elif isinstance(arg, list):
        return tuple(_make_hashable(x) for x in arg)
    elif isinstance(arg, set):
        return frozenset(_make_hashable(x) for x in arg)
    return arg


# Custom cache decorator to handle unhashable arguments
def hashable_lru_cache(maxsize=128, typed=False):
    """LRU cache decorator that works with unhashable arguments."""

    def decorator(func):
        @lru_cache(maxsize=maxsize, typed=typed)
        def cached_func(*args, **kwargs):
            # The real function will receive the original arguments
            return func(*args, **kwargs)

        def wrapper(*args, **kwargs):
            hashable_args = tuple(_make_hashable(arg) for arg in args)
            hashable_kwargs = {k: _make_hashable(v) for k, v in kwargs.items()}
            return cached_func(*hashable_args, **hashable_kwargs)

        wrapper.cache_info = cached_func.cache_info
        wrapper.cache_clear = cached_func.cache_clear
        return wrapper

    return decorator


class GitHubUtils:
    """
    Utility class for interacting with the GitHub API.

    Fetches and processes GitHub repositories, pull requests, and code content,
    preparing data for analysis or LLM input.
    """

    _client: Optional[Any] = None

    def __init__(
        self,
        token: Optional[str] = None,
        max_files: int = DEFAULT_MAX_FILES,
        max_pr_changes: int = DEFAULT_MAX_PR_CHANGES,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
    ):
        """
        Initialize the GitHub utils.

        Args:
            token: GitHub personal access token.
            max_files: Maximum number of files to process in a repository.
            max_pr_changes: Maximum number of file changes to process in a pull request.
            max_file_size: Maximum size of individual files to process.
        """
        if not _GITHUB_AVAILABLE:
            raise ImportError(
                "The PyGithub package is required to use GitHub utilities. "
                "Please install it with 'pip install PyGithub'."
            )

        # Try to load from .env using dotenv if available
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass  # Continue without dotenv

        self.token = token or os.getenv("GITHUB_TOKEN")
        self.max_files = max_files
        self.max_pr_changes = max_pr_changes
        self.max_file_size = max_file_size
        self.temp_dir = None

        # Validate essential configuration
        if not self.token:
            raise ValueError("GitHub token is required (provide via arg or GITHUB_TOKEN env var).")

        logger.info("GitHubUtils initialized")
        # Client is initialized lazily via the 'client' property

    @property
    def client(self) -> Github:
        """Lazy-initialized GitHub client."""
        if self._client is None:
            logger.info("Connecting to GitHub...")
            try:
                auth = Auth.Token(self.token)
                self._client = Github(auth=auth)
                # Test the connection by getting the authenticated user
                _ = self._client.get_user().login
                logger.info("Successfully connected to GitHub.")
            except GithubException as e:
                logger.error(f"GitHub authentication failed: {str(e)}", exc_info=True)
                raise RuntimeError(f"Failed to authenticate with GitHub: {str(e)}") from e
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred during GitHub connection: {e}", exc_info=True
                )
                raise RuntimeError(f"Unexpected error connecting to GitHub: {str(e)}") from e
        return self._client

    @hashable_lru_cache(maxsize=256)
    def get_repository(self, repository_identifier: str) -> Repository:
        """
        Get a GitHub repository by full name (username/repo).

        Args:
            repository_identifier: Repository identifier in format "username/repo"

        Returns:
            The Repository object
        """
        try:
            repo = self.client.get_repo(repository_identifier)
            # Access an attribute to test that the repo exists
            _ = repo.name
            return repo
        except GithubException as e:
            logger.error(f"Error fetching GitHub repository: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to fetch GitHub repository: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error fetching repository: {e}", exc_info=True)
            raise RuntimeError(f"Unexpected error fetching GitHub repository: {str(e)}") from e

    def download_repository(self, repo: Repository) -> str:
        """
        Download a GitHub repository and extract it to a temporary directory.

        Args:
            repo: The Repository object to download

        Returns:
            Path to the directory containing the extracted repository
        """
        try:
            # Clean up any previous downloads
            self.cleanup_temp_dir()

            # Create a new temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix="cellmage_github_")
            logger.info(f"Created temporary directory: {self.temp_dir}")

            # Get the default branch to download
            default_branch = repo.default_branch
            archive_url = repo.get_archive_link("zipball", ref=default_branch)

            # Download the zip file
            import requests

            zip_path = os.path.join(self.temp_dir, "repo.zip")
            headers = {"Authorization": f"token {self.token}"}
            response = requests.get(archive_url, headers=headers, stream=True)
            response.raise_for_status()

            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded repository archive to {zip_path}")

            # Extract the zip file
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # The zip file has a root directory with a generated name
                # Extract to get the name of this directory
                zip_ref.extractall(path=self.temp_dir)

            # Find the extracted directory (should be the only directory)
            extraction_dirs = [
                d
                for d in os.listdir(self.temp_dir)
                if os.path.isdir(os.path.join(self.temp_dir, d))
            ]
            if extraction_dirs:
                extracted_dir = os.path.join(self.temp_dir, extraction_dirs[0])
                logger.info(f"Extracted repository to {extracted_dir}")
                # Return the path to the extracted directory
                return extracted_dir
            else:
                logger.warning(
                    f"No directories found in extraction. Assuming code is at {self.temp_dir}"
                )
                logger.warning(
                    f"Code assumed to be at the root of the extraction directory: {self.temp_dir}"
                )
                return self.temp_dir

        except GithubException as e:
            logger.error(
                f"GitHub API Error downloading archive: {e.status} - {e.data.get('message', '')}"
            )
            self.cleanup_temp_dir()
            raise RuntimeError(f"Failed to download repository archive: {e}") from e
        except zipfile.BadZipFile:
            logger.error("Downloaded file is not a valid ZIP archive.")
            self.cleanup_temp_dir()
            raise RuntimeError("Downloaded file is not a valid ZIP archive.") from None
        except Exception as e:
            logger.error(f"An error occurred during download/extraction: {e}", exc_info=True)
            self.cleanup_temp_dir()
            raise RuntimeError(f"Failed to download or extract repository: {str(e)}") from e

    def get_pull_request(self, repo: Repository, pr_number: Union[int, str]) -> Dict[str, Any]:
        """
        Get information about a pull request including changes.

        Args:
            repo: The Repository object
            pr_number: The ID of the pull request

        Returns:
            Dictionary with PR information and changes
        """
        try:
            pr_number = int(pr_number)
            pr = repo.get_pull(pr_number)

            # Basic PR info
            pr_info = {
                "number": pr.number,
                "title": pr.title,
                "description": pr.body or "",
                "state": pr.state,
                "source_branch": pr.head.ref,
                "target_branch": pr.base.ref,
                "created_at": pr.created_at.isoformat() if pr.created_at else None,
                "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                "web_url": pr.html_url,
                "changes": [],
            }

            # Author info
            if pr.user:
                pr_info["author"] = {
                    "name": pr.user.name or pr.user.login,
                    "username": pr.user.login,
                }

            # Assignee info
            if pr.assignee:
                pr_info["assignee"] = {
                    "name": pr.assignee.name or pr.assignee.login,
                    "username": pr.assignee.login,
                }

            # Process changes (diffs)
            files = pr.get_files()
            pr_info["changes_count"] = files.totalCount

            # Process the changes
            for i, file in enumerate(files):
                if i >= self.max_pr_changes:
                    break

                change_info = {
                    "old_path": (
                        file.previous_filename
                        if hasattr(file, "previous_filename")
                        else file.filename
                    ),
                    "new_path": file.filename,
                    "status": file.status,  # added, modified, removed, renamed
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                    "patch": file.patch,  # The git diff
                }

                pr_info["changes"].append(change_info)

            logger.info(f"Successfully fetched PR #{pr_number} from {repo.full_name}")
            return pr_info

        except GithubException as e:
            logger.error(f"Error fetching PR #{pr_number}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to fetch PR #{pr_number}: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error fetching PR #{pr_number}: {e}", exc_info=True)
            raise RuntimeError(f"Unexpected error fetching PR #{pr_number}: {e}") from e

    def get_repository_summary(
        self,
        repository_identifier: str,
        full_code: bool = False,
        contributors_months: int = 6,
        exclusion_patterns: Dict[str, List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get a comprehensive summary of a GitHub repository.

        Args:
            repository_identifier: Repository identifier in format "username/repo"
            full_code: Whether to include full code contents
            contributors_months: Number of months to consider for contributor activity
            exclusion_patterns: Patterns to exclude files/directories

        Returns:
            Dictionary with repository information
        """
        try:
            result = {
                "project_info": {},
                "last_commit": {},
                "contributors": [],
                "estimated_tokens": 0,
            }

            # 1. Get the repository
            repo = self.get_repository(repository_identifier)

            # 2. Store repository information
            result["project_info"] = {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "default_branch": repo.default_branch,
                "web_url": repo.html_url,
                "visibility": "public" if not repo.private else "private",
                "star_count": repo.stargazers_count,
                "fork_count": repo.forks_count,
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "last_activity_at": repo.updated_at.isoformat() if repo.updated_at else None,
            }

            # 3. Get the latest commit information
            try:
                commits = list(repo.get_commits(sha=repo.default_branch, per_page=1))
                if commits:
                    commit = commits[0]
                    result["last_commit"] = {
                        "id": commit.sha,
                        "short_id": commit.sha[:7],
                        "author_name": commit.commit.author.name,
                        "authored_date": (
                            commit.commit.author.date.isoformat()
                            if commit.commit.author.date
                            else None
                        ),
                        "committer_name": commit.commit.committer.name,
                        "committed_date": (
                            commit.commit.committer.date.isoformat()
                            if commit.commit.committer.date
                            else None
                        ),
                        "message": commit.commit.message,
                    }
            except Exception as e:
                logger.warning(f"Could not fetch latest commit: {e}")

            # 4. Get contributors with commit activity
            try:
                # Calculate date from N months ago
                import datetime

                today = datetime.datetime.now()
                months_ago = today - datetime.timedelta(days=30 * contributors_months)
                months_ago_str = months_ago.isoformat()

                # Get contributors from repo
                stats = repo.get_stats_contributors()
                if stats is None:
                    # GitHub might need to calculate stats
                    logger.info("GitHub needs to calculate contributor stats, they'll be empty")
                    result["contributors"] = []
                else:
                    contributors_dict = {}

                    # Process contributors
                    for stat in stats:
                        contributor = stat.author
                        name = contributor.name or contributor.login
                        email = contributor.email or f"{contributor.login}@github.com"

                        # Filter by date if necessary
                        weekly_commits = stat.weeks
                        # Count commits in the last N months
                        recent_commits = sum(
                            week.c
                            for week in weekly_commits
                            if week.w > int(months_ago.timestamp())
                        )

                        if name not in contributors_dict:
                            contributors_dict[name] = {
                                "name": name,
                                "email": email,
                                "commits": 0,
                                "last_commit_date": None,
                            }

                        # Update commit count
                        contributors_dict[name]["commits"] += recent_commits

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
            repo_path = self.download_repository(repo)
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

            logger.info(f"Successfully generated repository summary for {repository_identifier}")
            return result

        except Exception as e:
            logger.error(f"Failed to generate repository summary: {e}", exc_info=True)
            raise
        finally:
            # Clean up temporary files
            self.cleanup_temp_dir()

    def process_repository_contents(
        self,
        repo_dir: str,
        include_full_code: bool = False,
        exclusion_patterns: Dict[str, List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Process repository contents, collecting file information and code.

        Args:
            repo_dir: Path to the directory containing the extracted repository
            include_full_code: Whether to include full code contents
            exclusion_patterns: Patterns to exclude files/directories

        Returns:
            Dictionary with repository content information
        """
        import fnmatch
        import re

        # Process exclusion patterns
        exclusion_patterns = exclusion_patterns or {}
        exclude_dirs = exclusion_patterns.get("dirs", [])
        exclude_files = exclusion_patterns.get("files", [])
        exclude_exts = [ext.lstrip(".") for ext in exclusion_patterns.get("extensions", [])]
        exclude_regexes = [re.compile(pattern) for pattern in exclusion_patterns.get("regexes", [])]

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
                        f"[File too large: {file_info['size'] / 1024 / 1024:.2f} MB]"
                    )
                    file_info["lines"] = 0
                    logger.debug(f"File too large to process: {file_info['path']}")
                    continue

                # Process files differently based on mode
                if include_full_code:
                    # In full code mode, include everything (up to the max file size limit)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
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
                            f"[File too large: {file_info['size'] / 1024 / 1024:.2f} MB]"
                        )
                        file_info["lines"] = 0
                        continue

                    try:
                        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                            lines = content.splitlines()
                            file_info["lines"] = len(lines)

                            # Truncate very long files for display
                            max_lines = 100  # Adjust as needed
                            if len(lines) > max_lines and not include_full_code:
                                # Show beginning and end with a notice in between
                                first_chunk = "\n".join(lines[: max_lines // 2])
                                last_chunk = "\n".join(lines[-(max_lines // 2) :])
                                content = (
                                    f"{first_chunk}\n\n"
                                    f"[...{len(lines) - max_lines} more lines...]\n\n"
                                    f"{last_chunk}"
                                )
                                file_info["content"] = content
                            else:
                                file_info["content"] = content

                            if file_info["is_code"]:
                                result["total_lines"] += len(lines)
                    except UnicodeDecodeError:
                        # For binary files, just note that it's binary
                        file_info["content"] = f"[Binary file: {file_info['size'] / 1024:.2f} KB]"
                        file_info["lines"] = 0

                # Add to processed files
                result["processed_files"].append(file_info)

            except Exception as e:
                logger.warning(f"Error processing file {file_info['path']}: {e}")
                file_info["content"] = f"[Error reading file: {str(e)}]"
                file_info["lines"] = 0

        # Determine top files by line count
        code_files = [f for f in all_files if f["is_code"]]
        code_files.sort(key=lambda f: f["lines"], reverse=True)
        result["top_files"] = code_files[:20]  # Top 20 files by line count

        logger.info(
            f"Processed {result['file_count']} files ({result['code_file_count']} code files)"
        )
        if exclusion_patterns:
            logger.info(
                f"Excluded {result['excluded_files_count']} files based on exclusion patterns"
            )

        return result

    def _estimate_tokens_from_dict(self, data: Dict[str, Any]) -> int:
        """Estimate the number of tokens in a dictionary."""
        try:
            # Serializing the dict and using the tokenizer provides a better estimate
            import json

            return default_token_counter(json.dumps(data))
        except Exception:
            # Fallback if we can't tokenize: roughly estimate 4 chars per token
            import json

            return len(json.dumps(data)) // 4

    def _estimate_tokens_from_list(self, data: List[Any], max_items: Optional[int] = None) -> int:
        """Estimate the number of tokens in a list."""
        try:
            if max_items is not None and len(data) > max_items:
                data = data[:max_items]

            import json

            return default_token_counter(json.dumps(data))
        except Exception:
            # Fallback
            import json

            return len(json.dumps(data)) // 4

    def _estimate_tokens_from_repo_contents(self, repo_contents: Dict[str, Any]) -> int:
        """Estimate the number of tokens from repository contents using tiktoken or fallback method."""
        try:
            # Sum up tokens in all processed files
            total_tokens = 0
            for file in repo_contents.get("processed_files", []):
                content = file.get("content", "")
                total_tokens += default_token_counter(content)

            return total_tokens
        except Exception:
            # Very rough fallback estimate based on character count
            total_chars = 0
            for file in repo_contents.get("processed_files", []):
                content = file.get("content", "")
                total_chars += len(content)

            # Rough estimate of 4 characters per token
            return total_chars // 4

    def format_repository_for_llm(self, repo_summary: Dict[str, Any]) -> str:
        """
        Format repository data for LLM consumption.

        Args:
            repo_summary: Repository summary from get_repository_summary()

        Returns:
            Formatted string representing the repository
        """
        import os

        output_lines = []

        # Repository information
        project = repo_summary.get("project_info", {})
        output_lines.append(f"# GitHub Repository: {project.get('full_name', '')}")
        output_lines.append("")
        output_lines.append(f"* **Description:** {project.get('description', '')}")
        output_lines.append(f"* **URL:** {project.get('web_url', '')}")
        output_lines.append(f"* **Default Branch:** {project.get('default_branch', '')}")
        if project.get("visibility"):
            output_lines.append(f"* **Visibility:** {project['visibility']}")
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

    def format_pull_request_for_llm(self, pr_data: Dict[str, Any]) -> str:
        """
        Format pull request data for LLM consumption.

        Args:
            pr_data: Pull request data from get_pull_request()

        Returns:
            Formatted string representing the pull request
        """
        import os

        output_lines = []

        # PR header information
        output_lines.append(f"# Pull Request #{pr_data.get('number')}: {pr_data.get('title', '')}")
        output_lines.append("")

        # Basic information
        output_lines.append(f"* **Repository:** {pr_data.get('repository', '')}")
        output_lines.append(f"* **URL:** {pr_data.get('web_url', '')}")
        output_lines.append(f"* **State:** {pr_data.get('state', '')}")
        output_lines.append(f"* **Source Branch:** {pr_data.get('source_branch', '')}")
        output_lines.append(f"* **Target Branch:** {pr_data.get('target_branch', '')}")

        # Author and assignee
        if pr_data.get("author"):
            output_lines.append(f"* **Author:** {pr_data['author'].get('name', '')}")
        if pr_data.get("assignee"):
            output_lines.append(f"* **Assignee:** {pr_data['assignee'].get('name', '')}")

        # Dates
        if pr_data.get("created_at"):
            output_lines.append(f"* **Created:** {pr_data['created_at']}")
        if pr_data.get("updated_at"):
            output_lines.append(f"* **Updated:** {pr_data['updated_at']}")

        # Description
        if pr_data.get("description"):
            output_lines.append("\n## Description")
            output_lines.append(pr_data["description"])

        # Changes summary
        output_lines.append("\n## Changes")
        output_lines.append(f"* **Files changed:** {pr_data.get('changes_count', 0)}")

        # Detailed changes
        if pr_data.get("changes"):
            output_lines.append("\n## File Changes")

            for i, change in enumerate(pr_data["changes"]):
                old_path = change.get("old_path", "")
                new_path = change.get("new_path", "")
                status = change.get("status", "")
                additions = change.get("additions", 0)
                deletions = change.get("deletions", 0)
                diff = change.get("patch", "")

                # Format based on change type
                if status == "added":
                    output_lines.append(f"### {i + 1}. Added: {new_path}")
                    output_lines.append(f"* {additions} additions, {deletions} deletions")
                elif status == "removed":
                    output_lines.append(f"### {i + 1}. Removed: {old_path}")
                    output_lines.append(f"* {additions} additions, {deletions} deletions")
                elif status == "modified":
                    output_lines.append(f"### {i + 1}. Modified: {new_path}")
                    output_lines.append(f"* {additions} additions, {deletions} deletions")
                elif status == "renamed":
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

                    # Wrap in code fence with language
                    output_lines.append(f"```{lang}")
                    output_lines.append(diff)
                    output_lines.append("```")

        return "\n".join(output_lines)

    def cleanup_temp_dir(self):
        """Clean up the temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
                self.temp_dir = None
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory: {e}")
