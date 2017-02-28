"""
Unit tests for the low-level XML interfaces.
"""

import l5x
from lxml import etree
import unittest


class ElementDict(unittest.TestCase):
    """Tests for the ElementDict accessor object."""
    def setUp(self):
        self.root = etree.Element('root')
        self.key_attr_values = ['foo', 'bar', 'baz']
        [etree.SubElement(self.root, 'child', key=n)
         for n in self.key_attr_values]

    def test_names(self):
        """Ensure the names attribute returns key attribute values."""
        e = l5x.dom.ElementDict(self.root, 'key', None)
        self.assertEqual(e.names, self.key_attr_values)

    def test_names_read_only(self):
        """Confirm attempts to modify names raises an exception."""
        e = l5x.dom.ElementDict(self.root, 'key', None)
        with self.assertRaises(AttributeError):
            e.names = 'foo'

    def test_fixed_child_type(self):
        """Confirm access to child elements with a fixed access class."""
        e = l5x.dom.ElementDict(self.root, 'key', ElementDictChild)
        for i in range(len(self.key_attr_values)):
            key = self.key_attr_values[i]
            child = e[key]
            self.assertIs(child.element, self.root[i])


class ElementDictChild(object):
    """Dummy child access object for ElementDict testing."""
    def __init__(self, element):
        self.element = element
