# Makefile for cellmage project

# Define phony targets to avoid conflicts with files of the same name
.PHONY: docs run-checks run-fix build clean test-unit release release-patch release-minor release-major prepare-changelog generate-changelog-llm examples test-magic

# Default target when just running 'make'
.DEFAULT_GOAL := help

# Default port for documentation server
PORT ?= 8000

# Define the documentation source and build directories
DOCS_SOURCE_DIR := docs/source/
DOCS_BUILD_DIR := docs/build/
DOCS_PROJECT_DIR := cellmage/ # Used in serve-docs

# Help target to display available commands
help:
	@echo "Available commands:"
	@echo "  make docs              - Build documentation using sphinx-autobuild (default port: 8000)"
	@echo "  make docs PORT=8080    - Build documentation with custom port"
	@echo "  make run-checks        - Run code quality checks and tests"
	@echo "  make run-fix           - Fix code formatting issues and run tests"
	@echo "  make build             - Build the Python package"
	@echo "  make clean             - Clean build artifacts"
	@echo "  make test-unit         - Run only unit tests"
	@echo "  make release           - Create a new release (patch version)"
	@echo "  make release-patch     - Create a new patch version release"
	@echo "  make release-minor     - Create a new minor version release"
	@echo "  make release-major     - Create a new major version release"
	@echo "  make prepare-changelog - Update CHANGELOG.md for a new release"
	@echo "  make generate-changelog-llm - Generate changelog entries with LLM"
	@echo "  make examples          - Run example scripts"
	@echo "  make test-magic        - Test refactored magic commands"

# Build documentation
docs:
    # Ensure a clean state before starting the server
	rm -rf $(DOCS_BUILD_DIR)
	rm -rf $(DOCS_SOURCE_DIR)/api/generated
	@echo "Starting documentation server on port $(PORT)..."
	# sphinx-autobuild watches for changes and rebuilds automatically
	sphinx-autobuild -b html --port $(PORT) --watch $(DOCS_PROJECT_DIR) --watch $(DOCS_SOURCE_DIR) $(DOCS_SOURCE_DIR) $(DOCS_BUILD_DIR)
	# Clean up after server stops (optional, as autobuild might handle this, or you might want to inspect the build)
	# echo "Cleaning up $(DOCS_BUILD_DIR) after server stop..."
	rm -rf $(DOCS_BUILD_DIR)

builddocs:
	@echo "Building documentation..."
	# Attempt to build the HTML documentation
	# -b html: specifies the HTML builder
	# -W: turns warnings into errors, so the build fails on any warning
	# -n: nit-picky mode, warns about all missing references
	sphinx-build -b html -W -n $(DOCS_SOURCE_DIR) $(DOCS_BUILD_DIR); \
	BUILD_EXIT_STATUS=$$?; \
	# Always clean up the build directory
	echo "Cleaning up $(DOCS_BUILD_DIR)..."; \
	rm -rf $(DOCS_BUILD_DIR); \
	rm -rf $(DOCS_SOURCE_DIR)/api/generated; \
	# Check the build status and exit if it failed
	if [ $$BUILD_EXIT_STATUS -ne 0 ]; then \
		echo "Documentation build failed. See output above for errors."; \
		exit 1; \
	else \
		echo "Documentation built successfully and build directory cleaned up."; \
	fi

# Run code quality checks
run-checks:
	isort --check .
	black --config pyproject.toml --check .
	ruff --config pyproject.toml check .
	CUDA_VISIBLE_DEVICES='' pytest -v --color=yes --doctest-modules tests/ cellmage/

# Fix code formatting issues
run-fix:
	isort .
	black --config pyproject.toml .
	ruff --config pyproject.toml check . --fix --unsafe-fixes
	CUDA_VISIBLE_DEVICES='' pytest -v --color=yes --doctest-modules tests/ cellmage/

# Run only unit tests
test-unit:
	CUDA_VISIBLE_DEVICES='' pytest -v --color=yes tests/unit/

# Build the Python package
build:
	rm -rf *.egg-info/
	python -m build

# Clean build artifacts
clean:
	rm -rf *.egg-info/ build/ dist/ docs/build/ **/__pycache__/ .pytest_cache/ .ruff_cache/
	# Delete any rst files in the generated folder if it exists
	find docs/build/generated -name "*.rst" -type f -delete 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Create a new release (defaults to patch version)
release: release-patch

# Create a patch version release
release-patch:
	@echo "Creating a new patch release..."
	@scripts/release.sh patch

# Create a minor version release
release-minor:
	@echo "Creating a new minor release..."
	@scripts/release.sh minor

# Create a major version release
release-major:
	@echo "Creating a new major release..."
	@scripts/release.sh major

# Update CHANGELOG.md for a new release
prepare-changelog:
	@echo "Updating CHANGELOG.md for release..."
	@python scripts/prepare_changelog.py

# Generate changelog entries with LLM
generate-changelog-llm:
	@echo "Generating changelog entries with LLM..."
	@if [ -z "$$API_KEY" ]; then \
		echo "ERROR: API_KEY environment variable is required."; \
		echo "Usage: API_KEY=your_openai_api_key make generate-changelog-llm"; \
		exit 1; \
	fi
	@python scripts/generate_changelog_with_llm.py

# Run example scripts
examples: examples-adapter examples-direct

examples-adapter:
	@echo "Running adapter comparison example..."
	@python scripts/adapter_comparison_example.py

examples-direct:
	@echo "Running direct adapter example..."
	@python scripts/direct_adapter_example.py

# Test refactored magic commands
test-magic:
	@echo "Testing refactored magic commands..."
	@python scripts/test_refactored_magic.py

test-magic-integration:
	@echo "Testing refactored magic commands with integration tests..."
	@python scripts/test_refactored_magic.py --with-integration
