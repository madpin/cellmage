# filepath: /Users/tpinto/madpin/cellmage/tests/integration/magic_commands/integration_test_base.py
"""
Base test case for magic command integration testing.

This module provides base classes and fixtures for integration testing
of CellMage magic commands in a more realistic environment.
"""

import unittest

import pytest

# Check if IPython is available
try:
    import IPython  # noqa: F401
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.testing.globalipapp import get_ipython, start_ipython

    IPYTHON_AVAILABLE = True
except ImportError:
    IPYTHON_AVAILABLE = False


@pytest.fixture(scope="module")
def ipython_instance():
    """Fixture that starts and provides a real IPython kernel.

    This is useful for integration tests that need to test magics
    in a real IPython environment.

    Yields:
        InteractiveShell: A running IPython shell instance.
    """
    if not IPYTHON_AVAILABLE:
        pytest.skip("IPython not available")

    try:
        # Try direct instance creation first, as this is more reliable
        ipython = InteractiveShell.instance()

        # Fallback to other methods if needed
        if ipython is None:
            ipython = start_ipython()
        if ipython is None:
            ipython = get_ipython()

        # Make sure we have an IPython instance
        if ipython is None:
            pytest.skip("Could not create IPython instance")

        # Yield the instance for use in tests
        yield ipython
    except Exception as e:
        pytest.skip(f"Could not create IPython instance: {str(e)}")
        return None


@pytest.mark.skipif(not IPYTHON_AVAILABLE, reason="IPython not available")
class MagicIntegrationTest(unittest.TestCase):
    """Base class for magic command integration tests.

    This class provides common setup and utility methods for integration
    testing of magic commands with a real IPython shell.
    """

    @classmethod
    def setUpClass(cls):
        """Set up the test environment once for all tests."""
        try:
            # Create a real InteractiveShell instance
            cls.ip = InteractiveShell.instance()
            cls.shell_available = cls.ip is not None
        except Exception as e:
            cls.shell_available = False
            cls.setup_error = str(e)

    def setUp(self):
        """Set up for each test."""
        if not self.shell_available:
            self.skipTest(f"IPython test shell could not be created: {self.setup_error}")

    def register_magic(self, magic_class, shell=None):
        """Register a magic class with the IPython shell.

        Args:
            magic_class: The magic class to register.
            shell: The shell to register with (defaults to self.ip).

        Returns:
            object: The registered magic instance.
        """
        shell = shell or self.ip
        magic_instance = magic_class(shell)
        shell.register_magics(magic_instance)
        return magic_instance

    def load_extension(self, extension_name: str) -> bool:
        """Load an extension into the IPython shell.

        Args:
            extension_name: The name of the extension to load.

        Returns:
            bool: True if the extension was loaded successfully.
        """
        try:
            self.ip.run_cell(f"%load_ext {extension_name}")
            return True
        except Exception as e:
            self.skipTest(f"Could not load extension {extension_name}: {e}")
            return False

    def assert_magic_registered(self, magic_name: str, magic_type: str = "line"):
        """Assert that a magic command is registered in the IPython shell.

        Args:
            magic_name: The name of the magic command.
            magic_type: The type of magic command ('line' or 'cell').
        """
        self.assertIn(magic_type, self.ip.magics_manager.magics)
        self.assertIn(magic_name, self.ip.magics_manager.magics[magic_type])

    def run_line_magic(self, magic_name: str, line: str = "") -> object:
        """Run a line magic and return its result.

        Args:
            magic_name: The name of the magic command.
            line: The arguments to pass to the magic.

        Returns:
            object: The result of the magic command.
        """
        return self.ip.run_line_magic(magic_name, line)

    def run_cell_magic(self, magic_name: str, line: str = "", cell: str = "") -> object:
        """Run a cell magic and return its result.

        Args:
            magic_name: The name of the magic command.
            line: The arguments to pass to the line part of the magic.
            cell: The cell content to pass to the magic.

        Returns:
            object: The result of the magic command.
        """
        return self.ip.run_cell_magic(magic_name, line, cell)
