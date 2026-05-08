import sys
import unittest
from pathlib import Path

# Ensure the project root is available when running this file directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.test_issue_unit import IssueUnitTests
from tests.test_selenium_system import SeleniumTests


def create_test_suite():
    """
    Create an explicit unittest TestSuite for the selected testing scaffold.

    This suite includes:
    - selected backend validation and permission unit tests
    - selected Selenium WebDriver end-to-end system tests
    """
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Unit tests from the issue scaffold
    suite.addTests(loader.loadTestsFromTestCase(IssueUnitTests))

    # Selenium WebDriver tests from the issue scaffold
    suite.addTests(loader.loadTestsFromTestCase(SeleniumTests))

    return suite


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(create_test_suite())

    # Return a non-zero exit code if any test fails.
    if not result.wasSuccessful():
        raise SystemExit(1)