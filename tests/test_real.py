"""
Unit tests for the REAL(floating-point) data type.
"""

from l5x import (atomic, rawtypes, tag)
import unittest
import xml.etree.ElementTree as ElementTree


class Base(object):
    """Base class for all unit tests."""

    def create_buf(self):
        """Creates a raw data buffer for the test value."""
        buf = bytearray(4)

        # Create a ctype from the same buffer so buffer content can be
        # accessed independently from the REAL object being tested.
        self.raw_value = rawtypes.REAL.from_buffer(buf)

        return buf

    def test_value_read(self):
        """Confirm reading the current value."""
        self.raw_value.value = 1.0
        self.assertEqual(1.0, self.test_real.value)

    def test_value_write(self):
        """Confirm writing a new value."""
        self.test_real.value = 1.0
        self.assertEqual(1.0, self.raw_value.value)

    def test_value_invalid_type(self):
        """Confirm an exception is raised when writing a non-float value."""
        with self.assertRaises(TypeError):
            self.test_real.value = 'not a float'

    def test_invalid_values(self):
        """Ensure NaN and infinite values raise an exception."""
        for value in ['NaN', 'inf']:
            with self.assertRaises(ValueError):
                self.test_real.value = float(value)

    def test_datatype(self):
        """Confirm the data_type attribute returns the data type name."""
        self.assertEqual('REAL', self.test_real.data_type)


class AsTag(Base, unittest.TestCase):
    """Runs the tests as a top-level tag."""

    def setUp(self):
        buf = self.create_buf()
        element = ElementTree.Element('Tag')
        element.attrib['TagType'] = 'Base'
        element.attrib['DataType'] = 'REAL'
        prj = type('prj', (object, ), {'get_tag_data_buffer': lambda x : buf})
        real_type = type('TestTag', (atomic.REAL, tag.Tag), {})
        self.test_real = real_type(element, prj, None)


class AsMember(Base, unittest.TestCase):
    """Runs the tests as a data member."""

    def setUp(self):
        buf = self.create_buf()
        element = ElementTree.Element('Member')
        element.attrib['DataType'] = 'REAL'
        real_type = type('TestReal', (atomic.REAL, tag.Member),
                        {'element':element})
        self.test_real = real_type(None, buf, '')
