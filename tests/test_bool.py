"""
Unit tests for the BOOL data type. These do not cover BOOLs that are members
of a parent integer; those are tested in integer tests.
"""

from l5x import (atomic, tag)
import xml.etree.ElementTree as ElementTree
import unittest


class Common(object):
    """Common unit tests for all BOOL instances."""

    def setUp(self):
        self.test_bool = self.create_test_bool()

    def test_value_invalid_type(self):
        """Confirm an exception is raised when writing a non-integer value."""
        with self.assertRaises(TypeError):
            self.test_bool.value = 'spam'

    def test_out_of_range_value(self):
        """Test exception when setting values beyond 0 or 1."""
        for x in [-1, 2]:
            with self.assertRaises(ValueError):
                self.test_bool.value = x

    def test_data_type(self):
        """Confirm the data_type attribute returns the correct type."""
        self.assertEqual('BOOL', self.test_bool.data_type)


class AsTag(Common, unittest.TestCase):
    """Unit tests for a top-level BOOL tag."""

    def create_test_bool(self):
        """Creates a test BOOL object as a top-level tag."""
        self.buf = bytearray(1)

        element = ElementTree.Element('Tag')
        element.attrib['TagType'] = 'Base'
        element.attrib['DataType'] = 'BOOL'

        # Create a dummy project that can return the tag's raw data buffer.
        prj = type('prj', (object, ),
                   {'get_tag_data_buffer': lambda x : self.buf})

        tag_type = type('TestBool', (tag.Tag, atomic.BOOL), {})

        return tag_type(element, prj, None)

    def test_value_read_zero(self):
        """Confirm reading a 0 value."""
        self.buf[0] = 0
        self.assertEqual(0, self.test_bool.value)

    def test_value_read_one(self):
        """Confirm reading a 1 value."""
        self.buf[0] = 1
        self.assertEqual(1, self.test_bool.value)

    def test_value_write_zero(self):
        """Confirm writing a 0 value."""
        self.buf[0] = 1
        self.test_bool.value = 0
        self.assertEqual(0, self.buf[0])

    def test_value_write_one(self):
        """Confirm writing a 1 value."""
        self.buf[0] = 0
        self.test_bool.value = 1
        self.assertEqual(1, self.buf[0])


def iterate_member_bits(test_method):
    """
    Decorator function to execute data member test methods across each
    possible bit within the underlying SINT.
    """
    def wrapper(self):
        for bit in range(8):
            self.test_bool = self.create_test_bool(bit)
            test_method(self, bit)

    return wrapper


class AsMember(Common, unittest.TestCase):
    """Unit tests for a BOOL data member."""

    def create_test_bool(self, bit=0):
        """Creates a test member targeting a specific raw data bit."""
        self.buf = bytearray(1)

        element = ElementTree.Element('Member')
        element.attrib['DataType'] = 'BOOL'

        member_type = type('TestType', (tag.Member, atomic.BOOL),
                           {'element':element})

        return member_type(None, self.buf, '', bit)

    @iterate_member_bits
    def test_value_read_zero(self, bit):
        """Confirm reading a 0 value evaluates only the target bit."""

        # Set all raw data bits except the target bit to 1.
        self.buf[0] = 0xff ^ (1 << bit)

        self.assertEqual(0, self.test_bool.value)

    @iterate_member_bits
    def test_value_read_one(self, bit):
        """Confirm reading a 1 value evaluates only the target bit."""

        # Set all raw data bits except the target bit to 0.
        self.buf[0] = 1 << bit

        self.assertEqual(1, self.test_bool.value)

    @iterate_member_bits
    def test_value_write_zero(self, bit):
        """Confirm writing a 0 affects only the target bit."""

        # Set all raw data bits.
        self.buf[0] = 0xff

        self.test_bool.value = 0
        self.assertEqual(0xff ^ (1 << bit), self.buf[0])

    @iterate_member_bits
    def test_value_write_one(self, bit):
        """Confirm writing a 1 affects only the target bit."""

        # Clear all raw data bits.
        self.buf[0] = 0

        self.test_bool.value = 1
        self.assertEqual(1 << bit, self.buf[0])
