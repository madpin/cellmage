"""
Test script to verify that the magic imports are working correctly.
"""

print("Attempting to import GitLab magic...")
try:
    from cellmage.magic_commands.tools.gitlab_magic import GitLabMagics

    print("✅ GitLabMagics imported successfully")

    # Create an instance to test _add_to_history method
    gitlab_magic = GitLabMagics()
    print("✅ GitLabMagics instance created")

except Exception as e:
    print(f"❌ Error importing GitLabMagics: {e}")
    import traceback

    traceback.print_exc()

print("\nAttempting to import Jira magic...")
try:
    from cellmage.magic_commands.tools.jira_magic import JiraMagics

    print("✅ JiraMagics imported successfully")

    # Create an instance to test _add_to_history method
    jira_magic = JiraMagics()
    print("✅ JiraMagics instance created")

except Exception as e:
    print(f"❌ Error importing JiraMagics: {e}")
    import traceback

    traceback.print_exc()
