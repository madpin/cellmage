# GitHub Release Process

## Steps

1. Update the version in `cellmage/version.py`.

2. Run the release script:

    ```bash
    # Default: increment patch version (0.5.5 -> 0.5.6)
    ./scripts/release.sh
    # or
    make release

    # Alternatively, you can specify the version increment type:

    # For patch releases (0.5.5 -> 0.5.6)
    ./scripts/release.sh patch
    # or
    make release-patch

    # For minor releases (0.5.5 -> 0.6.0)
    ./scripts/release.sh minor
    # or
    make release-minor

    # For major releases (0.5.5 -> 1.0.0)
    ./scripts/release.sh major
    # or
    make release-major
    ```

    This will check if the current version has already been released. If it has, it will suggest the next version based on the selected increment type. If you confirm, it will automatically update the version.py file.

    The script will then commit the changes to the CHANGELOG and `version.py` files and create a new tag in git which will trigger a workflow on GitHub Actions that handles the rest.

## Fixing a failed release

If for some reason the GitHub Actions release workflow failed with an error that needs to be fixed, you'll have to delete both the tag and corresponding release from GitHub. After you've pushed a fix, delete the tag from your local clone with

```bash
git tag -l | xargs git tag -d && git fetch -t
```

Then repeat the steps above.
