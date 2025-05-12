"""
Final test for CellMage extension loading.
"""

import pkgutil
import sys
import traceback

# Add current directory to path
sys.path.insert(0, ".")

# Force output flushing
import io

sys.stdout = io.TextIOWrapper(open(sys.stdout.fileno(), "wb", 0), write_through=True)


def main():
    try:
        print("=== CellMage Extension Test ===")

        # Import cellmage
        print("Importing cellmage...")
        import cellmage

        print(f"CellMage version: {cellmage.__version__}")
        print("\nSimulating extension loading...")

        # Discover tools
        print("\nDiscovering tools...")
        tools = []
        try:
            import cellmage.magic_commands.tools

            for _, mod_name, _ in pkgutil.iter_modules(cellmage.magic_commands.tools.__path__):
                if mod_name not in ["base_tools_magic", "__pycache__"]:
                    tools.append(mod_name.replace("_magic", ""))

            print(f"Tools discovered: {sorted(tools)}")
        except Exception as e:
            print(f"Error discovering tools: {e}")
            traceback.print_exc()

        # Discover integrations
        print("\nDiscovering integrations...")
        integrations = []
        try:
            import cellmage.integrations

            for _, mod_name, _ in pkgutil.iter_modules(cellmage.integrations.__path__):
                if mod_name != "__pycache__" and mod_name.endswith("_utils"):
                    integrations.append(mod_name.replace("_utils", ""))

            print(f"Integrations discovered: {sorted(integrations)}")
        except Exception as e:
            print(f"Error discovering integrations: {e}")
            traceback.print_exc()

        # Test the utility imports
        print("\nChecking utility imports...")
        try:
            import cellmage.utils

            print(f"Available utilities: {cellmage.utils.__all__}")
        except Exception as e:
            print(f"Error loading utils: {e}")
            traceback.print_exc()

        # Print mock extension loading summary
        try:
            print("\n===== MOCK EXTENSION LOADING OUTPUT =====")
            cellmage._print_extension_status(
                True,  # primary_loaded
                {"llm/cellm": "Interact with LLMs", "config": "Configure settings"},
                tools,
                integrations,
            )
        except Exception as e:
            print(f"Error printing extension status: {e}")
            traceback.print_exc()

        print("\n=== Test Completed ===")

    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
