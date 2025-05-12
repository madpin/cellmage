"""
Jira utility for interacting with the Jira API.

This module provides the JiraUtils class for fetching and processing Jira tickets.
"""

import logging
import os
from collections import defaultdict
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Set, Tuple

# Flag to check if Jira is available
_JIRA_AVAILABLE = False

try:
    from jira import JIRA, Issue
    from jira.exceptions import JIRAError
    from jira.resources import Comment as JiraCommentResource  # For type hinting

    _JIRA_AVAILABLE = True
except ImportError:
    # Define placeholder types for type checking when jira package is not available
    if TYPE_CHECKING:
        from jira import JIRA, Issue
        from jira.exceptions import JIRAError
        from jira.resources import Comment as JiraCommentResource
    else:
        JIRA = object
        Issue = object
        JIRAError = Exception
        JiraCommentResource = object

# --- Constants ---
DEFAULT_JIRA_URL: str = "https://jira.atlassian.net"
DEFAULT_EPIC_LINK_FIELD_ID: str = "customfield_10014"  # Default for most Jira instances
DEFAULT_MAX_RESULTS_PER_PAGE: int = 50  # Recommended max page size for Jira API
DEFAULT_MAX_COMMENTS_TO_FETCH: int = 5  # Max recent comments to include full body for
DEFAULT_COMMENT_MAX_LENGTH: int = 500  # Max length of comment bodies included

# Default fields list
DEFAULT_FETCH_FIELDS_LIST: List[str] = [
    "summary",
    "description",
    "status",
    "assignee",
    "reporter",
    "priority",
    "created",
    "updated",
    "duedate",
    "labels",
    "components",
    "issuelinks",
    "comment",  # Epic link field added dynamically in __init__
]

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


