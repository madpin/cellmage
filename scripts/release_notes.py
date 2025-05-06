# encoding: utf-8

"""
Prepares markdown release notes for GitHub releases.

This script generates formatted markdown content for GitHub releases by extracting
information from the CHANGELOG.md file and git commit history. It adds emojis
to section headers for better readability and provides a clean changelog format.

Usage:
    TAG=v1.2.3 python scripts/release_notes.py

Requirements:
    - Set TAG environment variable with the version tag (e.g., v1.2.3)
    - Valid CHANGELOG.md file with proper sections
    - Git repository with commit history
"""

import os
import sys
from typing import List, Optional

import packaging.version

# Check for required environment variable
if "TAG" not in os.environ:
    print("ERROR: TAG environment variable is required.")
    print("Usage: TAG=v1.2.3 python scripts/release_notes.py")
    sys.exit(1)

TAG = os.environ["TAG"]

# Validate TAG format
if not TAG.startswith("v"):
    print(f"WARNING: TAG '{TAG}' doesn't start with 'v', which is unusual for version tags.")

# Section headers with emojis for better readability
ADDED_HEADER = "### Added 🎉"
CHANGED_HEADER = "### Changed ⚠️"
FIXED_HEADER = "### Fixed ✅"
REMOVED_HEADER = "### Removed 👋"


def get_change_log_notes() -> str:
    """
    Extract changelog notes for the current release from CHANGELOG.md.

    Returns:
        str: Formatted markdown content with changelog notes

    Raises:
        FileNotFoundError: If CHANGELOG.md doesn't exist
        AssertionError: If no content was found for the specified TAG
    """
    try:
        if not os.path.exists("CHANGELOG.md"):
            raise FileNotFoundError("CHANGELOG.md file not found")

        in_current_section = False
        current_section_notes: List[str] = []

        with open("CHANGELOG.md") as changelog:
            for line in changelog:
                if line.startswith("## "):
                    if line.startswith("## Unreleased"):
                        continue
                    if line.startswith(f"## [{TAG}]"):
                        in_current_section = True
                        continue
                    elif in_current_section:
                        # We've moved past our section to the next version
                        break
                if in_current_section:
                    if line.startswith("### Added"):
                        line = ADDED_HEADER + "\n"
                    elif line.startswith("### Changed"):
                        line = CHANGED_HEADER + "\n"
                    elif line.startswith("### Fixed"):
                        line = FIXED_HEADER + "\n"
                    elif line.startswith("### Removed"):
                        line = REMOVED_HEADER + "\n"
                    current_section_notes.append(line)

        if not current_section_notes:
            raise AssertionError(f"No content found in CHANGELOG.md for version {TAG}")

        return "## What's new\n\n" + "".join(current_section_notes).strip() + "\n"

    except Exception as e:
        print(f"ERROR: Failed to extract changelog notes: {e}")
        sys.exit(1)


def get_commit_history() -> str:
    """
    Get all commits between the current tag and the previous tag.

    Returns:
        str: Formatted markdown content with commit history

    Raises:
        RuntimeError: If git commands fail
    """
    try:
        new_version = packaging.version.parse(TAG)

        # Pull all tags.
        result = os.system("git fetch --tags > /dev/null 2>&1")
        if result != 0:
            raise RuntimeError("Failed to fetch git tags")

        # Get all tags sorted by version, latest first.
        all_tags = os.popen("git tag -l --sort=-version:refname 'v*'").read().split("\n")

        # Out of `all_tags`, find the latest previous version so that we can collect all
        # commits between that version and the new version we're about to publish.
        # Note that we ignore pre-releases unless the new version is also a pre-release.
        last_tag: Optional[str] = None
        for tag in all_tags:
            if not tag.strip():  # could be blank line
                continue
            try:
                version = packaging.version.parse(tag)
                if new_version.pre is None and version.pre is not None:
                    continue
                if version < new_version:
                    last_tag = tag
                    break
            except ValueError:
                # Skip tags that don't parse as valid versions
                continue

        if last_tag is not None:
            print(f"Collecting commits between {last_tag} and {TAG}")
            commits = os.popen(f"git log {last_tag}..{TAG} --oneline --first-parent").read()
        else:
            print("No previous tag found, collecting all commits")
            commits = os.popen("git log --oneline --first-parent").read()

        if not commits.strip():
            print("WARNING: No commits found in the specified range")

        return "## Commits\n\n" + commits

    except Exception as e:
        print(f"ERROR: Failed to get commit history: {e}")
        return "## Commits\n\n*Error retrieving commit history*"


def main():
    """Generate and print release notes combining changelog and commit history."""
    try:
        print(get_change_log_notes())
        print(get_commit_history())
        print("\nRelease notes generated successfully!")
    except Exception as e:
        print(f"ERROR: Failed to generate release notes: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
