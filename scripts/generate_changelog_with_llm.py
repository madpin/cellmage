#!/usr/bin/env python
"""
Generate changelog entries using LLM based on git commit history.

This script analyzes commit messages between the previous and current version tags,
and uses an LLM to generate structured changelog entries in the Keep a Changelog format.

Usage:
    python scripts/generate_changelog_with_llm.py [--since-tag <tag>] [--quiet]

Environment variables:
    CELLMAGE_API_KEY/OPENAI_API_KEY: Your LLM API key (required)
    CELLMAGE_API_BASE/OPENAI_API_BASE: API endpoint URL (default: OpenAI's endpoint)
    MODEL: LLM model to use (default: gpt-4.1-mini)
    MODEL_LIST: Comma-separated list of models to try in order (overrides MODEL)

Requirements:
    - Git repository with commit history
    - OpenAI API key (or compatible API key for other providers)
"""

import argparse
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import openai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODELS = ["gpt-4.1-mini", "gemini-2.5-flash", "Qwen3-235B-A22B"]
SECTION_HEADERS = ["Added", "Changed", "Fixed", "Removed", "Security", "Deprecated"]


def get_current_version():
    """Get the current version from cellmage.version."""
    try:
        version_output = subprocess.check_output(
            ["python", "-c", "from cellmage.version import VERSION; print(VERSION)"],
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        ).strip()
        return f"v{version_output}"
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get version: {e.output.strip()}")
        sys.exit(1)


def get_previous_tag(current_tag):
    """Get the previous release tag."""
    try:
        # Get all tags sorted by version, newest first
        tags = subprocess.check_output(
            ["git", "tag", "-l", "--sort=-v:refname"],
            universal_newlines=True,
        ).splitlines()

        # Find the previous tag
        found_current = False
        for tag in tags:
            if tag.strip() == current_tag:
                found_current = True
                continue
            if found_current and tag.strip():
                return tag.strip()

        # If no previous tag found, return earliest commit
        return subprocess.check_output(
            ["git", "rev-list", "--max-parents=0", "HEAD"],
            universal_newlines=True,
        ).strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e}")
        return None


def get_commit_messages(since_tag, current_tag):
    """Get commit messages between two tags. If current_tag does not exist, use HEAD."""
    try:
        # Check if current_tag exists as a git ref
        tag_exists = False
        if current_tag:
            try:
                subprocess.check_output(
                    ["git", "rev-parse", "--verify", current_tag], stderr=subprocess.STDOUT
                )
                tag_exists = True
            except subprocess.CalledProcessError:
                tag_exists = False

        end_ref = current_tag if tag_exists else "HEAD"
        if since_tag:
            range_spec = f"{since_tag}..{end_ref}"
        else:
            range_spec = end_ref

        commits = subprocess.check_output(
            ["git", "log", range_spec, "--pretty=format:%s (%h)"],
            universal_newlines=True,
        )
        return commits
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get commit messages: {e}")
        return ""