class JiraUtils:
    """
    Utility class for interacting with the Jira API.

    Fetches and processes Jira issues, including epics and links,
    preparing data for analysis or LLM input.
    """

    # Use Any type to avoid issues when jira package is not available
    _client: Optional[Any] = None

    def __init__(
        self,
        user_email: Optional[str] = None,
        api_token: Optional[str] = None,
        jira_url: Optional[str] = None,
        epic_link_field_id: Optional[str] = None,
        fetch_fields: Optional[List[str]] = None,
    ):
        """Initialize JiraUtils.

        Args:
            user_email: Email associated with the Jira API token.
                Falls back to JIRA_USER_EMAIL env var.
            api_token: Jira API token (PAT). Falls back to JIRA_API_TOKEN env var.
            jira_url: URL of the Jira instance. Falls back to JIRA_URL env var
                or DEFAULT_JIRA_URL.
            epic_link_field_id: The custom field ID for the Epic link.
                Falls back to JIRA_EPIC_LINK_FIELD_ID env var or
                DEFAULT_EPIC_LINK_FIELD_ID constant.
            fetch_fields: List of fields to fetch for issues. Defaults to a comprehensive list.

        Raises:
            ValueError: If required authentication details are missing.
        """
        if not _JIRA_AVAILABLE:
            raise ImportError(
                "The 'jira' package is required but not installed. "
                "Please install it with 'pip install jira'."
            )

        # Try to load from .env using dotenv if available
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass  # Continue without dotenv

        self.user_email = user_email or os.getenv("JIRA_USER_EMAIL")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN")
        self.jira_url = jira_url or os.getenv("JIRA_URL") or DEFAULT_JIRA_URL

        # Allow empty string env var to override default
        _env_epic_field = os.getenv("JIRA_EPIC_LINK_FIELD_ID")
        self.epic_link_field_id = (
            epic_link_field_id
            if epic_link_field_id is not None
            else _env_epic_field if _env_epic_field is not None else DEFAULT_EPIC_LINK_FIELD_ID
        )

        # Validate essential configuration
        if not self.user_email:
            raise ValueError(
                "Jira user email is required (provide via arg or JIRA_USER_EMAIL env var)."
            )
        if not self.api_token:
            raise ValueError(
                "Jira API token is required (provide via arg or JIRA_API_TOKEN env var)."
            )
        if not self.jira_url:
            raise ValueError("Jira URL is required (provide via arg or JIRA_URL env var).")

        # Configure fields to fetch
        _default_fields: List[str] = DEFAULT_FETCH_FIELDS_LIST[:]  # Create a copy
        if self.epic_link_field_id not in _default_fields:
            _default_fields.append(self.epic_link_field_id)

        # Use provided fetch_fields or the computed default list
        effective_fetch_fields = fetch_fields if fetch_fields is not None else _default_fields

        # Ensure base fields required for processing are always included
        _required_base_fields = {"key", "summary", "status", "issuelinks", "comment"}
        self.fetch_fields: List[str] = list(set(effective_fetch_fields) | _required_base_fields)
        # Store as a sorted tuple for consistent use in cached functions
        self.fetch_fields_tuple: Tuple[str, ...] = tuple(sorted(self.fetch_fields))

        logger.info(f"JiraUtils initialized for URL: {self.jira_url} with user: {self.user_email}")
        # Client is initialized lazily via the 'client' property

    @property
    def client(self) -> JIRA:
        """Lazy-initialized, authenticated jira.JIRA client."""
        if self._client is None:
            logger.info(f"Connecting to Jira at {self.jira_url}...")
            try:
                self._client = JIRA(
                    server=self.jira_url,
                    basic_auth=(self.user_email, self.api_token),
                )
                logger.info(f"Successfully connected to Jira as {self.user_email}.")
            except JIRAError as e:
                logger.error(
                    f"Jira connection failed: Status {e.status_code} - {e.text}", exc_info=True
                )
                raise RuntimeError(f"Failed to connect to Jira: {e.text}") from e
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred during Jira connection: {e}", exc_info=True
                )
                raise RuntimeError(f"Unexpected error connecting to Jira: {str(e)}") from e
        return self._client

    def _fetch_paginated_issues(
        self, jql: str, max_results: Optional[int] = None, fields: Optional[Sequence[str]] = None
    ) -> List[Issue]:
        """Internal helper to fetch issues using pagination."""
        issues_batch: List[Issue] = []
        start_at = 0
        total_fetched = 0
        # Use instance default fields tuple if None provided
        fields_to_fetch_seq = fields if fields is not None else self.fetch_fields_tuple
        # Convert sequence to comma-separated string for the API call
        fields_str = ",".join(fields_to_fetch_seq)
        # Ensure key is always present
        if "key" not in fields_to_fetch_seq:
            fields_str = "key," + fields_str

        effective_page_size = DEFAULT_MAX_RESULTS_PER_PAGE

        while True:
            num_to_fetch = effective_page_size
            if max_results is not None:
                remaining_needed = max_results - total_fetched
                if remaining_needed <= 0:
                    break
                num_to_fetch = min(effective_page_size, remaining_needed)

            logger.debug(
                f"Fetching issues with JQL: '{jql}', startAt: {start_at}, maxResults: {num_to_fetch}"
            )
            try:
                current_batch = self.client.search_issues(
                    jql,
                    startAt=start_at,
                    maxResults=num_to_fetch,
                    fields=fields_str,
                    json_result=False,
                )
            except JIRAError as e:
                logger.error(
                    f"JQL query failed: '{jql}'. Status: {e.status_code} - {e.text}", exc_info=True
                )
                raise
            except Exception as e:
                logger.error(f"Unexpected error fetching issues: {e}", exc_info=True)
                raise RuntimeError(f"Unexpected error fetching issues: {str(e)}") from e

            batch_size = len(current_batch)
            issues_batch.extend(current_batch)
            total_fetched += batch_size
            logger.debug(
                f"Fetched {batch_size} issues in this batch. Total fetched: {total_fetched}"
            )

            if batch_size < num_to_fetch or (
                max_results is not None and total_fetched >= max_results
            ):
                break
            start_at += batch_size

        logger.info(
            f"Finished fetching for JQL '{jql}'. Total issues retrieved: {len(issues_batch)}"
        )
        return issues_batch

    def fetch_tickets_raw(
        self, jql: str, max_results: Optional[int] = None, fields: Optional[Sequence[str]] = None
    ) -> List[Issue]:
        """Fetch raw jira.Issue objects based on JQL."""
        logger.info(
            f"Fetching raw tickets for JQL: {jql}"
            + (f" (max: {max_results})" if max_results else "")
        )
        fields_to_fetch = fields if fields is not None else self.fetch_fields_tuple
        return self._fetch_paginated_issues(jql, max_results, fields_to_fetch)

    @hashable_lru_cache(maxsize=256)
    def fetch_single_ticket_raw(
        self, ticket_key: str, fields: Optional[Sequence[str]] = None
    ) -> Issue:
        """Fetch a single raw jira.Issue object by key (cached)."""
        logger.debug(f"Fetching single raw ticket: {ticket_key}")
        fields_to_fetch_seq = fields if fields is not None else self.fetch_fields_tuple
        fields_str = ",".join(fields_to_fetch_seq)

        if "key" not in fields_to_fetch_seq:
            fields_str = "key," + fields_str

        normalized_key = ticket_key.upper()

        try:
            issue = self.client.issue(normalized_key, fields=fields_str)
            logger.debug(f"Successfully fetched raw ticket: {normalized_key}")
            return issue
        except JIRAError as e:
            logger.warning(
                f"Failed to fetch ticket {normalized_key}: Status {e.status_code} - {e.text}",
                exc_info=False,
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching ticket {normalized_key}: {e}", exc_info=True)
            raise RuntimeError(
                f"Unexpected error fetching ticket {normalized_key}: {str(e)}"
            ) from e

    def _get_field_value(self, issue: Issue, field_name: str, default: Any = None) -> Any:
        """Safely retrieve a field value from an issue."""
        try:
            value = getattr(issue.fields, field_name, default)
            return value if value is not None else default
        except AttributeError:
            logger.debug(
                f"AttributeError accessing field '{field_name}' on issue {issue.key}. Returning default."
            )
            return default

    def _get_display_name(self, user_object: Optional[Any], default: str = "Unknown User") -> str:
        """Safely extract the displayName from a Jira user object."""
        if user_object:
            if hasattr(user_object, "displayName") and user_object.displayName:
                return user_object.displayName
            if hasattr(user_object, "name") and user_object.name:
                return user_object.name
        return default

    def _get_epic_info(self, issue: Issue) -> Tuple[Optional[str], Optional[str]]:
        """Extract the Epic key and summary from an issue, if linked."""
        epic_key: Optional[str] = self._get_field_value(issue, self.epic_link_field_id)

        if not epic_key:
            return None, None

        epic_summary: Optional[str] = None
        try:
            epic_fields_tuple = ("summary",)
            epic_issue = self.fetch_single_ticket_raw(epic_key, fields=epic_fields_tuple)
            epic_summary = self._get_field_value(epic_issue, "summary", default=f"Epic {epic_key}")
            logger.debug(f"Found Epic link for {issue.key}: {epic_key} ('{epic_summary}')")
        except JIRAError:
            logger.warning(
                f"Could not fetch details for Epic {epic_key} linked from {issue.key}.",
                exc_info=False,
            )
            epic_summary = f"Epic {epic_key} (details unavailable)"
        except Exception as e:
            logger.error(f"Unexpected error fetching epic {epic_key} details: {e}", exc_info=True)
            epic_summary = f"Epic {epic_key} (error fetching details)"

        return epic_key, epic_summary

    def _get_issue_links(self, issue: Issue) -> List[Dict[str, Any]]:
        """Extract and process all issue links from an issue."""
        processed_links: List[Dict[str, Any]] = []
        raw_links = self._get_field_value(issue, "issuelinks", default=[])

        if not raw_links:
            return processed_links

        logger.debug(f"Processing {len(raw_links)} links for issue {issue.key}")
        linked_issue_fields_tuple = ("summary", "status")

        for link in raw_links:
            link_data: Dict[str, Any] = {}
            try:
                link_type_obj = getattr(link, "type", None)
                if not link_type_obj:
                    logger.warning(f"Link object in issue {issue.key} missing 'type'. Skipping.")
                    continue

                linked_issue_obj = None
                direction = None

                # Determine direction and link type name
                if hasattr(link, "outwardIssue"):
                    direction = "outward"
                    linked_issue_obj = link.outwardIssue
                    link_data["type"] = getattr(link_type_obj, "outward", "Unknown Outward Type")
                elif hasattr(link, "inwardIssue"):
                    direction = "inward"
                    linked_issue_obj = link.inwardIssue
                    link_data["type"] = getattr(link_type_obj, "inward", "Unknown Inward Type")
                else:
                    logger.warning(
                        f"Link object in issue {issue.key} has no inward or outward issue. Skipping."
                    )
                    continue

                if not linked_issue_obj or not hasattr(linked_issue_obj, "key"):
                    logger.warning(
                        f"Link object in issue {issue.key} missing linked issue key. Skipping."
                    )
                    continue

                linked_key = linked_issue_obj.key
                link_data["direction"] = direction
                link_data["key"] = linked_key

                # Fetch summary and status of the linked issue (cached)
                linked_summary: Optional[str] = f"Issue {linked_key}"
                linked_status: Optional[str] = "Unknown"
                try:
                    linked_issue_details = self.fetch_single_ticket_raw(
                        linked_key, fields=linked_issue_fields_tuple
                    )
                    linked_summary = self._get_field_value(
                        linked_issue_details, "summary", default=linked_summary
                    )
                    status_obj = self._get_field_value(linked_issue_details, "status")
                    linked_status = (
                        status_obj.name
                        if status_obj and hasattr(status_obj, "name")
                        else linked_status
                    )
                except JIRAError:
                    logger.warning(
                        f"Could not fetch details for linked issue {linked_key}.", exc_info=False
                    )
                    linked_summary += " (details unavailable)"
                except Exception as e:
                    logger.error(
                        f"Unexpected error fetching linked issue {linked_key} details: {e}",
                        exc_info=True,
                    )
                    linked_summary += " (error fetching details)"

                link_data["summary"] = linked_summary
                link_data["status"] = linked_status

                processed_links.append(link_data)
                logger.debug(f"Processed link from {issue.key}: {link_data}")

            except AttributeError as e:
                logger.warning(
                    f"AttributeError processing link in issue {issue.key}: {e}", exc_info=False
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error processing a link in issue {issue.key}: {e}", exc_info=True
                )

        return processed_links

    def _get_comments_summary(
        self,
        issue: Issue,
        max_comments_to_fetch: int = DEFAULT_MAX_COMMENTS_TO_FETCH,
        max_length: int = DEFAULT_COMMENT_MAX_LENGTH,
    ) -> Dict[str, Any]:
        """Extract comments summary and a limited list of recent comments."""
        comments_field = self._get_field_value(issue, "comment", default=None)
        all_comments: List[JiraCommentResource] = []
        if comments_field and hasattr(comments_field, "comments"):
            all_comments = comments_field.comments
        else:
            logger.debug(f"No comments found or comment field malformed for issue {issue.key}")
            return {
                "total_count": 0,
                "fetched_count": 0,
                "unique_commenters": 0,
                "commenter_stats": [],
                "fetched_comments": [],
            }

        total_count = len(all_comments)
        logger.debug(f"Processing {total_count} total comments for issue {issue.key}")

        commenter_data: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"count": 0, "total_chars": 0}
        )
        authors: Set[str] = set()

        for comment in all_comments:
            author_name = self._get_display_name(
                getattr(comment, "author", None), default="Unknown User"
            )
            authors.add(author_name)
            body_length = len(getattr(comment, "body", ""))
            commenter_data[author_name]["count"] += 1
            commenter_data[author_name]["total_chars"] += body_length

        unique_commenters = len(authors)

        commenter_stats = sorted(
            [
                {
                    "author": author,
                    "comment_count": stats["count"],
                    "total_chars": stats["total_chars"],
                }
                for author, stats in commenter_data.items()
            ],
            key=lambda x: x["comment_count"],
            reverse=True,
        )

        fetched_comments: List[Dict[str, Any]] = []
        comments_to_process = (
            all_comments[-max_comments_to_fetch:] if max_comments_to_fetch > 0 else []
        )
        fetched_count = len(comments_to_process)

        for comment in comments_to_process:
            author_name = self._get_display_name(
                getattr(comment, "author", None), default="Unknown User"
            )
            body = getattr(comment, "body", "")
            truncated_body = (
                (body[:max_length] + "..." if len(body) > max_length else body)
                if max_length >= 0
                else body
            )
            created_iso = None
            try:
                created_dt = getattr(comment, "created", None)
                if created_dt and hasattr(created_dt, "isoformat"):
                    created_iso = created_dt.isoformat()
                elif isinstance(created_dt, str):
                    created_iso = created_dt
            except Exception as e:
                logger.error(f"Error formatting created date for comment: {e}", exc_info=False)

            fetched_comments.append(
                {"author": author_name, "body": truncated_body, "created": created_iso}
            )

        return {
            "total_count": total_count,
            "fetched_count": fetched_count,
            "unique_commenters": unique_commenters,
            "commenter_stats": commenter_stats,
            "fetched_comments": fetched_comments,
        }

    def process_issue_details(self, issue: Issue) -> Dict[str, Any]:
        """Transform a raw jira.Issue object into a structured dictionary."""
        logger.debug(f"Processing details for issue: {issue.key}")

        status_obj = self._get_field_value(issue, "status")
        assignee_obj = self._get_field_value(issue, "assignee")
        reporter_obj = self._get_field_value(issue, "reporter")
        priority_obj = self._get_field_value(issue, "priority")
        components_list = self._get_field_value(issue, "components", default=[])
        labels_list = self._get_field_value(issue, "labels", default=[])

        epic_key, epic_summary = self._get_epic_info(issue)
        links = self._get_issue_links(issue)
        comments_summary = self._get_comments_summary(issue)

        def format_iso_date(field_name: str) -> Optional[str]:
            date_val = self._get_field_value(issue, field_name)
            if not date_val:
                return None
            if hasattr(date_val, "isoformat"):
                return date_val.isoformat()
            # Try to handle string dates (e.g., YYYY-MM-DD from some fields)
            if isinstance(date_val, str):
                return date_val
            logger.warning(f"Could not format date field '{field_name}' for issue {issue.key}")
            return str(date_val)  # Fallback to string representation

        details = {
            "key": issue.key,
            "url": issue.permalink(),
            "summary": self._get_field_value(issue, "summary", default=""),
            "description": self._get_field_value(issue, "description"),
            "status": status_obj.name if status_obj and hasattr(status_obj, "name") else "Unknown",
            "assignee": self._get_display_name(assignee_obj, default="Unassigned"),
            "reporter": self._get_display_name(reporter_obj),
            "priority": (
                priority_obj.name if priority_obj and hasattr(priority_obj, "name") else None
            ),
            "created_date": format_iso_date("created"),
            "updated_date": format_iso_date("updated"),
            "due_date": format_iso_date("duedate"),
            "labels": labels_list,  # Keep as list for JSON
            "components": [
                comp.name for comp in components_list if hasattr(comp, "name")
            ],  # Keep as list for JSON
            "epic_key": epic_key,
            "epic_summary": epic_summary,
            "links": links,  # Keep detailed structure for JSON
            "comments_summary": comments_summary,  # Keep detailed structure for JSON
        }
        logger.debug(f"Finished processing details for issue: {issue.key}")
        return details

    def fetch_processed_tickets(
        self, jql: str, max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch issues based on JQL and return them as processed dictionaries."""
        logger.info(
            f"Fetching and processing tickets for JQL: {jql}"
            + (f" (max: {max_results})" if max_results else "")
        )
        raw_issues = self.fetch_tickets_raw(
            jql, max_results=max_results, fields=self.fetch_fields_tuple
        )

        processed_tickets: List[Dict[str, Any]] = []
        for issue in raw_issues:
            try:
                processed_details = self.process_issue_details(issue)
                processed_tickets.append(processed_details)
            except Exception as e:
                logger.error(f"Failed to process issue {issue.key}: {e}", exc_info=True)
                processed_tickets.append(
                    {
                        "key": issue.key,
                        "url": issue.permalink(),
                        "summary": "Error processing issue",
                        "error": f"Failed to process issue details: {str(e)}",
                    }
                )

        logger.info(
            f"Successfully fetched and processed {len(processed_tickets)} tickets for JQL: {jql}"
        )
        return processed_tickets

    def fetch_processed_ticket(self, ticket_key: str) -> Dict[str, Any]:
        """Fetch a single issue by key and return it as a processed dictionary."""
        logger.info(f"Fetching and processing single ticket: {ticket_key}")
        try:
            raw_issue = self.fetch_single_ticket_raw(ticket_key, fields=self.fetch_fields_tuple)
            processed_ticket = self.process_issue_details(raw_issue)
            logger.info(f"Successfully fetched and processed ticket: {ticket_key}")
            return processed_ticket
        except (JIRAError, RuntimeError) as e:
            logger.error(f"Failed to fetch or process ticket {ticket_key}: {e}", exc_info=True)
            raise

    def format_tickets_for_llm(
        self,
        tickets: List[Dict[str, Any]],
        include_description: bool = False,
        description_length: int = 300,
        include_comments: bool = True,
    ) -> str:
        """Format processed tickets into a concise Markdown string for LLM input."""
        output_lines: List[str] = []
        output_lines.append(f"# Jira Ticket Summary ({len(tickets)} issues)\n")

        for ticket in tickets:
            if "error" in ticket:  # Handle tickets that failed processing
                output_lines.append(
                    f"## [{ticket.get('key', 'N/A')}] - Error processing this ticket\n"
                )
                output_lines.append(f"*   Error details: {ticket['error']}")
                output_lines.append("\n---\n")
                continue

            output_lines.append(
                f"## [{ticket.get('key', 'N/A')}] {ticket.get('summary', 'No Summary')}\n"
            )
            output_lines.append(f"*   **Status:** {ticket.get('status', 'Unknown')}")
            output_lines.append(f"*   **Assignee:** {ticket.get('assignee', 'Unassigned')}")
            if ticket.get("priority"):
                output_lines.append(f"*   **Priority:** {ticket['priority']}")
            if ticket.get("due_date"):
                output_lines.append(f"*   **Due:** {ticket['due_date'][:10]}")
            if ticket.get("epic_key"):
                output_lines.append(
                    f"*   **Epic:** [{ticket['epic_key']}] {ticket.get('epic_summary', '')}"
                )
            if ticket.get("components"):
                output_lines.append(f"*   **Components:** {', '.join(ticket['components'])}")
            if ticket.get("labels"):
                output_lines.append(f"*   **Labels:** {', '.join(ticket['labels'])}")

            if include_description and ticket.get("description"):
                desc = ticket["description"]
                truncated_desc = (
                    desc[:description_length] + "..." if len(desc) > description_length else desc
                )
                formatted_desc = truncated_desc.replace("\r\n", "\n").replace("\n", "\n    ")
                output_lines.append(
                    f"\n*   **Description:**\n    ```\n    {formatted_desc}\n    ```"
                )

            if ticket.get("links"):
                links = ticket["links"]
                link_summary = defaultdict(list)
                for link in links:
                    link_text = f"[{link.get('key', 'N/A')}] ({link.get('status', '?')})"
                    link_summary[link.get("type", "Link").capitalize()].append(link_text)
                output_lines.append("\n*   **Links:**")
                for link_type, linked_items in link_summary.items():
                    output_lines.append(f"    *   {link_type}: {', '.join(linked_items)}")

            if include_comments and ticket.get("comments_summary"):
                c_summary = ticket["comments_summary"]
                output_lines.append(
                    f"\n*   **Comments:** {c_summary.get('total_count', 0)} total by {c_summary.get('unique_commenters', 0)} people."
                )
                top_commenters = [
                    f"{stat['author']} ({stat['comment_count']})"
                    for stat in c_summary.get("commenter_stats", [])[:3]
                ]
                if top_commenters:
                    output_lines.append(f"    *   Top commenters: {', '.join(top_commenters)}")
                recent_comments = c_summary.get("fetched_comments", [])
                if recent_comments:
                    output_lines.append("    *   Recent comments:")
                    for comment in recent_comments:
                        author = comment.get("author", "Unknown")
                        date_str = comment.get("created", "")[:10] if comment.get("created") else ""
                        body_snippet = comment.get("body", "").replace("\n", " ").replace("\r", "")
                        output_lines.append(f'        *   {date_str} ({author}): "{body_snippet}"')

            output_lines.append("\n---\n")

        return "\n".join(output_lines)

    def close(self) -> None:
        """Close the Jira client connection resources."""
        if self._client:
            logger.info("Closing Jira client connection.")
            try:
                self._client.close()
                self._client = None
                logger.info("Jira client connection closed.")
            except Exception as e:
                logger.warning(f"Error encountered while closing Jira client: {e}", exc_info=False)
                self._client = None
        else:
            logger.debug("Jira client already closed or was never initialized.")

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point. Ensures the client connection is closed."""
        self.close()
