"""
Unit tests for the atomic integer types.
"""

from l5x import (atomic, rawtypes, tag)
import ctypes
import xml.etree.ElementTree as ElementTree
import unittest


class Integer(object):
    """
    Base class defining test methods to be executed against each integer
    type..
    """

    def create_buf(self):
        """Creates a raw data buffer for the test integer."""
        buf = bytearray(self._num_bits // 8)

        # Create a ctype from the same buffer so buffer content can be
        # accessed independently from the integer object being tested.
        self.raw_value = self.raw_type.from_buffer(buf)

        return buf

    @property
    def _num_bits(self):
        """Calculates the number of bits in the target type."""
        return ctypes.sizeof(self.raw_type) * 8

    @property
    def _min(self):
        """
        Calculates the smallest value that can be represented by the test
        integer.
        """
        return -2 ** (self._num_bits - 1)

    @property
    def _max(self):
        """
        Calculates the largest value that can be represented by the test
        integer.
        """
        return (2 ** (self._num_bits - 1)) - 1

    def test_value_read(self):
        """Verify reading the value returns the correct value."""
        self.raw_value.value = 42
        self.assertEqual(self.test_int.value, 42)

    def test_value_write(self):
        """Verify writing a value correctly updates the raw data."""
        self.test_int.value = 42
        self.assertEqual(42, self.raw_value.value)

    def test_value_write_type(self):
        """Verify setting the value to a non-integer raises an exception."""
        with self.assertRaises(TypeError):
            self.test_int.value = '42'

    def test_value_out_of_range(self):
        """Ensure setting out-of-range values raise an exception."""
        with self.assertRaises(ValueError):
            self.test_int.value = self._min - 1
        with self.assertRaises(ValueError):
            self.test_int.value = self._max + 1

    def test_value_min(self):
        """Confirm the minimum value is accepted."""
        self.test_int.value = self._min

    def test_value_max(self):
        """Confirm the maximum value is accepted."""
        self.test_int.value = self._max

    def test_invalid_index(self):
        """Verify invalid bit indices raise an exception."""
        with self.assertRaises(IndexError):
            self.test_int[-1]
        with self.assertRaises(IndexError):
            self.test_int[self._num_bits]

    def test_bit_index_type(self):
        """Verify non-integer bit indices raise an exception."""
        with self.assertRaises(TypeError):
            self.test_int['foo']

    def test_bit_value_read(self):
        """Confirm non-sign bits reflect the current integer value."""
        for bit in range(self._num_bits - 1):
            # Check setting only the target bit.
            value = 1 << bit
            self.raw_value.value = value
            for test_bit in range(self._num_bits):
                if test_bit == bit:
                    test_value = 1
                else:
                    test_value = 0
                self.assertEqual(self.test_int[test_bit].value, test_value)

            # Check setting all except the target bit.
            value = ~(1 << bit)
            self.raw_value.value = value
            for test_bit in range(self._num_bits):
                if test_bit == bit:
                    test_value = 0
                else:
                    test_value = 1
                self.assertEqual(self.test_int[test_bit].value, test_value)

    def test_bit_value_write(self):
        """Confirm writing non-sign bits properly update the integer value."""
        for bit in range(self._num_bits - 1):
            # Check setting only the target bit.
            self.raw_value.value = 0
            self.test_int[bit].value = 1
            self.assertEqual(self.raw_value.value, 1 << bit)

            # Check clearing only the target bit.
            self.raw_value.value = -1
            self.test_int[bit].value = 0
            self.assertEqual(self.raw_value.value, ~(1 << bit))

    def test_sign_bit_read(self):
        """Confirm MSB is treated as the sign when reading a value."""
        sign_bit = self._num_bits - 1
        self.raw_value.value = self._min
        self.assertEqual(self.test_int[sign_bit].value, 1)

    def test_sign_bit_write(self):
        """Confirm MSB is treated as the sign bit when writing a value."""
        sign_bit = self._num_bits - 1
        self.test_int[sign_bit].value = 1
        self.assertEqual(self.raw_value.value, self._min)

    def test_bit_write_type(self):
        """
        Confirm an exception is raised when setting a bit to a non-integer.
        """
        with self.assertRaises(TypeError):
            self.test_int[0].value = 'foo'

    def test_bit_value_range(self):
        """Ensure bit values other than 0 or 1 raise an exception."""
        with self.assertRaises(ValueError):
            self.test_int[0].value = -1
        with self.assertRaises(ValueError):
            self.test_int[0].value = 2

    def test_datatype(self):
        """Confirm the data_type attribute returns the data type name."""
        self.assertEqual(self.raw_type.__name__, self.test_int.data_type)

    def test_bit_datatype(self):
        """Confirm bit objects return the correct data type."""
        bit = self.test_int[0]
        self.assertEqual('BOOL', bit.data_type)


class AsTag(Integer):
    """Creates a test integer object as a top-level tag."""

    def setUp(self):
        buf = self.create_buf()
        element = ElementTree.Element('Tag')
        element.attrib['TagType'] = 'Base'
        element.attrib['DataType'] = self.raw_type.__name__
        prj = type('prj', (object, ), {'get_tag_data_buffer': lambda x : buf})
        i_type = type('TestTag', (tag.Tag, self.dtype), {})
        self.test_int = i_type(element, prj, None)


class AsMember(Integer):
    """Creates a test integer object as a member."""

    def setUp(self):
        buf = self.create_buf()
        element = ElementTree.Element('Member')
        element.attrib['DataType'] = self.raw_type.__name__
        int_type = type('TestInt', (tag.Member, self.dtype),
                        {'element':element})
        self.test_int = int_type(None, buf, '')


class TypeSINT(object):
    """Type definitions for SINT tests."""

    raw_type = rawtypes.SINT
    dtype = atomic.SINT


class TagSINT(TypeSINT, AsTag, unittest.TestCase):
    """Combines the necessary superclasses to test a SINT top-level tag."""
    pass


class MemberSINT(TypeSINT, AsMember, unittest.TestCase):
    """Combines the necessary superclasses to tests a SINT member."""
    pass


class TypeINT(object):
    """Type definitions for INT tests."""

    raw_type = rawtypes.INT
    dtype = atomic.INT


class TagINT(TypeINT, AsTag, unittest.TestCase):
    """Combines the necessary superclasses to test an INT top-level tag."""
    pass


class MemberINT(TypeINT, AsMember, unittest.TestCase):
    """Combines the necessary superclasses to tests an INT member."""
    pass


class TypeDINT(object):
    """Type definitions for DINT tests."""

    raw_type = rawtypes.DINT
    dtype = atomic.DINT


class TagDINT(TypeDINT, AsTag, unittest.TestCase):
    """Combines the necessary superclasses to test a DINT top-level tag."""
    pass


class MemberDINT(TypeDINT, AsMember, unittest.TestCase):
    """Combines the necessary superclasses to tests a DINT member."""
    pass


class TypeLINT(object):
    """Type definitions for LINT tests."""

    raw_type = rawtypes.LINT
    dtype = atomic.LINT


class TagLINT(TypeLINT, AsTag, unittest.TestCase):
    """Combines the necessary superclasses to test a LINT top-level tag."""
    pass


class MemberLINT(TypeLINT, AsMember, unittest.TestCase):
    """Combines the necessary superclasses to tests a LINT member."""
    pass


class BitOperand(unittest.TestCase):
    """Unit tests for the comment operand assigned to an integer bit."""

    def test_tag(self):
        """Verify operand string for a top-level integer tag."""
        bit = self._create_bit('', 0)
        self.assertEqual('.0', bit.operand)

    def test_member(self):
        """Verify operand string for a integer member."""
        bit = self._create_bit('spam', 2)
        self.assertEqual('spam.2', bit.operand)

    def _create_bit(self, int_name, bit):
        """Creates a test bit object."""
        buf = bytearray(1)
        element = ElementTree.Element('Tag')
        int_type = type('TestTag', (tag.Member, atomic.SINT), {})
        int_tag = int_type(None, buf, int_name)
        return int_tag[bit]
