"""
Unit tests for a project's controller object.
"""

from tests import fixture
import unittest


class Controller(unittest.TestCase):
    """Tests for the controller container object."""
    def setUp(self):
        prj = fixture.setup()
        self.controller = prj.controller

    def test_read_comm_path(self):
        """Ensure comm_path attribute is a non-empty string."""
        path = self.controller.comm_path
        self.assertIsInstance(path, str)
        self.assertGreater(len(path), 0)

    def test_set_comm_path(self):
        """Test setting a new communication path."""
        old = self.controller.comm_path
        new = '\\'.join((old, '1'))
        self.controller.comm_path = new
        self.assertEqual(self.controller.comm_path, new)

    def test_comm_path_type(self):
        """Test setting comm_path to a non-string raises an exception."""
        with self.assertRaises(TypeError):
            self.controller.comm_path = 0

    def test_del_comm_path(self):
        """Test deleting comm_path."""
        self.controller.comm_path = None
        self.assertIsNone(self.controller.comm_path)

        # Ensure deleting a nonexistent path succeeds.
        self.controller.comm_path = None

    def test_snn_read(self):
        """Test reading the safety network number."""
        snn = self.controller.snn

    def test_snn_write(self):
        """Test writing the safety network number."""
        self.controller.snn = '000011110000'

    @classmethod
    def tearDownClass(cls):
        """Changes the output project."""
        prj = fixture.setup()

        # Communication path.
        old = prj.controller.comm_path
        new = '\\'.join(('output', old, '42'))
        prj.controller.comm_path = new

        # Safety network number.
        prj.controller.snn = '000A0BADD00D'

        fixture.teardown(prj)
