"""
IPython magic command for GitHub integration with CellMage.

This module provides magic commands for fetching GitHub repositories and pull requests
to use as context in LLM prompts.
"""

import logging
import sys
from typing import Any, Dict, List, Optional, Union

# IPython imports with fallback handling
try:
    from IPython.core.magic import line_magic, magics_class
    from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring

    _IPYTHON_AVAILABLE = True
except ImportError:
    _IPYTHON_AVAILABLE = False

    # Define dummy decorators if IPython is not installed
    def magics_class(cls):
        return cls

    def line_magic(func):
        return func

    def magic_arguments():
        return lambda func: func

    def argument(*args, **kwargs):
        return lambda func: func


from cellmage.integrations.github_utils import GitHubUtils

# Import the base magic class
from cellmage.magic_commands.tools.base_tool_magic import BaseMagics

# Create a global logger
logger = logging.getLogger(__name__)

# Attempt to import GitHub utils
try:
    import os

    _GITHUB_AVAILABLE = True
except ImportError:
    _GITHUB_AVAILABLE = False


@magics_class
class GitHubMagics(BaseMagics):
    """IPython magic commands for fetching and using GitHub repositories and pull requests as context."""

    def __init__(self, shell):
        """Initialize the GitHub magic utility."""
        if not _IPYTHON_AVAILABLE:
            logger.warning("IPython not found. GitHub magics are disabled.")
            return

        super().__init__(shell)
        self.github_utils = None
        self._init_github_client()

    def _init_github_client(self) -> None:
        """Initialize the GitHub client if possible."""
        if not _GITHUB_AVAILABLE:
            logger.warning("GitHub package not available. Please install the PyGithub package.")
            return

        try:
            # Import required modules for GitHub utils
            from dotenv import load_dotenv

            # Load environment variables
            load_dotenv()

            # Check for required environment variables
            github_token = os.getenv("GITHUB_TOKEN")

            if not github_token:
                logger.warning("Missing GitHub environment variables. Please set GITHUB_TOKEN.")
                return

            # Try to initialize GitHubUtils
            try:
                self.github_utils = GitHubUtils(token=github_token)
                logger.info("GitHubUtils initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize GitHubUtils: {e}")
        except Exception as e:
            logger.error(f"Error during GitHub client initialization: {e}")

    def _fetch_repository(
        self,
        repository_identifier: str,
        full_code: bool = False,
        contributors_months: int = 6,
        exclusion_patterns: Optional[Dict[str, List[str]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a GitHub repository by repository identifier and return processed data."""
        if self.github_utils is None:
            print("❌ GitHub client not available")
            return None

        try:
            kwargs = {"full_code": full_code, "contributors_months": contributors_months}

            if exclusion_patterns:
                kwargs["exclusion_patterns"] = exclusion_patterns

            repo_summary = self.github_utils.get_repository_summary(repository_identifier, **kwargs)
            return repo_summary
        except Exception as e:
            print(f"❌ Error fetching GitHub repository {repository_identifier}: {e}")
            logger.error(f"Error fetching GitHub repository {repository_identifier}: {e}")
            return None

    def _fetch_pull_request(
        self, repository_identifier: str, pr_number: Union[int, str]
    ) -> Optional[Dict[str, Any]]:
        """Fetch a GitHub pull request by number and return processed data."""
        if self.github_utils is None:
            print("❌ GitHub client not available")
            return None

        try:
            repo = self.github_utils.get_repository(repository_identifier)
            pr_data = self.github_utils.get_pull_request(repo, pr_number)
            return pr_data
        except Exception as e:
            print(
                f"❌ Error fetching GitHub pull request {pr_number} from {repository_identifier}: {e}"
            )
            logger.error(
                f"Error fetching GitHub pull request {pr_number} from {repository_identifier}: {e}"
            )
            return None

    def _format_repository_for_display(self, repo_data: Dict[str, Any]) -> str:
        """Format repository data for terminal display."""
        if not repo_data:
            return "No repository data available"

        return self.github_utils.format_repository_for_llm(repo_data)

    def _format_pr_for_display(self, pr_data: Dict[str, Any]) -> str:
        """Format pull request data for terminal display."""
        if not pr_data:
            return "No pull request data available"

        return self.github_utils.format_pull_request_for_llm(pr_data)

    def _add_to_history(
        self, content: str, source_type: str, source_id: str, as_system_msg: bool = False
    ) -> bool:
        """Add the content to the chat history as a user or system message."""
        return super()._add_to_history(
            content=content,
            source_type=source_type,
            source_id=source_id,
            source_name="github",
            id_key="github_id",
            as_system_msg=as_system_msg,
        )

    def _find_messages_to_remove(
        self, history: List, source_name: str, source_type: str, source_id: str, id_key: str
    ) -> List[int]:
        """
        Find messages to remove from history based on GitHub-specific rules.

        For pull requests, we want to remove all pull requests from the same repository.
        For other content types, we use exact matching.
        """
        indices_to_remove = []

        if source_type == "pull_request":
            # For pull requests, extract the repository name from source_id
            # Format is typically "repo_name#pr_number"
            repo_name = source_id.split("#")[0] if "#" in source_id else source_id

            # Remove ANY pull request from the same repository
            for i, msg in enumerate(history):
                if (
                    msg.metadata
                    and msg.metadata.get("source") == source_name
                    and msg.metadata.get("type") == "pull_request"
                    and msg.metadata.get(id_key, "").startswith(repo_name + "#")
                ):
                    indices_to_remove.append(i)

            if indices_to_remove:
                logger.info(
                    f"Found {len(indices_to_remove)} previous pull requests from repository {repo_name} to remove"
                )
        else:
            # For other content types, use the standard exact match approach
            indices_to_remove = super()._find_messages_to_remove(
                history, source_name, source_type, source_id, id_key
            )

        return indices_to_remove

    @magic_arguments()
    @argument(
        "repo", type=str, nargs="?", help="GitHub repository identifier (e.g., username/repo)"
    )
    @argument("--pr", type=str, help="Pull request number to fetch")
    @argument(
        "--system",
        action="store_true",
        help="Add content as system message instead of user message",
    )
    @argument("--show", action="store_true", help="Only show content without adding to history")
    @argument(
        "--clean",
        action="store_true",
        help="Clean the repository content to focus on code",
    )
    @argument(
        "--full-code",
        action="store_true",
        help="Include all code content from the repository (may be very large)",
    )
    @argument(
        "--exclude-dir",
        type=str,
        action="append",
        metavar="DIR",
        help="Exclude directories matching this pattern (can be used multiple times)",
    )
    @argument(
        "--exclude-file",
        type=str,
        action="append",
        metavar="PATTERN",
        help="Exclude files matching this pattern (can be used multiple times)",
    )
    @argument(
        "--exclude-ext",
        type=str,
        action="append",
        metavar="EXT",
        help="Exclude files with this extension (can be used multiple times)",
    )
    @argument(
        "--exclude-regex",
        type=str,
        action="append",
        metavar="REGEX",
        help="Exclude files matching this regex pattern (can be used multiple times)",
    )
    @argument(
        "--contributors-months",
        type=int,
        default=6,
        help="Include contributors from the last N months (default: 6)",
    )
    @line_magic("github")
    def github_magic(self, line):
        """Fetch GitHub repository or pull request and add to the chat context.

        Examples:
            %github username/repo
            %github username/repo --system
            %github username/repo --pr 123
            %github username/repo --pr 123 --show
            %github username/repo --clean
            %github username/repo --full-code
            %github username/repo --contributors-months 12
        """
        if not _IPYTHON_AVAILABLE:
            print("❌ IPython is not available. Cannot use %github magic.")
            return

        if not _GITHUB_AVAILABLE:
            print(
                "❌ GitHub package not available. Please install with: pip install PyGithub python-dotenv"
            )
            return

        try:
            args = parse_argstring(self.github_magic, line)
        except Exception as e:
            print(f"❌ Error parsing arguments: {e}")
            return

        # Initialize client if needed
        if self.github_utils is None:
            print("❌ GitHub client not available. Please check your environment variables.")
            return

        try:
            # Fetch repository or pull request
            if not args.repo:
                print("❌ Please provide a GitHub repository identifier (e.g., username/repo)")
                return

            # Clean up repository identifier - remove quotes if present
            cleaned_repo = args.repo.strip()
            if (cleaned_repo.startswith("'") and cleaned_repo.endswith("'")) or (
                cleaned_repo.startswith('"') and cleaned_repo.endswith('"')
            ):
                cleaned_repo = cleaned_repo[1:-1]

            if args.pr:
                # Fetch pull request
                logger.debug(f"Fetching pull request {args.pr} from repository: {cleaned_repo}")
                pr_data = self._fetch_pull_request(cleaned_repo, args.pr)

                if not pr_data:
                    print(
                        f"No pull request found with number: {args.pr} in repository {cleaned_repo}"
                    )
                    return

                formatted_pr = self._format_pr_for_display(pr_data)

                if args.show:
                    print("\n" + formatted_pr)
                else:
                    self._add_to_history(
                        formatted_pr,
                        source_type="pull_request",
                        source_id=f"{cleaned_repo}#{args.pr}",
                        as_system_msg=args.system,
                    )

            else:
                # Fetch repository
                logger.debug(f"Fetching repository: {cleaned_repo}")

                # Process exclusion patterns
                exclusion_patterns = {}

                if args.exclude_dir:
                    # Clean up directory patterns
                    exclusion_patterns["dirs"] = [
                        pattern.strip("\"'") for pattern in args.exclude_dir
                    ]
                    print(f"Excluding directories: {', '.join(exclusion_patterns['dirs'])}")

                if args.exclude_file:
                    # Clean up file patterns
                    exclusion_patterns["files"] = [
                        pattern.strip("\"'") for pattern in args.exclude_file
                    ]
                    print(f"Excluding files: {', '.join(exclusion_patterns['files'])}")

                if args.exclude_ext:
                    # Clean up extensions (remove leading dot if present)
                    exclusion_patterns["extensions"] = [
                        ext.strip("\"'").lstrip(".") for ext in args.exclude_ext
                    ]
                    print(f"Excluding extensions: {', '.join(exclusion_patterns['extensions'])}")

                if args.exclude_regex:
                    # Clean up regex patterns
                    exclusion_patterns["regexes"] = [
                        pattern.strip("\"'") for pattern in args.exclude_regex
                    ]
                    print(f"Excluding by regex: {', '.join(exclusion_patterns['regexes'])}")

                # Only pass exclusion_patterns if any patterns were provided
                exclusion_kwargs = {}
                if exclusion_patterns:
                    exclusion_kwargs["exclusion_patterns"] = exclusion_patterns
                    print(
                        f"Applying {sum(len(patterns) for patterns in exclusion_patterns.values())} exclusion patterns across {len(exclusion_patterns)} categories"
                    )

                repo_data = self._fetch_repository(
                    cleaned_repo, args.full_code, args.contributors_months, **exclusion_kwargs
                )

                if not repo_data:
                    print(f"No repository found with identifier: {cleaned_repo}")
                    return

                # Format for display/history
                formatted_repo = self._format_repository_for_display(repo_data)

                if args.show:
                    print("\n" + formatted_repo)

                    # Show token estimate
                    if "estimated_tokens" in repo_data:
                        tokens = repo_data["estimated_tokens"]
                        print("\n--- Token Estimation ---")
                        print(f"Code: ~{tokens['code']:,} tokens")
                        print(f"Metadata: ~{tokens['metadata']:,} tokens")
                        print(f"Total: ~{tokens['total']:,} tokens")
                else:
                    # Add to chat history and show token estimation
                    success = self._add_to_history(
                        formatted_repo,
                        source_type="repository",
                        source_id=cleaned_repo,
                        as_system_msg=args.system,
                    )

                    if success and "estimated_tokens" in repo_data:
                        tokens = repo_data["estimated_tokens"]
                        print(
                            f"✅ Estimated token size: ~{tokens['total']:,} tokens "
                            + f"({tokens['code']:,} code, {tokens['metadata']:,} metadata)"
                        )

        except Exception as e:
            print(f"❌ Error in GitHub magic: {e}")
            logger.error(f"Error in GitHub magic: {e}", exc_info=True)


# --- Extension Loading ---
def load_ipython_extension(ipython):
    """Register the GitHub magics with the IPython runtime."""
    if not _IPYTHON_AVAILABLE:
        print("IPython is not available. Cannot load GitHub magics.", file=sys.stderr)
        return

    if not _GITHUB_AVAILABLE:
        print(
            "GitHub package not found. Please install with: pip install PyGithub python-dotenv",
            file=sys.stderr,
        )
        print("GitHub magics will not be available.", file=sys.stderr)
        return

    try:
        # Create and register the magic class
        magic_class = GitHubMagics(ipython)
        ipython.register_magics(magic_class)
        print("✅ GitHub Magics loaded. Use %github username/repo to fetch repositories.")
    except Exception as e:
        logger.exception("Failed to register GitHub magics.")
        print(f"❌ Failed to load GitHub Magics: {e}", file=sys.stderr)


def unload_ipython_extension(ipython):
    """Unregister the magics."""
    pass
