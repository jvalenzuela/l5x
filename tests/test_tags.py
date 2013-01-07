"""
Unittests for tag accesss.
"""

import ctypes
import l5x
import math
import unittest


class Tag(object):
    """Base class for testing a tag."""
    def setUp(self):
        self.tag = doc.controller.tags[self.name]

    def test_desc(self):
        """Test reading and writing tag's description."""
        # Test project should begin with no description.
        self.assertIsNone(self.tag.description)

        desc = ' '.join((self.name, 'description'))
        self.tag.description = desc
        self.assertEqual(self.tag.description, desc)

    @classmethod
    def tearDownClass(cls):
        """Sets tag's final value for the output project."""
        doc.controller.tags[cls.name].value = cls.output_value


class Integer(Tag):
    """Base class for testing integer data types."""
    output_value = -1

    def test_type(self):
        """Verify correct data type string."""
        self.assertEqual(self.tag.data_type, self.data_type)

    def test_length(self):
        """Test len() returns number of bits."""
        self.assertEqual(len(self.tag), self.bits)

    def test_value_type(self):
        """Verify value access uses integers."""
        self.assertIsInstance(self.tag.value, int)
        with self.assertRaises(TypeError):
            self.tag.value = 'not an int'

    def test_value_range(self):
        """Ensure setting out-of-range values raises an exception."""
        try:
            with self.assertRaises(ValueError):
                self.tag.value = self.value_min - 1
            with self.assertRaises(ValueError):
                self.tag.value = self.value_max + 1

        # Ignore type errors on Python 2.7.x if the out-of-range
        # test value is promoted to long.
        except TypeError:
            pass
                
    def test_value(self):
        """Test setting and getting of valid values."""
        for value in [0, self.value_min, self.value_max]:
            self.tag.value = value
            self.assertEqual(self.tag.value, value)

    def test_invalid_bit_indices(self):
        """Verify invalid bit indices raise an exception."""
        with self.assertRaises(IndexError):
            self.tag[-1]
        with self.assertRaises(IndexError):
            self.tag[len(self.tag)]

    def test_bit_value_type(self):
        """Ensure bit values are expressed as integers."""
        self.assertIsInstance(self.tag[0].value, int)
        with self.assertRaises(TypeError):
            self.tag[0] = 'foo'

    def test_bit_value_range(self):
        """Ensure bit values accept only 0 or 1."""
        self.tag[0].value = 0
        self.tag[0].value = 1
        with self.assertRaises(ValueError):
            self.tag[0].value = 2

    def test_bit_values(self):
        """Verify bit values are reflected in the full integer."""
        # Start with all bits cleared.
        self.tag.value = 0
        sign_bit = len(self.tag) - 1

        for bit in range(len(self.tag)):
            # The bit should start at zero.
            self.assertEqual(self.tag[bit].value, 0)

            for bit_value in [1, 0]:
                self.tag[bit].value = bit_value
                self.assertEqual(self.tag[bit].value, bit_value)

                # Compare the tag's full value with a bit mask using
                # ctypes to ensure correct sign bit operation.
                cvalue = self.ctype(self.tag.value)
                mask = self.ctype(bit_value << bit)
                self.assertEqual(cvalue.value, mask.value)

    def test_bit_desc(self):
        """ """
        for bit in range(self.bits):
            # Test project should have no bit descriptions at start.
            self.assertIsNone(self.tag[bit].description)

            # Give the bit a description then read it back.
            desc = ' '.join((self.name, str(bit), 'description'))
            self.tag[bit].description = desc
            self.assertEqual(self.tag[bit].description, desc)


class TestSINT(Integer, unittest.TestCase):
    name = 'sint'
    data_type = 'SINT'
    bits = 8
    ctype = ctypes.c_int8
    value_min = -128
    value_max = 127


class TestINT(Integer, unittest.TestCase):
    name = 'int'
    data_type = 'INT'
    bits = 16
    ctype = ctypes.c_int16
    value_min = -32768
    value_max = 32767


class TestDINT(Integer, unittest.TestCase):
    name = 'dint'
    data_type = 'DINT'
    bits = 32
    ctype = ctypes.c_int32
    value_min = -2147483648
    value_max = 2147483647


class TestBOOL(Tag, unittest.TestCase):
    """BOOL type tests."""
    name = 'bool'
    output_value = 1

    def test_value_type(self):
        """Confirm values are integers."""
        self.assertIsInstance(self.tag.value, int)
        with self.assertRaises(TypeError):
            self.tag.value = 'not an int'

    def test_value_range(self):
        """Test exception when setting values other than 0 or 1."""
        for x in [-1, 2]:
            with self.assertRaises(ValueError):
                self.tag.value = x

    def test_value(self):
        """Test setting legal values."""
        for x in [0, 1]:
            self.tag.value = x
            self.assertEqual(self.tag.value, x)


class TestREAL(Tag, unittest.TestCase):
    """REAL type tests."""
    name = 'real'
    output_value = math.pi

    def test_value_type(self):
        """Confirm values are floats."""
        self.assertIsInstance(self.tag.value, float)
        with self.assertRaises(TypeError):
            self.tag.value = 'not a float'

    def test_value(self):
        """Test setting and reading some legal values."""
        for x in [0.0, -1.5, math.pi, math.e]:
            self.tag.value = x
            self.assertAlmostEqual(self.tag.value, x)

    def test_invalid_values(self):
        """Ensure NaN and infinite values raise an exception."""
        for value in ['NaN', 'inf']:
            with self.assertRaises(ValueError):
                self.tag.value = float(value)


class TestArray1(Tag, unittest.TestCase):
    """Single-dimensional array tests."""
    name = 'array1'
    output_value = range(10)

    def test_len(self):
        """Ensure length is a positive integer."""
        self.assertIsInstance(len(self.tag), int)
        self.assertGreater(len(self.tag), 0)

    def test_index_type(self):
        """Ensure non-integer indices raise an exception."""
        with self.assertRaises(TypeError):
            self.tag['not an int']
            
    def test_index_range(self):
        """Ensure negative and indices beyond the end raise exceptions."""
        for i in [-1, len(self.tag)]:
            with self.assertRaises(IndexError):
                self.tag[i]

    def test_value_type(self):
        """Verify value is a list of correct length."""
        self.assertIsInstance(self.tag.value, list)
        self.assertEqual(len(self.tag.value), len(self.tag))

    def test_invalid_value_type(self):
        """Test setting value to a non-list raises an exception."""
        with self.assertRaises(TypeError):
            self.tag.value = 'not a list'

    def test_invalid_value_size(self):
        """Test setting value with an oversize source raises an exception."""
        x = [0] * (len(self.tag) + 1)
        with self.assertRaises(IndexError):
            self.tag.value = x

    def test_value(self):
        """Test setting and getting list values."""
        for v in [[0] * len(self.tag), range(len(self.tag))]:
            self.value = v
            self.assertEqual(self.value, v)

    def test_element_description(self):
        """Test setting and getting element descriptions."""
        for i in range(len(self.tag)):
            # Test project should begin with no description.
            self.assertIsNone(self.tag[i].description)
            
            new_desc = ' '.join(('element', str(i)))
            self.tag[i].description = new_desc
            self.assertEqual(self.tag[i].description, new_desc)
            

def setUpModule():
    """Opens the test project."""
    global doc
    doc = l5x.Project('tests/test.L5X')


def tearDownModule():
    """Writes the output project."""
    doc.write('tests/out_tags.L5X')
