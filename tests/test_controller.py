"""
Unit tests for a project's controller object.
"""

from l5x import project
import unittest
import xml.etree.ElementTree as ElementTree


class Controller(unittest.TestCase):
    """Tests for the controller container object."""
    def setUp(self):
        ctl_element = ElementTree.Element('Controller')

        # Add a controller module.
        modules = ElementTree.SubElement(ctl_element, 'Modules')
        ElementTree.SubElement(modules, 'Module')

        # Add an empty Tags parent.
        ElementTree.SubElement(ctl_element, 'Tags')

        self.controller = project.Controller(ctl_element, None)

    def test_read_comm_path(self):
        """Ensure comm_path returns the correct attribute value."""
        self.controller.element.attrib['CommPath'] = 'foo'
        self.assertEqual(self.controller.comm_path, 'foo')

    def test_read_nonexistent_comm_path(self):
        """Ensure reading a nonexistent communication path returns None."""
        self.assertIsNone(self.controller.comm_path)

    def test_new_comm_path(self):
        """Test setting a new communication path."""
        self.controller.comm_path = 'new'
        self.assertEqual(self.controller.element.attrib['CommPath'], 'new')

    def test_overwrite_comm_path(self):
        """Test modifying an existing communication path."""
        self.controller.element.attrib['CommPath'] = 'old'
        self.controller.comm_path = 'new'
        self.assertEqual(self.controller.element.attrib['CommPath'], 'new')

    def test_comm_path_type(self):
        """Test setting comm_path to a non-string raises an exception."""
        with self.assertRaises(TypeError):
            self.controller.comm_path = 0

    def test_remove_existing_comm_path(self):
        """Test deleting an existing communication path."""
        self.controller.element.attrib['CommPath'] = 'foo'
        self.controller.comm_path = None
        with self.assertRaises(KeyError):
            self.controller.element.attrib['CommPath']

    def test_remove_nonexistent_comm_path(self):
        """Test deleting a communication path when one does not exist."""
        self.controller.comm_path = None
        with self.assertRaises(KeyError):
            self.controller.element.attrib['CommPath']

    def test_snn_read(self):
        """Test reading the safety network number."""
        module = self.controller.element.find('Modules/Module')
        module.attrib['SafetyNetwork'] = '16#0000_0000_1111_2222'
        self.assertEqual(self.controller.snn, '000011112222')
