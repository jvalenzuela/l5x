"""
Unit tests for a project's programs object.
"""

from tests import fixture
import unittest


class Programs(unittest.TestCase):
    """Tests for the top-level programs container object."""
    def setUp(self):
        prj = fixture.setup()
        self.programs = prj.programs

    def test_names_type(self):
        """Test name attribute returns an interable of non-empty strings."""
        self.assertGreater(len(self.programs.names), 0)
        for prg in self.programs.names:
            self.assertIsInstance(prg, str)
            self.assertGreater(len(prg), 0)

    def test_names_read_only(self):
        """Ensure names attribute is read-only."""
        with self.assertRaises(AttributeError):
            self.programs.names = 'foo'

    def test_index(self):
        """Test indexing by names."""
        for prg in self.programs.names:
            self.programs[prg]

    def test_tags_names(self):
        """Ensure tags names attribute is a iterable of non-empty strings."""
        for prg in self.programs.names:
            tags = self.programs[prg].tags.names
            for tag in tags:
                self.assertIsInstance(tag, str)
                self.assertGreater(len(tag), 0)

    @classmethod
    def tearDownClass(cls):
        """Add program tag descriptions to the output project."""
        prj = fixture.setup()

        for prg in prj.programs.names:
            for tag in prj.programs[prg].tags.names:
                desc = ' '.join((prg, tag))
                prj.programs[prg].tags[tag].description = desc
        
        fixture.teardown(prj)
