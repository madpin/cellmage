# Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to run code quality checks before each commit. Pre-commit helps ensure that code meets the project's quality standards before it's committed and pushed to the repository.

## What Gets Checked

The following checks are run automatically before each commit:

- **Code Formatting**
  - `black`: Formats Python code according to project standards
  - `isort`: Sorts imports alphabetically and separates them into sections

- **Linting**
  - `ruff`: Lints Python code for errors, style issues, and potential bugs

- **Type Checking**
  - `pyright`: Performs static type checking on Python code

- **Other Checks**
  - Trailing whitespace removal
  - End-of-file fixing (ensures files end with a newline)
  - YAML, TOML, and JSON validation
  - Checking for large files
  - Detecting debug statements (like `import pdb; pdb.set_trace()`)

## Installation

Pre-commit is included in the development dependencies of this project. To set it up:

1. Install the development dependencies:

```bash
pip install -e ".[dev]"
```

2. Install the pre-commit hooks:

```bash
pre-commit install
```

This will install the pre-commit hooks into your local git repository, so they run automatically before each commit.

## Manual Usage

You can run the pre-commit hooks manually without making a commit:

- Run on all files in the repository:
```bash
pre-commit run --all-files
```

- Run on staged files only:
```bash
pre-commit run
```

- Run a specific hook:
```bash
pre-commit run black
```

## Skipping Hooks

In rare cases, you may need to bypass the pre-commit hooks (not recommended):

```bash
git commit -m "Your message" --no-verify
```

However, this should be avoided as the CI pipeline runs the same checks and will still catch issues.

## Updating Hooks

To update the hooks to their latest versions:

```bash
pre-commit autoupdate
```

Then commit the changes to `.pre-commit-config.yaml`.

## Configuration

The pre-commit configuration is stored in `.pre-commit-config.yaml` at the root of the repository. This configuration matches the checks run in our CI pipeline.

Additional settings for specific tools are in `pyproject.toml`. For example:
- `[tool.black]` for Black formatting configuration
- `[tool.isort]` for import sorting configuration
- `[tool.ruff]` for Ruff linting configuration
