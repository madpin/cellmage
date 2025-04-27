"""
Argument definitions for IPython magic commands.

This module provides reusable argument groups for IPython magic commands,
making it easier to maintain consistent interfaces across commands.
"""

from IPython.core.magic_arguments import argument, argument_group

# --- Common Argument Groups ---


def persona_args():
    """Arguments for persona management."""
    return [
        argument("-p", "--persona", type=str, help="Select and activate a persona by name."),
        argument("--show-persona", action="store_true", help="Show the currently active persona details."),
        argument("--list-personas", action="store_true", help="List available persona names."),
    ]


def override_args():
    """Arguments for parameter overrides."""
    return [
        argument(
            "--set-override",
            nargs=2,
            metavar=("KEY", "VALUE"),
            help="Set a temporary LLM param override (e.g., --set-override temperature 0.5).",
        ),
        argument("--remove-override", type=str, metavar="KEY", help="Remove a specific override key."),
        argument(
            "--clear-overrides",
            action="store_true",
            help="Clear all temporary LLM param overrides.",
        ),
        argument("--show-overrides", action="store_true", help="Show the currently active overrides."),
    ]


def history_args():
    """Arguments for history management."""
    return [
        argument(
            "--clear-history",
            action="store_true",
            help="Clear the current chat history (keeps system prompt).",
        ),
        argument("--show-history", action="store_true", help="Display the current message history."),
    ]


def persistence_args():
    """Arguments for session persistence."""
    return [
        argument(
            "--save",
            type=str,
            nargs="?",
            const=True,
            metavar="FILENAME",
            help="Save session. If no name, uses current session ID. '.md' added automatically.",
        ),
        argument(
            "--load",
            type=str,
            metavar="SESSION_ID",
            help="Load session from specified identifier (filename without .md).",
        ),
        argument("--list-sessions", action="store_true", help="List saved session identifiers."),
        argument(
            "--auto-save",
            action="store_true",
            help="Enable automatic saving of conversations to the conversations directory.",
        ),
        argument(
            "--no-auto-save",
            action="store_true",
            help="Disable automatic saving of conversations.",
        ),
    ]


def snippet_args():
    """Arguments for snippet management."""
    return [
        argument("--list-snippets", action="store_true", help="List available snippet names."),
        argument(
            "--snippet",
            type=str,
            action="append",
            help="Add user snippet content before sending prompt. Can be used multiple times.",
        ),
        argument(
            "--sys-snippet",
            type=str,
            action="append",
            help="Add system snippet content before sending prompt. Can be used multiple times.",
        ),
    ]


def config_args():
    """Arguments for general configuration."""
    return [
        argument(
            "--status",
            action="store_true",
            help="Show current status (persona, overrides, history length).",
        ),
        argument("--model", type=str, help="Set the default model for the LLM client."),
    ]


def llm_execution_args():
    """Arguments for LLM execution in cell magic."""
    return [
        argument("-p", "--persona", type=str, help="Use specific persona for THIS call only."),
        argument("-m", "--model", type=str, help="Use specific model for THIS call only."),
        argument("-t", "--temperature", type=float, help="Set temperature for THIS call."),
        argument("--max-tokens", type=int, dest="max_tokens", help="Set max_tokens for THIS call."),
        argument(
            "--no-history",
            action="store_false",
            dest="add_to_history",
            help="Do not add this exchange to history.",
        ),
        argument(
            "--no-stream",
            action="store_false",
            dest="stream",
            help="Do not stream output (wait for full response).",
        ),
        argument(
            "--no-rollback",
            action="store_false",
            dest="auto_rollback",
            help="Disable auto-rollback check for this cell run.",
        ),
        argument(
            "--param",
            nargs=2,
            metavar=("KEY", "VALUE"),
            action="append",
            help="Set any other LLM param ad-hoc (e.g., --param top_p 0.9).",
        ),
    ]


# --- Helper Functions ---


def add_argument_group(func, arg_group_func):
    """
    Add a group of arguments to a magic function.

    Args:
        func: The magic function to decorate
        arg_group_func: Function that returns a list of arguments

    Returns:
        The decorated function with arguments added
    """
    for arg in arg_group_func():
        func = arg(func)
    return func
