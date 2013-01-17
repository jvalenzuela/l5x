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


class ArrayOutputValue(object):
    """Descriptor class to generate n-dimensional array output values.

    Creates unique values for each element by incrementing an accumulator
    while iterating through members of each dimension.
    """
    def __get__(self, instance, owner=None):
        self.tag = doc.controller.tags[owner.name]
        self.acc = 0
        return self.build_dim(len(self.tag.shape) - 1)
        
    def build_dim(self, dim):
        """Generates a set of values for elements of a single dimension."""
        elements = range(self.tag.shape[dim])

        # The lowest order dimension results in integer values for each
        # element.
        if dim == 0:
            value = [x + self.acc for x in elements]
            self.acc = value[-1] + 1

        # All other higher order dimensions recursively build a list for each
        # element.
        else:
            value = [self.build_dim(dim - 1) for x in elements]

        return value


class TestArray1(Tag, unittest.TestCase):
    """Single-dimensional array tests."""
    name = 'array1'
    output_value = ArrayOutputValue()

    def test_shape_type(self):
        """Ensure shape is a tuple."""
        self.assertIsInstance(self.tag.shape, tuple)

    def test_shape_size(self):
        """Verify shape length is equal to the number of dimensions."""
        self.assertEqual(len(self.tag.shape), 1)

    def test_shape_value_type(self):
        """Shape members must be integers."""
        self.assertIsInstance(self.tag.shape[0], int)

    def test_shape_value(self):
        """Verify correct dimension value."""
        self.assertEqual(self.tag.shape[0], 10)

    def test_index_type(self):
        """Ensure non-integer indices raise an exception."""
        with self.assertRaises(TypeError):
            self.tag['not an int']
            
    def test_index_range(self):
        """Ensure negative and indices beyond the end raise exceptions."""
        for i in [-1, self.tag.shape[0]]:
            with self.assertRaises(IndexError):
                self.tag[i]

    def test_value_type(self):
        """Verify value is a list of correct length."""
        self.assertIsInstance(self.tag.value, list)
        self.assertEqual(len(self.tag.value), self.tag.shape[0])

    def test_invalid_value_type(self):
        """Test setting value to a non-list raises an exception."""
        with self.assertRaises(TypeError):
            self.tag.value = 'not a list'

    def test_invalid_value_size(self):
        """Test setting value with an oversize source raises an exception."""
        x = [0] * (self.tag.shape[0] + 1)
        with self.assertRaises(IndexError):
            self.tag.value = x

    def test_value(self):
        """Test setting and getting list values."""
        for v in [[0] * self.tag.shape[0], range(self.tag.shape[0])]:
            self.value = v
            self.assertEqual(self.value, v)

    def test_element_description(self):
        """Test setting and getting element descriptions."""
        for i in range(self.tag.shape[0]):
            # Test project should begin with no description.
            self.assertIsNone(self.tag[i].description)
            
            new_desc = ' '.join(('element', str(i)))
            self.tag[i].description = new_desc
            self.assertEqual(self.tag[i].description, new_desc)


class TestArray3(Tag, unittest.TestCase):
    """Multidimensional array tests"""
    name = 'array3'
    output_value = ArrayOutputValue()

    def test_shape_size(self):
        """Verify shape length is equal to the number of dimensions."""
        self.assertEqual(len(self.tag.shape), 3)

    def test_shape_values(self):
        """Verify correct dimension values."""
        self.assertEqual(self.tag.shape[0], 2)
        self.assertEqual(self.tag.shape[1], 3)
        self.assertEqual(self.tag.shape[2], 4)

    def test_dim_value(self):
        """Verify values for each dimension are correctly sized lists."""
        value = self.tag.value
        for dim in range(len(self.tag.shape) - 1, -1):
            self.assertIsInstance(value, list)
            self.assertEqual(len(value), self.tag.shape[dim])
            value = value[0]

    def test_dim_description(self):
        """Confirm descriptions are not permitted for whole dimensions."""
        dim = self.tag
        for i in range(len(self.tag.shape) - 1):
            dim = dim[0]
            with self.assertRaises(TypeError):
                dim.description
            with self.assertRaises(TypeError):
                dim.description = 'test'


def setUpModule():
    """Opens the test project."""
    global doc
    doc = l5x.Project('tests/test.L5X')


def tearDownModule():
    """Writes the output project."""
    doc.write('tests/out_tags.L5X')
