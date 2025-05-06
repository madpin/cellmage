#!/bin/bash

# Release script for cellmage
#
# This script automates the process of creating a new release:
# 1. Gets the current version from cellmage.version
# 2. Updates the CHANGELOG.md file
# 3. Commits the changes
# 4. Creates and pushes a new git tag
#
# Usage:
#   ./scripts/release.sh [patch|minor|major]
#   or
#   make release
#   make release-minor
#   make release-major

set -e

# Function to handle errors
handle_error() {
    echo "ERROR: Release process failed at line $1."
    exit 1
}

# Set up error handling
trap 'handle_error $LINENO' ERR

# Default version increment type
VERSION_TYPE=${1:-"patch"}

echo "=== Cellmage Release Process ==="
echo "Version increment type: $VERSION_TYPE"

# Check if git is clean
if [[ -n $(git status -s) ]]; then
    echo "ERROR: Working directory is not clean. Please commit or stash changes before releasing."
    exit 1
fi

# Get the current version from Python code
if ! TAG=$(python -c 'from cellmage.version import VERSION; print("v" + VERSION)'); then
    echo "ERROR: Failed to get version from cellmage.version."
    exit 1
fi

# Check if current tag already exists
if git tag -l "$TAG" | grep -q "$TAG"; then
    echo "WARNING: Tag $TAG already exists!"

    # Extract major, minor, patch from current version
    CURRENT_VERSION=${TAG#v}
    IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

    # Calculate next version based on VERSION_TYPE
    if [[ "$VERSION_TYPE" == "major" ]]; then
        NEXT_MAJOR=$((MAJOR + 1))
        SUGGESTED_VERSION="v$NEXT_MAJOR.0.0"
        VERSION_FILE_UPDATES="-e s/_MAJOR = \"$MAJOR\"/_MAJOR = \"$NEXT_MAJOR\"/ -e s/_MINOR = \"$MINOR\"/_MINOR = \"0\"/ -e s/_PATCH = \"$PATCH\"/_PATCH = \"0\"/"
    elif [[ "$VERSION_TYPE" == "minor" ]]; then
        NEXT_MINOR=$((MINOR + 1))
        SUGGESTED_VERSION="v$MAJOR.$NEXT_MINOR.0"
        VERSION_FILE_UPDATES="-e s/_MINOR = \"$MINOR\"/_MINOR = \"$NEXT_MINOR\"/ -e s/_PATCH = \"$PATCH\"/_PATCH = \"0\"/"
    else
        # Default to patch
        NEXT_PATCH=$((PATCH + 1))
        SUGGESTED_VERSION="v$MAJOR.$MINOR.$NEXT_PATCH"
        VERSION_FILE_UPDATES="-e s/_PATCH = \"$PATCH\"/_PATCH = \"$NEXT_PATCH\"/"
    fi

    echo "Would you like to create a new $VERSION_TYPE version: $SUGGESTED_VERSION? [y/N]"
    read -p "> " create_new_version

    if [[ $create_new_version == "y" || $create_new_version == "Y" || $create_new_version == "yes" || $create_new_version == "Yes" ]]; then
        # Update version.py with new version
        echo "Updating version.py with new version $SUGGESTED_VERSION..."
        sed -i '' $VERSION_FILE_UPDATES cellmage/version.py

        # Get the updated version
        if ! TAG=$(python -c 'from cellmage.version import VERSION; print("v" + VERSION)'); then
            echo "ERROR: Failed to get updated version from cellmage.version."
            exit 1
        fi
        echo "Version updated to: $TAG"
    else
        echo "Release cancelled. Please update version.py manually before proceeding."
        exit 1
    fi
fi

echo "Current version: $TAG"
read -p "Creating new release for $TAG. Do you want to continue? [Y/n] " prompt

if [[ $prompt == "y" || $prompt == "Y" || $prompt == "yes" || $prompt == "Yes" || $prompt == "" ]]; then
    echo "Preparing changelog..."
    if ! python scripts/prepare_changelog.py; then
        echo "ERROR: Failed to update changelog."
        exit 1
    fi

    echo "Committing changes..."
    git add CHANGELOG.md cellmage/version.py
    if ! git commit -m "Bump version to $TAG for release"; then
        echo "No changes to commit or commit failed."
        # Continue anyway since there might be no changes
    fi

    echo "Pushing changes..."
    if ! git push; then
        echo "WARNING: Failed to push changes. Please push manually."
    fi

    echo "Creating new git tag $TAG"
    if ! git tag "$TAG" -m "$TAG"; then
        echo "ERROR: Failed to create tag $TAG"
        exit 1
    fi

    echo "Pushing tag..."
    if ! git push --tags; then
        echo "ERROR: Failed to push tags."
        echo "Please push tags manually with: git push --tags"
        exit 1
    fi

    echo "=== Release $TAG completed successfully! ==="
    echo "Next steps:"
    echo "1. Go to GitHub and create a new release from this tag"
    echo "2. Use the release_notes.py script to generate release notes: TAG=$TAG python scripts/release_notes.py"
else
    echo "Release cancelled by user."
    exit 1
fi
