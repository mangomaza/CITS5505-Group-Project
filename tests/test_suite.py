import unittest

from tests.test_issue_unit import IssueUnitTests
from tests.test_selenium_system import SeleniumSystemTests


def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(IssueUnitTests))
    suite.addTests(loader.loadTestsFromTestCase(SeleniumSystemTests))
    return suite


if __name__ == '__main__':
    unittest.main(verbosity=2)
