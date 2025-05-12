"""
Comprehensive test to verify our fix for the GitLab and Jira magic commands.
"""

import logging

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")

# Test both magic modules
print("=== Testing GitLab Magic ===")
try:
    from cellmage.magic_commands.tools.gitlab_magic import GitLabMagics

    print("✅ GitLabMagics imported successfully")

    # Create a minimal mock of needed components
    class DummyShell:
        pass

    gitlab_magic = GitLabMagics(shell=DummyShell())
    print("✅ GitLabMagics instance created successfully")

    # Validate the _add_to_history method specifically
    try:
        result = gitlab_magic._add_to_history(
            content="Test content", source_type="test", source_id="123"
        )
        print(f"✅ gitlab_magic._add_to_history executed (returned {result})")
    except ImportError:
        print("❌ Import error in _add_to_history")
    except Exception as e:
        print(f"⚠️ Other error in _add_to_history: {e}")

except Exception as e:
    print(f"❌ Error with GitLab magic: {e}")
    import traceback

    traceback.print_exc()

print("\n=== Testing Jira Magic ===")
try:
    from cellmage.magic_commands.tools.jira_magic import JiraMagics

    print("✅ JiraMagics imported successfully")

    jira_magic = JiraMagics(shell=DummyShell())
    print("✅ JiraMagics instance created successfully")

    # Validate the _add_to_history method specifically
    try:
        result = jira_magic._add_to_history(
            content="Test content", source_type="test", source_id="JIRA-123"
        )
        print(f"✅ jira_magic._add_to_history executed (returned {result})")
    except ImportError:
        print("❌ Import error in _add_to_history")
    except Exception as e:
        print(f"⚠️ Other error in _add_to_history: {e}")

except Exception as e:
    print(f"❌ Error with Jira magic: {e}")
    import traceback

    traceback.print_exc()