def generate_changelog_with_llm(
    commits: str,
    version: str,
    api_key: str,
    api_base: Optional[str] = None,
    models: List[str] = None,
) -> str:
    """Use LLM to generate changelog entries based on commit messages."""
    if not commits.strip():
        logger.warning("No commits found to analyze")
        return ""

    # Configure OpenAI client with API base if provided
    client_kwargs = {"api_key": api_key}
    if api_base:
        client_kwargs["base_url"] = api_base

    client = openai.OpenAI(**client_kwargs)

    # Use default model if none provided
    if not models:
        models = DEFAULT_MODELS

    # Ensure models is a flat list of strings
    if models and isinstance(models[0], list):
        models = models[0]

    # Log the API configuration (without exposing the key)
    logger.info(f"Using models in order: {', '.join(models)}")
    if api_base:
        logger.info(f"Using custom API base: {api_base}")
    else:
        logger.info("Using default OpenAI API endpoint")

    # Prepare the prompt
    prompt = f"""
As an AI expert in software development, analyze the following git commit messages
and organize them into a structured changelog for version {version}.

The changelog should follow the Keep a Changelog format with these sections:
- Added (for new features)
- Changed (for changes in existing functionality)
- Fixed (for bug fixes)
- Removed (for removed features)
- Security (for security fixes)
- Deprecated (for soon-to-be removed features)

Only include sections that have relevant entries. Combine related commits into single,
well-written entries. Use proper grammar and complete sentences.

Here are the commit messages:

{commits}

Respond only with the changelog content, without any additional commentary,
following this format:
### Added
- Entry 1
- Entry 2

### Changed
- Entry 1
- Entry 2

### Fixed
- Entry 1
- Entry 2

etc.
"""

    for model_name in models:
        try:
            logger.info(f"Attempting to generate changelog using model: {model_name}")
            # Make API call
            response = client.chat.completions.create(
                model=model_name.strip(),
                messages=[
                    {
                        "role": "system",
                        "content": "You are a software development assistant that creates well-organized changelog entries.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=1000,
            )

            # Extract changelog content
            changelog_content = response.choices[0].message.content.strip()
            logger.info(f"Successfully generated changelog for {version} using model {model_name}")
            return changelog_content

        except Exception as e:
            logger.error(f"Error generating changelog with model {model_name}: {e}")
            if model_name == models[-1]:
                logger.error("All models failed to generate changelog")
                raise
            else:
                logger.info("Trying next model in fallback list")

    return ""


def update_changelog_file(changelog_content, version):
    """Update CHANGELOG.md with the generated content."""
    try:
        changelog_path = Path("CHANGELOG.md")
        if not changelog_path.exists():
            logger.error("CHANGELOG.md not found")
            return False

        with changelog_path.open("r") as f:
            lines = f.readlines()

        # Find the insertion point (after the Unreleased section)
        insert_index = -1
        version_already_exists = False

        for i, line in enumerate(lines):
            if line.startswith("## Unreleased"):
                insert_index = i + 1
            elif line.startswith(f"## [v{version}]") or line.startswith(f"## [{version}]"):
                version_already_exists = True
                break

        if version_already_exists:
            logger.info(f"Version {version} already exists in CHANGELOG.md")
            return False

        if insert_index < 0:
            logger.error("Unreleased section not found in CHANGELOG.md")
            return False

        # Prepare new content
        current_date = datetime.now().strftime("%Y-%m-%d")
        version_header = f"\n## [{version}](https://github.com/madpin/cellmage/releases/tag/{version}) - {current_date}\n\n"

        # Insert the new version section
        new_content = (
            lines[:insert_index]
            + [version_header]
            + [changelog_content + "\n\n"]
            + lines[insert_index:]
        )

        # Write updated content back to file
        with changelog_path.open("w") as f:
            f.writelines(new_content)

        logger.info(f"Successfully updated CHANGELOG.md with content for {version}")
        return True

    except Exception as e:
        logger.error(f"Error updating CHANGELOG.md: {e}")
        return False


def main():
    """Generate changelog entries and update CHANGELOG.md."""
    parser = argparse.ArgumentParser(description="Generate changelog entries using LLM")
    parser.add_argument("--since-tag", help="Starting tag for collecting commits")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    parser.add_argument("--models", help="Comma-separated list of models to try in order")
    args = parser.parse_args()

    if args.quiet:
        logger.setLevel(logging.WARNING)

    # Get API key from environment variables
    api_key = (
        os.environ.get("CELLMAGE_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("API_KEY")
    )

    if not api_key:
        logger.error(
            "API key not found. Please set one of these environment variables: "
            "CELLMAGE_API_KEY, OPENAI_API_KEY, or API_KEY"
        )
        sys.exit(1)

    # Get API base from environment variables (optional)
    api_base = os.environ.get("CELLMAGE_API_BASE") or os.environ.get("OPENAI_API_BASE")

    # Get models from environment variable MODEL or use default
    model_from_env = os.environ.get("MODEL")
    default_model = DEFAULT_MODELS[0] if DEFAULT_MODELS else "gpt-4.1-mini"
    model = model_from_env if model_from_env else default_model

    # Get model list from command line or environment
    if args.models:
        model_list = args.models.split(",")
        logger.info(f"Using models from command line: {', '.join(model_list)}")
    else:
        model_list_env = os.environ.get("MODEL_LIST")
        if model_list_env:
            model_list = model_list_env.split(",")
            logger.info(f"Using models from MODEL_LIST: {', '.join(model_list)}")
        else:
            # If no model list specified, use the single model or default models
            model_list = [model] if isinstance(model, str) else DEFAULT_MODELS
            if isinstance(model, str):
                logger.info(f"Using single model: {model}")
            else:
                logger.info(f"Using default models: {', '.join(DEFAULT_MODELS)}")

    # Get version
    current_version = get_current_version()
    logger.info(f"Current version: {current_version}")

    # Get previous tag if not specified
    since_tag = args.since_tag
    if not since_tag:
        since_tag = get_previous_tag(current_version)
        logger.info(f"Using previous tag: {since_tag}")

    # Get commit messages - pass current_version tag instead of just using HEAD
    commits = get_commit_messages(since_tag, current_version)

    # Generate changelog with LLM
    changelog_content = generate_changelog_with_llm(
        commits, current_version, api_key, api_base, model_list
    )

    if changelog_content:
        # Update CHANGELOG.md
        if update_changelog_file(changelog_content, current_version):
            print(f"Changelog for {current_version} generated successfully!")
        else:
            logger.error("Failed to update CHANGELOG.md")
            sys.exit(1)
    else:
        logger.error("No changelog content generated")
        sys.exit(1)


if __name__ == "__main__":
    main()
