"""
Simple test script to verify that the MagicCommandsTestBase works correctly.
"""

import os
import sys

# Add the path to the cellmage package
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import unittest

from tests.unit.magic_commands.test_base import MagicCommandsTestBase, ipython_required


class SimpleTest(MagicCommandsTestBase):
    """Simple test to verify the MagicCommandsTestBase works."""

    @ipython_required
    def test_ipython_availability(self):
        """Test that IPython is available and decorated test runs."""
        print("IPython is available and test is running!")
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
