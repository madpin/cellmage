"""
IPython magic command for Jira integration with CellMage.

This module provides magic commands for fetching Jira tickets and using them as context in LLM prompts.
"""

import logging
import sys
from typing import Any, Dict, List, Optional

# IPython imports with fallback handling
try:
    from IPython.core.magic import Magics, line_magic, magics_class
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

    class DummyMagics:
        pass  # Dummy base class

    Magics = DummyMagics  # Type alias for compatibility

# Create a global logger
logger = logging.getLogger(__name__)

# Attempt to import Jira utils
try:
    # from functools import lru_cache

    from jira import JIRA

    _JIRA_AVAILABLE = True
except ImportError:
    _JIRA_AVAILABLE = False


@magics_class
class JiraMagics(Magics):
    """IPython magic commands for fetching and using Jira tickets as context."""

    def __init__(self, shell):
        if not _IPYTHON_AVAILABLE:
            logger.warning("IPython not found. Jira magics are disabled.")
            return

        super().__init__(shell)
        self.jira_client = None
        self.jira_utils = None
        self._init_jira_client()

    def _init_jira_client(self) -> None:
        """Initialize the Jira client if possible."""
        if not _JIRA_AVAILABLE:
            logger.warning("Jira package not available. Please install the jira package.")
            return

        try:
            # Import required modules for Jira utils
            import os

            from dotenv import load_dotenv

            # Load environment variables
            load_dotenv()

            # Check for required environment variables
            jira_url = os.getenv("JIRA_URL")
            jira_user = os.getenv("JIRA_USER_EMAIL")
            jira_token = os.getenv("JIRA_API_TOKEN")

            if not jira_url or not jira_user or not jira_token:
                logger.warning(
                    "Missing Jira environment variables. Please set JIRA_URL, JIRA_USER_EMAIL, and JIRA_API_TOKEN."
                )
                return

            # Try to initialize JiraUtils
            try:
                from ..utils.jira_utils import JiraUtils

                self.jira_utils = JiraUtils(
                    user_email=jira_user, api_token=jira_token, jira_url=jira_url
                )
                logger.info(f"JiraUtils initialized successfully for {jira_url}")
            except Exception as e:
                logger.error(f"Failed to initialize JiraUtils: {e}")
                # Fallback to basic JIRA client if JiraUtils fails
                try:
                    self.jira_client = JIRA(server=jira_url, basic_auth=(jira_user, jira_token))
                    logger.info(f"Basic JIRA client initialized successfully for {jira_url}")
                except Exception as e:
                    logger.error(f"Failed to initialize basic JIRA client: {e}")
        except Exception as e:
            logger.error(f"Error during Jira client initialization: {e}")

    def _get_client(self):
        """Get the JiraUtils instance or JIRA client, initializing if needed."""
        if self.jira_utils is not None:
            return self.jira_utils

        if self.jira_client is not None:
            return self.jira_client

        self._init_jira_client()

        if self.jira_utils is not None:
            return self.jira_utils

        if self.jira_client is not None:
            return self.jira_client

        return None

    def _fetch_ticket(self, ticket_key: str) -> Optional[Dict[str, Any]]:
        """Fetch a Jira ticket by key and return processed data."""
        client = self._get_client()

        if client is None:
            print("❌ Jira client not available")
            return None

        try:
            # If we're using JiraUtils
            if hasattr(client, "fetch_processed_ticket"):
                return client.fetch_processed_ticket(ticket_key)

            # If we're using basic JIRA client
            issue = client.issue(ticket_key)

            # Create a simplified dictionary with basic issue information
            return {
                "key": issue.key,
                "summary": issue.fields.summary,
                "description": issue.fields.description,
                "status": (
                    issue.fields.status.name
                    if hasattr(issue.fields.status, "name")
                    else str(issue.fields.status)
                ),
                "assignee": (
                    issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
                ),
                "reporter": (
                    issue.fields.reporter.displayName if issue.fields.reporter else "Unknown"
                ),
                "created_date": (
                    str(issue.fields.created) if hasattr(issue.fields, "created") else None
                ),
                "updated_date": (
                    str(issue.fields.updated) if hasattr(issue.fields, "updated") else None
                ),
            }
        except Exception as e:
            print(f"❌ Error fetching Jira ticket {ticket_key}: {e}")
            logger.error(f"Error fetching Jira ticket {ticket_key}: {e}")
            return None

    def _fetch_tickets_by_jql(
        self, jql: str, max_results: Optional[int] = 10
    ) -> List[Dict[str, Any]]:
        """Fetch Jira tickets by JQL query and return processed data."""
        client = self._get_client()

        if client is None:
            print("❌ Jira client not available")
            return []

        try:
            # If we're using JiraUtils
            if hasattr(client, "fetch_processed_tickets"):
                return client.fetch_processed_tickets(jql, max_results=max_results)

            # If we're using basic JIRA client
            issues = client.search_issues(jql, maxResults=max_results)

            results = []
            for issue in issues:
                results.append(
                    {
                        "key": issue.key,
                        "summary": issue.fields.summary,
                        "description": issue.fields.description,
                        "status": (
                            issue.fields.status.name
                            if hasattr(issue.fields.status, "name")
                            else str(issue.fields.status)
                        ),
                        "assignee": (
                            issue.fields.assignee.displayName
                            if issue.fields.assignee
                            else "Unassigned"
                        ),
                        "reporter": (
                            issue.fields.reporter.displayName
                            if issue.fields.reporter
                            else "Unknown"
                        ),
                        "created_date": (
                            str(issue.fields.created) if hasattr(issue.fields, "created") else None
                        ),
                        "updated_date": (
                            str(issue.fields.updated) if hasattr(issue.fields, "updated") else None
                        ),
                    }
                )

            return results
        except Exception as e:
            print(f"❌ Error fetching Jira tickets with JQL '{jql}': {e}")
            logger.error(f"Error fetching Jira tickets with JQL '{jql}': {e}")
            return []

    def _format_ticket_for_display(self, ticket: Dict[str, Any]) -> str:
        """Format a ticket for terminal display."""
        if not ticket:
            return "No ticket data available"

        # If using JiraUtils with full formatting
        if (
            hasattr(self, "jira_utils")
            and self.jira_utils is not None
            and hasattr(self.jira_utils, "format_tickets_for_llm")
        ):
            return self.jira_utils.format_tickets_for_llm(
                [ticket], include_description=True, include_comments=True
            )

        # Basic formatting
        output = []
        output.append(f"# [{ticket.get('key', 'N/A')}] {ticket.get('summary', 'No Summary')}")
        output.append(f"**Status:** {ticket.get('status', 'Unknown')}")
        output.append(f"**Assignee:** {ticket.get('assignee', 'Unassigned')}")
        output.append(f"**Reporter:** {ticket.get('reporter', 'Unknown')}")

        if ticket.get("created_date"):
            output.append(f"**Created:** {ticket.get('created_date')}")

        if ticket.get("updated_date"):
            output.append(f"**Updated:** {ticket.get('updated_date')}")

        if ticket.get("description"):
            desc = ticket.get("description")
            output.append("\n**Description:**")
            output.append(f"```\n{desc}\n```")

        return "\n".join(output)

    def _get_chat_manager(self):
        """Get the ChatManager instance."""
        try:
            from ..integrations.ipython_magic import get_chat_manager

            return get_chat_manager()
        except Exception as e:
            logger.error(f"Error getting ChatManager: {e}")
            print(f"❌ Error getting ChatManager: {e}")
            return None

    def _add_ticket_to_history(
        self, ticket_data: Dict[str, Any], as_system_msg: bool = False
    ) -> bool:
        """Add the ticket data to the chat history as a user or system message."""
        import uuid

        from ..models import Message

        manager = self._get_chat_manager()
        if not manager:
            print("❌ ChatManager not available")
            return False

        try:
            # Format ticket for LLM
            if (
                hasattr(self, "jira_utils")
                and self.jira_utils is not None
                and hasattr(self.jira_utils, "format_tickets_for_llm")
            ):
                content = self.jira_utils.format_tickets_for_llm(
                    [ticket_data], include_description=True, include_comments=True
                )
            else:
                # Basic formatting
                content = self._format_ticket_for_display(ticket_data)

            # Create message
            role = "system" if as_system_msg else "user"
            message = Message(
                role=role,
                content=content,
                id=str(uuid.uuid4()),
                metadata={"source": "jira", "jira_key": ticket_data.get("key", "")},
            )

            # Add to history
            manager.history_manager.add_message(message)
            print(
                f"✅ Added Jira ticket {ticket_data.get('key', '')} as {role} message to chat history"
            )
            return True

        except Exception as e:
            logger.error(f"Error adding ticket to history: {e}")
            print(f"❌ Error adding ticket to history: {e}")
            return False

    @magic_arguments()
    @argument("ticket", type=str, nargs="?", help="Jira ticket key (e.g., PROJECT-123)")
    @argument("--jql", type=str, help="JQL query instead of a specific ticket key")
    @argument("--max", type=int, default=5, help="Maximum number of tickets to retrieve with JQL")
    @argument(
        "--system",
        action="store_true",
        help="Add tickets as system messages instead of user messages",
    )
    @argument("--show", action="store_true", help="Only show tickets without adding to history")
    @line_magic("jira")
    def jira_magic(self, line):
        """Fetch Jira ticket(s) and add them to the chat context.

        Examples:
            %jira PROJECT-123
            %jira --jql "project = PROJECT AND assignee = currentUser()"
            %jira PROJECT-123 --system
            %jira --jql "project = PROJECT ORDER BY updated DESC" --max 3
        """
        if not _IPYTHON_AVAILABLE:
            print("❌ IPython is not available. Cannot use %jira magic.")
            return

        if not _JIRA_AVAILABLE:
            print(
                "❌ Jira package not available. Please install with: pip install jira python-dotenv"
            )
            return

        try:
            args = parse_argstring(self.jira_magic, line)
        except Exception as e:
            print(f"❌ Error parsing arguments: {e}")
            return

        # Initialize client if needed
        if self._get_client() is None:
            print("❌ Jira client not available. Please check your environment variables.")
            return

        try:
            # Fetch by JQL or specific ticket key
            if args.jql:
                # Clean up JQL query - remove outer quotes if present
                cleaned_jql = args.jql.strip()
                if (cleaned_jql.startswith("'") and cleaned_jql.endswith("'")) or (
                    cleaned_jql.startswith('"') and cleaned_jql.endswith('"')
                ):
                    cleaned_jql = cleaned_jql[1:-1]

                print(f"Fetching tickets with JQL: {cleaned_jql}")
                tickets = self._fetch_tickets_by_jql(cleaned_jql, max_results=args.max)

                if not tickets:
                    print(f"No tickets found with JQL: {cleaned_jql}")
                    return

                print(f"Found {len(tickets)} tickets.")

                # Display or add to history
                for ticket in tickets:
                    if args.show:
                        print("\n" + self._format_ticket_for_display(ticket))
                    else:
                        self._add_ticket_to_history(ticket, as_system_msg=args.system)

            elif args.ticket:
                # Clean up ticket key - remove quotes if present
                cleaned_ticket = args.ticket.strip()
                if (cleaned_ticket.startswith("'") and cleaned_ticket.endswith("'")) or (
                    cleaned_ticket.startswith('"') and cleaned_ticket.endswith('"')
                ):
                    cleaned_ticket = cleaned_ticket[1:-1]

                print(f"Fetching ticket: {cleaned_ticket}")
                ticket = self._fetch_ticket(cleaned_ticket)

                if not ticket:
                    print(f"No ticket found with key: {cleaned_ticket}")
                    return

                if args.show:
                    print("\n" + self._format_ticket_for_display(ticket))
                else:
                    self._add_ticket_to_history(ticket, as_system_msg=args.system)

            else:
                print("❌ Please provide either a ticket key or a JQL query.")

        except Exception as e:
            print(f"❌ Error in Jira magic: {e}")
            logger.error(f"Error in Jira magic: {e}", exc_info=True)


# --- Extension Loading ---
def load_ipython_extension(ipython):
    """Register the Jira magics with the IPython runtime."""
    if not _IPYTHON_AVAILABLE:
        print("IPython is not available. Cannot load Jira magics.", file=sys.stderr)
        return

    if not _JIRA_AVAILABLE:
        print(
            "Jira package not found. Please install with: pip install jira python-dotenv",
            file=sys.stderr,
        )
        print("Jira magics will not be available.", file=sys.stderr)
        return

    try:
        magic_class = JiraMagics(ipython)
        ipython.register_magics(magic_class)
        print("✅ Jira Magics loaded. Use %jira <ticket-key> to fetch tickets.")
    except Exception as e:
        logger.exception("Failed to register Jira magics.")
        print(f"❌ Failed to load Jira Magics: {e}", file=sys.stderr)


def unload_ipython_extension(ipython):
    """Unregister the magics."""
    pass
