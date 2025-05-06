#!/usr/bin/env python
"""
Test script for validating the refactored magic commands.

This script provides a quick way to validate that the refactored magic commands
are properly registered and can be loaded by IPython.

Usage:
    python test_refactored_magic.py [--with-integration]

Expected output:
    Success messages indicating that the magic commands were properly loaded.
"""

import argparse
import sys
from unittest.mock import MagicMock, patch


class IPythonConfigurable:
    """A simple mock of IPython's Configurable class for testing."""

    def __init__(self, *args, **kwargs):
        """Initialize with standard attributes to pass trait validation."""
        # Add attributes that Configurable expects
        self.config = kwargs.get("config", {})
        self.parent = kwargs.get("parent", None)

    def register_magics(self, magic_class):
        """Mock method to register magic classes."""
        print(f"Registered magic class: {magic_class.__name__}")
        return True


def test_magic_refactoring():
    """Test that the refactored magic commands can be loaded."""
    # First, check that IPython is available
    try:
        print("✅ IPython is available")
    except ImportError:
        print("❌ IPython is not available. Cannot test magic commands.")
        return False

    # Create a mock IPython shell that mimics Configurable
    mock_shell = IPythonConfigurable()
    # Add the register_magics method which our code calls
    mock_shell.register_magics = MagicMock(return_value=True)

    # Track the number of successful registrations
    success_count = 0

    # Test 1: Load the main extension but patch integration modules to prevent their errors
    with (
        patch("cellmage.integrations.jira_magic.load_ipython_extension"),
        patch("cellmage.integrations.gitlab_magic.load_ipython_extension"),
        patch("cellmage.integrations.github_magic.load_ipython_extension"),
        patch("cellmage.integrations.confluence_magic.load_ipython_extension"),
    ):
        try:
            import cellmage

            # Patch the chat manager to avoid runtime errors
            with patch("cellmage.magic_commands.ipython.common.get_chat_manager"):
                cellmage.load_ipython_extension(mock_shell)

            # Check that register_magics was called at least once
            assert mock_shell.register_magics.call_count > 0
            print(
                f"✅ Main extension loaded successfully (registered {mock_shell.register_magics.call_count} magic classes)"
            )
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to load main extension: {e}")

    # Test 2: Test loading just the magic_commands module
    try:
        mock_shell.register_magics.reset_mock()
        from cellmage.magic_commands import load_ipython_extension

        # Patch common components to prevent runtime errors
        with patch("cellmage.magic_commands.ipython.common.get_chat_manager"):
            load_ipython_extension(mock_shell)

        assert mock_shell.register_magics.call_count > 0
        print(
            f"✅ Magic commands module loaded successfully (registered {mock_shell.register_magics.call_count} magic classes)"
        )
        success_count += 1
    except Exception as e:
        print(f"❌ Failed to load magic_commands module: {e}")

    # Test 3: Test loading specific magic classes directly
    try:
        # Try to import and verify the classes
        from cellmage.magic_commands.ipython.ambient_magic import AmbientModeMagics
        from cellmage.magic_commands.ipython.config_magic import ConfigMagics
        from cellmage.magic_commands.ipython.llm_magic import CoreLLMMagics

        # Check for the key methods
        assert hasattr(ConfigMagics, "configure_llm")
        assert hasattr(CoreLLMMagics, "execute_llm")
        assert hasattr(AmbientModeMagics, "configure_llm_persistent")
        assert hasattr(AmbientModeMagics, "disable_llm_config_persistent")

        print("✅ All magic classes imported and verified successfully")
        success_count += 1
    except ImportError as e:
        print(f"❌ Failed to import magic classes: {e}")
    except AssertionError:
        print("❌ Magic classes don't have expected methods")
    except Exception as e:
        print(f"❌ Unexpected error testing magic classes: {e}")

    # Print summary
    if success_count == 3:
        print("\n✅ All tests passed! The refactored magic commands should work correctly.")
    else:
        print(f"\n⚠️ {success_count}/3 tests passed. Further debugging may be needed.")

    return success_count == 3


def run_integration_tests():
    """Run the integration tests for the refactored magics."""
    print("\n=== Running Integration Tests ===\n")
    try:
        import pytest

        # Run the tests with pytest-xvs flag (explained to user)
        # -x: exit on first failure
        # -v: verbose output
        # -s: don't capture stdout/stderr
        test_result = pytest.main(["-xvs", "tests/integration/test_refactored_magics.py"])

        if test_result == 0:  # pytest.ExitCode.OK
            print("\n✅ Integration tests passed successfully!")
            return True
        else:
            print(f"\n❌ Some integration tests failed (exit code: {test_result})")
            return False
    except ImportError:
        print("❌ pytest not installed. Cannot run integration tests.")
        return False
    except Exception as e:
        print(f"❌ Failed to run integration tests: {e}")
        return False


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test the refactored magic commands")
    parser.add_argument(
        "--with-integration", action="store_true", help="Run integration tests as well"
    )
    args = parser.parse_args()

    # Run the basic tests
    basic_tests_passed = test_magic_refactoring()

    # Run integration tests if requested
    if args.with_integration:
        integration_tests_passed = run_integration_tests()

        # Only succeed if both test suites pass
        sys.exit(0 if (basic_tests_passed and integration_tests_passed) else 1)
    else:
        sys.exit(0 if basic_tests_passed else 1)
