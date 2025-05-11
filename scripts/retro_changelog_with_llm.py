#!/usr/bin/env python
"""
Retroactively generate changelog entries for all historical versions using LLM.

- Iterates through all version tags in git history (chronological order)
- For each version, determines the commit range (from previous tag to current tag)
- Uses LLM to generate a changelog section for that version
- Updates CHANGELOG.md, skipping versions that already exist

Usage:
    python scripts/retro_changelog_with_llm.py [--dry-run] [--start-tag vX.Y.Z] [--end-tag vX.Y.Z]

Environment variables:
    CELLMAGE_API_KEY/OPENAI_API_KEY: Your LLM API key (required)
    CELLMAGE_API_BASE/OPENAI_API_BASE: API endpoint URL (optional)
    MODEL: LLM model to use (default: gpt-4.1-mini)
    MODEL_LIST: Comma-separated list of models to try in order (overrides MODEL)

Requirements:
    - Git repository with version tags (vX.Y.Z)
    - OpenAI API key (or compatible API key for other providers)
    - openai python package
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import openai

CHANGELOG_PATH = Path("CHANGELOG.md")
DEFAULT_MODELS = ["gpt-4.1-mini", "gemini-2.5-flash", "Qwen3-235B-A22B"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("retro_changelog_with_llm")


def get_all_version_tags(start_tag=None, end_tag=None) -> List[str]:
    tags = subprocess.check_output(
        ["git", "tag", "-l", "v*", "--sort=version:refname"], universal_newlines=True
    ).splitlines()
    tags = [t.strip() for t in tags if t.strip()]
    if start_tag:
        if start_tag in tags:
            tags = tags[tags.index(start_tag) :]
        else:
            logger.warning(f"Start tag {start_tag} not found, using all tags.")
    if end_tag:
        if end_tag in tags:
            tags = tags[: tags.index(end_tag) + 1]
        else:
            logger.warning(f"End tag {end_tag} not found, using all tags.")
    return tags


def get_commit_messages(since_tag: Optional[str], to_tag: str) -> str:
    if since_tag:
        range_spec = f"{since_tag}..{to_tag}"
    else:
        range_spec = to_tag
    try:
        commits = subprocess.check_output(
            ["git", "log", range_spec, "--pretty=format:%s (%h)"], universal_newlines=True
        )
        return commits
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get commit messages: {e}")
        return ""


def parse_existing_versions_in_changelog() -> List[str]:
    if not CHANGELOG_PATH.exists():
        return []
    versions = []
    for line in CHANGELOG_PATH.read_text().splitlines():
        if line.startswith("## [v"):
            tag = line.split("[")[1].split("]")[0]
            versions.append(tag)
    return versions


def generate_changelog_with_llm(
    commits: str, version: str, api_key: str, api_base: Optional[str], models: List[str]
) -> str:
    if not commits.strip():
        logger.warning(f"No commits found for {version}")
        return ""
    client_kwargs = {"api_key": api_key}
    if api_base:
        client_kwargs["base_url"] = api_base
    client = openai.OpenAI(**client_kwargs)
    prompt = f"""
As an AI expert in software development, analyze the following git commit messages\nand organize them into a structured changelog for version {version}.\n\nThe changelog should follow the Keep a Changelog format with these sections:\n- Added (for new features)\n- Changed (for changes in existing functionality)\n- Fixed (for bug fixes)\n- Removed (for removed features)\n- Security (for security fixes)\n- Deprecated (for soon-to-be removed features)\n\nOnly include sections that have relevant entries. Combine related commits into single,\nwell-written entries. Use proper grammar and complete sentences.\n\nHere are the commit messages:\n\n{commits}\n\nRespond only with the changelog content, without any additional commentary,\nfollowing this format:\n### Added\n- Entry 1\n\n### Changed\n- Entry 1\n\n### Fixed\n- Entry 1\n\netc.\n"""
    for model_name in models:
        try:
            logger.info(f"Generating changelog for {version} using model: {model_name}")
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
            changelog_content = response.choices[0].message.content.strip()
            logger.info(f"Changelog for {version} generated successfully.")
            return changelog_content
        except Exception as e:
            logger.error(f"Model {model_name} failed: {e}")
            if model_name == models[-1]:
                logger.error("All models failed for this version.")
                return ""
            logger.info("Trying next model...")
    return ""


