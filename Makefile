# Makefile for cellmage project

# Define phony targets to avoid conflicts with files of the same name
.PHONY: docs run-checks run-fix build clean test-unit

# Default target when just running 'make'
.DEFAULT_GOAL := help

# Help target to display available commands
help:
	@echo "Available commands:"
	@echo "  make docs       - Build documentation using sphinx-autobuild"
	@echo "  make run-checks - Run code quality checks and tests"
	@echo "  make run-fix    - Fix code formatting issues and run tests"
	@echo "  make build      - Build the Python package"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make test-unit  - Run only unit tests"

# Build documentation
docs:
	rm -rf docs/build/
	sphinx-autobuild -b html --watch cellmage/ docs/source/ docs/build/

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
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
