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


class ParseDim(unittest.TestCase):
    """Unit tests for parsing dimension attributes."""

    def test_tag(self):
        """Verify a top-level tag's dimensions."""

        # Tags may have between 1 and 3 dimensions, inclusive.
        for size in range(1, 4):
            expected = tuple([x + 1 for x in range(size)])
            e = ElementTree.Element('Tag')
            e.attrib['Dimensions'] = self._dim_str(expected)
            ar = type('TestArray', (array.Base, ), {'element': e})
            self.assertEqual(expected, ar.get_dim())

    def test_udt(self):
        """Verify a UDT member's dimension."""

        # UDT's may only have a single dimension.
        expected = (5, )

        e = ElementTree.Element('Member')
        e.attrib['Dimension'] = self._dim_str(expected)
        ar = type('TestArray', (array.Base, ), {'element': e})
        self.assertEqual(expected, ar.get_dim())

    def _dim_str(self, dim):
        """Generates an attribute string from a given set of dimensions."""
        return ' '.join([str(x) for x in reversed(dim)])