def insert_version_section(
    changelog_lines: List[str], version: str, content: str, date: Optional[str]
) -> List[str]:
    # Insert after '## Unreleased' if present, else at top
    header = f"## [{version}](https://github.com/madpin/cellmage/releases/tag/{version})"
    if date:
        header += f" - {date}"
    header += "\n"
    section = ["\n", header, content.strip() + "\n"]
    # Find '## Unreleased' and insert after, else at top
    for i, line in enumerate(changelog_lines):
        if line.startswith("## Unreleased"):
            return changelog_lines[: i + 1] + section + changelog_lines[i + 1 :]
    return section + changelog_lines


def remove_version_section(changelog_lines: List[str], version: str) -> List[str]:
    """Remove any existing section for the given version from the changelog lines."""
    header = f"## [{version}]"
    header_with_link = f"## [{version}](https://github.com/madpin/cellmage/releases/tag/{version})"
    start_idx = None
    end_idx = None
    for i, line in enumerate(changelog_lines):
        if line.startswith(header) or line.startswith(header_with_link):
            start_idx = i
            # Find where the next version section starts or end of file
            for j in range(i + 1, len(changelog_lines)):
                if changelog_lines[j].startswith("## [") and j != i:
                    end_idx = j
                    break
            if end_idx is None:
                end_idx = len(changelog_lines)
            break
    if start_idx is not None:
        return changelog_lines[:start_idx] + changelog_lines[end_idx:]
    return changelog_lines


def main():
    parser = argparse.ArgumentParser(
        description="Retroactively generate changelog entries for all versions using LLM."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write to CHANGELOG.md, just print what would be added.",
    )
    parser.add_argument("--start-tag", type=str, help="Start from this tag (inclusive)")
    parser.add_argument("--end-tag", type=str, help="End at this tag (inclusive)")
    args = parser.parse_args()

    api_key = (
        os.environ.get("CELLMAGE_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("API_KEY")
    )
    if not api_key:
        logger.error("No API key found. Set CELLMAGE_API_KEY, OPENAI_API_KEY, or API_KEY.")
        sys.exit(1)
    api_base = os.environ.get("CELLMAGE_API_BASE") or os.environ.get("OPENAI_API_BASE")
    models = os.environ.get("MODEL_LIST")
    if models:
        models = [m.strip() for m in models.split(",") if m.strip()]
    else:
        models = (
            [os.environ.get("MODEL", DEFAULT_MODELS[0])]
            if os.environ.get("MODEL")
            else DEFAULT_MODELS
        )

    tags = get_all_version_tags(args.start_tag, args.end_tag)
    if not tags:
        logger.error("No version tags found.")
        sys.exit(1)
    logger.info(f"Found {len(tags)} version tags.")

    existing_versions = parse_existing_versions_in_changelog()
    logger.info(f"CHANGELOG.md contains {len(existing_versions)} versions.")

    changelog_lines = (
        CHANGELOG_PATH.read_text().splitlines(keepends=True)
        if CHANGELOG_PATH.exists()
        else ["# Changelog\n", "\n", "## Unreleased\n", "\n"]
    )

    for i, tag in enumerate(tags):
        since_tag = tags[i - 1] if i > 0 else None
        commits = get_commit_messages(since_tag, tag)
        if not commits.strip():
            logger.info(f"No commits for {tag}, skipping.")
            continue
        # Try to get tag date
        try:
            date = subprocess.check_output(
                ["git", "log", "-1", "--format=%ad", "--date=short", tag], universal_newlines=True
            ).strip()
        except Exception:
            date = None
        changelog_content = generate_changelog_with_llm(commits, tag, api_key, api_base, models)
        if not changelog_content:
            logger.warning(f"No changelog generated for {tag}")
            continue
        logger.info(f"Adding changelog for {tag}")
        # Remove any existing section for this version
        changelog_lines = remove_version_section(changelog_lines, tag)
        changelog_lines = insert_version_section(changelog_lines, tag, changelog_content, date)
        if args.dry_run:
            print(f"\n--- Changelog for {tag} ---\n{changelog_content}\n")
    if not args.dry_run:
        with CHANGELOG_PATH.open("w") as f:
            f.writelines(changelog_lines)
        logger.info("CHANGELOG.md updated.")
    else:
        logger.info("Dry run complete. No changes written.")


if __name__ == "__main__":
    main()
