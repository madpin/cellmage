"""Test the dynamic discovery plugin mechanism independently."""

import types
import unittest
from unittest.mock import MagicMock, patch


class DynamicLoadingTest(unittest.TestCase):
    """Test dynamic discovery of plugins without relying on the actual cellmage package."""

    def test_plugin_discovery_pattern(self):
        """Test the core plugin discovery pattern."""
        # Create mock IPython shell
        mock_ipython = MagicMock()

        # Create mock packages and modules
        mock_pkg = types.ModuleType("mock_pkg")
        mock_pkg.__path__ = ["mock_path"]

        # Mock modules that will be discovered
        mock_plugin1 = types.ModuleType("mock_pkg.plugin1")
        mock_plugin1.load_ipython_extension = MagicMock()

        mock_plugin2 = types.ModuleType("mock_pkg.plugin2")
        mock_plugin2.load_ipython_extension = MagicMock()

        # Mock module without load_ipython_extension
        mock_plugin3 = types.ModuleType("mock_pkg.plugin3")

        # Set up mocks for pkgutil.iter_modules and importlib.import_module
        mock_modules = [
            (None, "plugin1", False),
            (None, "plugin2", False),
            (None, "plugin3", False),
        ]

        with patch("pkgutil.iter_modules", return_value=mock_modules):
            with patch(
                "importlib.import_module",
                side_effect=lambda name: {
                    "mock_pkg.plugin1": mock_plugin1,
                    "mock_pkg.plugin2": mock_plugin2,
                    "mock_pkg.plugin3": mock_plugin3,
                }[name],
            ):

                # This is the code pattern we're testing from cellmage.__init__.py
                import importlib
                import pkgutil

                # Dynamic discovery of plugins
                for _, mod_name, _ in pkgutil.iter_modules(mock_pkg.__path__):
                    full_name = f"mock_pkg.{mod_name}"
                    try:
                        module = importlib.import_module(full_name)
                        loader = getattr(module, "load_ipython_extension", None)
                        if callable(loader):
                            loader(mock_ipython)
                    except ImportError:
                        # Just log and continue in real code
                        pass
                    except Exception:
                        # Just log and continue in real code
                        pass

        # Verify the plugins with load_ipython_extension were called
        mock_plugin1.load_ipython_extension.assert_called_once_with(mock_ipython)
        mock_plugin2.load_ipython_extension.assert_called_once_with(mock_ipython)

    def test_magic_discovery_pattern(self):
        """Test the pattern for discovering magic command classes."""
        # Create mock IPython shell
        mock_ipython = MagicMock()
        mock_ipython.register_magics = MagicMock()

        # Create mock magic class
        class TestMagics:
            def __init__(self, shell=None):
                self.shell = shell

        # Create a module with the magic class
        mock_module = types.ModuleType("mock_module")
        mock_module.TestMagics = TestMagics

        # Test the pattern from cellmage/magic_commands/ipython/__init__.py
        for name, obj in mock_module.__dict__.items():
            if isinstance(obj, type) and name.endswith("Magics"):
                try:
                    # Create instance with shell if needed
                    magic_instance = obj(mock_ipython)
                    mock_ipython.register_magics(magic_instance)
                except Exception:
                    pass

        # Check that register_magics was called with an instance
        self.assertEqual(mock_ipython.register_magics.call_count, 1)
        args, _ = mock_ipython.register_magics.call_args
        self.assertIsInstance(args[0], TestMagics)
        self.assertEqual(args[0].shell, mock_ipython)


if __name__ == "__main__":
    unittest.main()
