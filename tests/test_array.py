"""
Unit tests for the array module.
"""

from l5x import array
import xml.etree.ElementTree as ElementTree
import unittest


class ArrayDetect(unittest.TestCase):
    """Unit tests for the is_array function."""

    def test_tag_non_array(self):
        """Confirm a non-array tag is not detected as an array."""
        e = ElementTree.Element('Tag')
        self.assertFalse(array.is_array(e))

    def test_tag_array_single(self):
        """Confirm a single-dimensional array tag is detected as an array."""
        e = ElementTree.Element('Tag')
        e.attrib['Dimensions'] = '1'
        self.assertTrue(array.is_array(e))

    def test_tag_array_multi(self):
        """Confirm a multi-dimensional array tag is detected as an array."""
        e = ElementTree.Element('Tag')
        e.attrib['Dimensions'] = '1 2'
        self.assertTrue(array.is_array(e))

    def test_udt_non_array(self):
        """Confirm a non-array UDT member is not detected as an array."""
        e = ElementTree.Element('Member')
        e.attrib['Dimension'] = '0'
        self.assertFalse(array.is_array(e))

    def test_udt_array(self):
        """Confirm an array UDT member is detected as an array."""
        e = ElementTree.Element('Member')
        e.attrib['Dimension'] = '1'
        self.assertTrue(array.is_array(e))
