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


class TestAttributeDescriptor(unittest.TestCase):
    """Tests for the AttributeDescriptor class."""
    def setUp(self):
        self.root = etree.Element('root')
        self.desc = AttributeDescriptorFixture(self.root)

    def test_get(self):
        """Confirm the attribute's value is returned from a read access."""
        self.root.attrib['attr'] = 'foo'
        self.assertEqual(self.desc.rw, 'foo')

    def test_get_missing(self):
        """Confirm None is returned when reading a nonexistent attribute."""
        self.assertIsNone(self.desc.rw)

    def test_get_conversion(self):
        """Confirm descriptor subclasses convert read values."""
        self.root.attrib['attr'] = '42'
        self.assertEqual(self.desc.convert, 42)

    def test_set(self):
        """Confirm writing an attribute's value."""
        self.desc.rw = 'foo'
        self.assertEqual(self.root.attrib['attr'], 'foo')

    def test_set_read_only(self):
        """Confirm writing a read-only value raises an exception."""
        with self.assertRaises(AttributeError):
            self.desc.ro = 'foo'

    def test_set_type(self):
        """Confirm an exception is raised for non-string values."""
        with self.assertRaises(TypeError):
            self.desc.rw = 42

    def test_del(self):
        """Confirm writing a value of None deletes the attribute."""
        self.root.attrib['attr'] = 'foo'
        self.desc.rw = None
        self.assertNotIn('attr', self.root.attrib)

    def test_del_nonexistent(self):
        """Confirm deleting a nonexistent attribute does nothing."""
        self.desc.rw = None

    def test_set_conversion(self):
        """Confirm descriptor subclasses convert values on write."""
        self.desc.convert = 'spam'
        self.assertEqual(self.root.attrib['attr'], 'eggs')


class ConverterAttributeDescriptor(l5x.dom.AttributeDescriptor):
    """Dummy subclass to test read/write conversions."""
    def from_xml(self, value):
        return int(value)

    def to_xml(self, value):
        return 'eggs'


class AttributeDescriptorFixture(object):
    """Dummy object for AttributeDescriptor tests."""
    rw = l5x.dom.AttributeDescriptor('attr')
    ro = l5x.dom.AttributeDescriptor('attr', True)
    convert = ConverterAttributeDescriptor('attr')

    def __init__(self, element):
        self.element = element
