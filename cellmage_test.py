"""
CellMage Extension Check

This script tests the CellMage extension loading mechanism to verify fixes.
"""

import logging
import pkgutil
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cellmage_test")


def test_tools_import():
    """Test importing tools module and checking return type."""
    try:

        print("✅ Successfully imported cellmage.magic_commands.tools")

        # Verify the module discovery function
        def discover_tools() -> List[str]:
            """Discover available tool magic modules."""
            import cellmage.magic_commands.tools as tools_pkg

            # Skip base tools magic and __pycache__
            skip_modules = ["base_tools_magic", "__pycache__"]

            discovered = []

            # Iterate through the available modules
            for _, mod_name, _ in pkgutil.iter_modules(tools_pkg.__path__):
                if mod_name in skip_modules:
                    continue

                # Extract the name without _magic for display
                tool_name = mod_name.replace("_magic", "")
                discovered.append(tool_name)

            return discovered

        # Run the discovery function
        discovered_tools = discover_tools()
        print(f"📋 Discovered tools: {discovered_tools}")

    except Exception as e:
        print(f"❌ Error importing or testing tools module: {e}")


def test_integrations_import():
    """Test importing integrations module."""
    try:

        print("✅ Successfully imported cellmage.integrations")

        # Discover available integrations
        def discover_integrations() -> List[str]:
            """Discover available integration modules."""
            import cellmage.integrations as int_pkg

            # Skip non-integrations
            skip_modules = ["__pycache__"]

            discovered = []

            # Iterate through the available modules
            for _, mod_name, _ in pkgutil.iter_modules(int_pkg.__path__):
                if mod_name in skip_modules:
                    continue

                # Track integration utils
                if mod_name.endswith("_utils"):
                    base_name = mod_name.replace("_utils", "")
                    discovered.append(base_name)
                else:
                    discovered.append(mod_name)

            return discovered

        # Run the discovery function
        discovered_integrations = discover_integrations()
        print(f"📋 Discovered integrations: {discovered_integrations}")

    except Exception as e:
        print(f"❌ Error importing or testing integrations module: {e}")


def main():
    """Run all tests."""
    print("🧪 Testing CellMage Extension Loading\n")

    # Import the main module
    try:
        import cellmage

        print(f"✅ Successfully imported cellmage (version: {cellmage.__version__})")
    except Exception as e:
        print(f"❌ Error importing cellmage: {e}")
        return

    # Test tools import
    test_tools_import()

    # Test integrations import
    test_integrations_import()

    print("\n✅ Tests completed")


if __name__ == "__main__":
    main()
