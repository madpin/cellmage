#!/bin/bash

# Release script for cellmage
#
# This script automates the process of creating a new release:
# 1. Gets the current version from cellmage.version
# 2. Bumps the version (patch/minor/major)
# 3. Updates the CHANGELOG.md file
# 4. Commits the changes
# 5. Creates and pushes a new git tag
#
# Usage:
#   ./scripts/release.sh [patch|minor|major]
#   or
#   make release
#   make release-minor
#   make release-major

set -e

handle_error() {
    echo "ERROR: Release process failed at line $1."
    exit 1
}
trap 'handle_error $LINENO' ERR

VERSION_TYPE=${1:-"patch"}

echo "=== Cellmage Release Process ==="
echo "Version increment type: $VERSION_TYPE"

if [[ -z "${CELLMAGE_API_KEY}" && -z "${OPENAI_API_KEY}" && -z "${API_KEY}" ]]; then
    echo "WARNING: No API key found. LLM-powered changelog generation will be skipped."
    echo "To enable LLM changelog generation, set CELLMAGE_API_KEY, OPENAI_API_KEY, or API_KEY environment variable."
    USE_LLM=false
else
    USE_LLM=true
fi

if [[ -n $(git status -s) ]]; then
    echo "ERROR: Working directory is not clean. Please commit or stash changes before releasing."
    exit 1
fi

# Get the current version and previous tag
CURRENT_VERSION=$(python -c 'from cellmage.version import VERSION; print(VERSION)')
CURRENT_TAG="v$CURRENT_VERSION"
PREV_TAG=$(git tag --sort=-creatordate | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | grep -v "$CURRENT_TAG" | head -n 1)

IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Calculate next version
if [[ "$VERSION_TYPE" == "major" ]]; then
    NEXT_MAJOR=$((MAJOR + 1))
    NEXT_VERSION="$NEXT_MAJOR.0.0"
    sed -i '' -e "s/_MAJOR = \"$MAJOR\"/_MAJOR = \"$NEXT_MAJOR\"/g" cellmage/version.py
    sed -i '' -e "s/_MINOR = \"$MINOR\"/_MINOR = \"0\"/g" cellmage/version.py
    sed -i '' -e "s/_PATCH = \"$PATCH\"/_PATCH = \"0\"/g" cellmage/version.py
elif [[ "$VERSION_TYPE" == "minor" ]]; then
    NEXT_MINOR=$((MINOR + 1))
    NEXT_VERSION="$MAJOR.$NEXT_MINOR.0"
    sed -i '' -e "s/_MINOR = \"$MINOR\"/_MINOR = \"$NEXT_MINOR\"/g" cellmage/version.py
    sed -i '' -e "s/_PATCH = \"$PATCH\"/_PATCH = \"0\"/g" cellmage/version.py
else
    NEXT_PATCH=$((PATCH + 1))
    NEXT_VERSION="$MAJOR.$MINOR.$NEXT_PATCH"
    sed -i '' -e "s/_PATCH = \"$PATCH\"/_PATCH = \"$NEXT_PATCH\"/g" cellmage/version.py
fi
NEW_TAG="v$NEXT_VERSION"

# Bump version in version.py before changelog generation
# Get the updated version after bump
UPDATED_VERSION=$(python -c 'from cellmage.version import VERSION; print(VERSION)')
UPDATED_TAG="v$UPDATED_VERSION"

echo "Current version: $CURRENT_TAG"
echo "Previous tag: $PREV_TAG"
echo "Next version: $NEW_TAG"
read -p "Creating new release for $NEW_TAG. Do you want to continue? [Y/n] " prompt

if [[ $prompt == "y" || $prompt == "Y" || $prompt == "yes" || $prompt == "Yes" || $prompt == "" ]]; then
    # Generate changelog with LLM if API key is provided
    if [[ "$USE_LLM" == true ]]; then
        echo "Generating changelog with LLM..."
        # Only pass --since-tag, do not pass the new tag as the end of the range
        if ! python scripts/generate_changelog_with_llm.py --since-tag "$PREV_TAG"; then
            echo "WARNING: Failed to generate changelog with LLM. Falling back to basic changelog format."
        fi
    fi

    # Run prepare_changelog.py to ensure version header is in CHANGELOG.md
    echo "Preparing changelog structure..."
    if ! python scripts/prepare_changelog.py; then
        echo "ERROR: Failed to update changelog."
        exit 1
    fi

    echo "Committing changes..."
    git add CHANGELOG.md cellmage/version.py
    if ! git commit -m "Bump version to $NEW_TAG for release"; then
        echo "No changes to commit or commit failed."
    fi

    echo "Pushing changes..."
    if ! git push; then
        echo "WARNING: Failed to push changes. Please push manually."
    fi

    echo "Creating new git tag $NEW_TAG"
    if ! git tag "$NEW_TAG" -m "$NEW_TAG"; then
        echo "ERROR: Failed to create tag $NEW_TAG"
        exit 1
    fi

    echo "Pushing tag..."
    if ! git push --tags; then
        echo "ERROR: Failed to push tags."
        echo "Please push tags manually with: git push --tags"
        exit 1
    fi

    echo "=== Release $NEW_TAG completed successfully! ==="
    echo "Next steps:"
    echo "1. Go to GitHub and create a new release from this tag"
    echo "2. Use the release_notes.py script to generate release notes: TAG=$NEW_TAG python scripts/release_notes.py"
else
    echo "Release cancelled by user."
    exit 1
fi
