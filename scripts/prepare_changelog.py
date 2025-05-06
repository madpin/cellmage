#!/usr/bin/env python
"""
Prepare changelog for a new release.

This script updates the CHANGELOG.md file when releasing a new version.
It adds a new section with the current version from cellmage.version
and the current date.

Usage:
    python prepare_changelog.py

Requirements:
    - CHANGELOG.md file with an "## Unreleased" section
    - cellmage.version module with VERSION defined
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

from cellmage.version import VERSION

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Update CHANGELOG.md with a new section for the current version."""
    try:
        changelog_path = Path("CHANGELOG.md")

        # Check if changelog exists
        if not changelog_path.exists():
            raise FileNotFoundError(f"Changelog file not found at {changelog_path}")

        logger.info(f"Updating changelog for version v{VERSION}")

        with changelog_path.open() as f:
            lines = f.readlines()

        insert_index: int = -1
        for i in range(len(lines)):
            line = lines[i]
            if line.startswith("## Unreleased"):
                insert_index = i + 1
                logger.info("Found Unreleased section")
            elif line.startswith(f"## [v{VERSION}]"):
                logger.info("CHANGELOG already up-to-date")
                return
            elif line.startswith("## [v"):
                break

        if insert_index < 0:
            logger.error("Couldn't find 'Unreleased' section in CHANGELOG.md")
            raise RuntimeError("Couldn't find 'Unreleased' section")

        # Add new version section
        current_date = datetime.now().strftime("%Y-%m-%d")
        lines.insert(insert_index, "\n")
        lines.insert(
            insert_index + 1,
            f"## [v{VERSION}](https://github.com/madpin/cellmage/releases/tag/v{VERSION}) - "
            f"{current_date}\n",
        )

        logger.info(f"Added version v{VERSION} dated {current_date}")

        # Write updated content back to file
        try:
            with changelog_path.open("w") as f:
                f.writelines(lines)
            logger.info("Successfully updated CHANGELOG.md")
        except IOError as e:
            logger.error(f"Failed to write to CHANGELOG.md: {e}")
            raise

    except Exception as e:
        logger.error(f"Error updating changelog: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
