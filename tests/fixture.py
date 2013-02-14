"""
Utilities used by all test modules to ensure test output is accumulated into
a single output file for final validation by RSLogix.
"""

import l5x


INPUT_FILE = 'tests/test.L5X'
OUTPUT_FILE = 'tests/output.L5X'


def setup():
    """Called by setUpModule to acquire the project for testing."""
    try:
        prj = l5x.Project(OUTPUT_FILE)
    except IOError:
        prj = l5x.Project(INPUT_FILE)
    return prj


def teardown(prj):
    """Called by tearDownModule to write the tests final output data."""
    prj.write(OUTPUT_FILE)
