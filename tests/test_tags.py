"""
Unittests for tag access.
"""

import ctypes
from tests import fixture
import l5x
import math
import unittest


class Scope(unittest.TestCase):
    """Tests for a tag scope."""
    def setUp(self):
        self.scope = prj.controller.tags

    def test_names(self):
        """Test names attribute returns a non-empty list of strings."""
        self.assertGreater(len(self.scope.names), 0)
        for tag in self.scope.names:
            self.assertIsInstance(tag, str)
            self.assertGreater(len(tag), 0)

    def test_name_index(self):
        """Ensure tags can be indexed by name."""
        for name in self.scope.names:
            self.scope[name]

    def test_name_read_only(self):
        """Verify list of names cannot be directly modified."""
        with self.assertRaises(AttributeError):
            self.scope.names = 'foo'

    def test_invalid_index(self):
        """Verify accessing a nonexistent tag raises an exception."""
        with self.assertRaises(KeyError):
            self.scope['not_a_tag']


class Tag(object):
    """Base class for testing a tag."""
    def setUp(self):
        self.tag = prj.controller.tags[self.name]

    def test_desc(self):
        """Test reading and writing tag's description."""
        desc = 'description'
        self.tag.description = desc
        self.assertEqual(self.tag.description, desc)

    def test_del_desc(self):
        """Test removing a tag's description."""
        self.tag.description = 'description'
        self.tag.description = None
        self.assertIsNone(self.tag.description)

    def test_invalid_desc(self):
        """Ensure non-string types raise an exception."""
        with self.assertRaises(TypeError):
            self.tag.description = 0

    def test_data_type(self):
        """Ensure data_type attribute is a read-only, non-empty string."""
        self.assertIsInstance(self.tag.data_type, str)
        self.assertGreater(len(self.tag.data_type), 0)
        with self.assertRaises(AttributeError):
            self.tag.data_type = 'fail'

    def test_remove_raw_data(self):
        """Ensure setting top-level tag value removes undecorated data."""
        clean = l5x.Project(fixture.INPUT_FILE)
        tag = clean.controller.tags[self.name]
        tag.value = tag.value
        self.assertFalse(self.raw_data_exists(tag))

    def raw_data_exists(self, tag):
        """Checks to see if a tag contans an undecorated data element."""
        exists = False
        for e in tag.child_elements:
            if (e.tagName == 'Data') and (not e.hasAttribute('Format')):
                exists = True
        return exists

    @classmethod
    def tearDownClass(cls):
        """Sets tag's final value for the output project."""
        tag = prj.controller.tags[cls.name]
        tag.description = ' '.join((cls.name, 'description'))
        try:
            output_value = cls.output_value
        except AttributeError:
            pass
        else:
            tag.value = output_value


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

    def test_bit_index_type(self):
        """Verity non-integer bit indices raise an exception."""
        with self.assertRaises(TypeError):
            self.tag['foo']

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
        """Test accessing bit descriptions."""
        for bit in range(self.bits):
            desc = ' '.join((self.name, str(bit), 'description'))
            self.tag[bit].description = desc
            self.assertEqual(self.tag[bit].description, desc)

    def test_bit_value_raw_data(self):
        """Ensure undecorated data is cleared when setting a single bit."""
        clean = l5x.Project(fixture.INPUT_FILE)
        tag = clean.controller.tags[self.name]
        tag[0].value = 0
        self.assertFalse(self.raw_data_exists(tag))


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
        self.tag = prj.controller.tags[owner.name]
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

    def test_shape_read_only(self):
        """Ensure attempting to set shape raises an exception."""
        with self.assertRaises(AttributeError):
            self.tag.shape = 0

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
            new_desc = ' '.join(('element', str(i)))
            self.tag[i].description = new_desc
            self.assertEqual(self.tag[i].description, new_desc)

    def test_element_value_raw_data(self):
        """Ensure setting a single element clears undecorated data."""
        clean = l5x.Project(fixture.INPUT_FILE)
        tag = clean.controller.tags[self.name]
        tag[0].value = tag[0].value
        self.assertFalse(self.raw_data_exists(tag))


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


class Structure(Tag, unittest.TestCase):
    """Structured data tag tests."""
    name = 'timer'
    output_value = {'PRE':-1, 'ACC':-2, 'EN':1, 'TT':1, 'DN':1}

    def test_value_type(self):
        """Verify value is returned as a non-empty dict."""
        self.assertIsInstance(self.tag.value, dict)
        self.assertGreater(len(self.tag.value), 0)

    def test_invalid_value_type(self):
        """Test setting value to a non-dict raises an exception."""
        with self.assertRaises(TypeError):
            self.tag.value = 'not a dict'

    def test_value(self):
        """Test setting and getting dict values."""
        x = {'PRE':42, 'ACC':142, 'EN':1, 'TT':0, 'DN':1}
        self.tag.value = x
        self.assertDictEqual(self.tag.value, x)

    def test_member_names_type(self):
        """Verify keys for value dict are strings."""
        for member in self.tag.value.keys():
            self.assertIsInstance(member, str)

    def test_index_type(self):
        """Verify non-string indices raise an exception."""
        with self.assertRaises(TypeError):
            self.tag[0].value

    def test_invalid_index(self):
        """Verify indices for nonexistent members raise an exception."""
        with self.assertRaises(KeyError):
            self.tag['foo'].value

    def test_indices(self):
        """Test indices of valid members."""
        for member in self.output_value.keys():
            self.tag[member].value

    def test_member_values(self):
        """Test setting and getting member values."""
        for member in self.output_value.keys():
            for x in range(2):
                self.tag[member].value = x
                self.assertEqual(self.tag[member].value, x)

    def test_names(self):
        """Verify names attributes returns an iterable of non-empty strings."""
        self.assertGreater(len(self.tag.names), 0)
        for member in self.tag.names:
            self.assertIsInstance(member, str)
            self.assertGreater(len(member), 0)
        with self.assertRaises(AttributeError):
            self.tag.names = 'fail'

    def test_element_value_raw_data(self):
        """Ensure setting a single member clears undecorated data."""
        clean = l5x.Project(fixture.INPUT_FILE)
        tag = clean.controller.tags[self.name]
        tag['PRE'].value = tag['PRE'].value
        self.assertFalse(self.raw_data_exists(tag))


class ComplexOutputValue(object):
    """Generates the final complex UDT output value."""
    def __get__(self, instance, owner=None):
        self.tag = prj.controller.tags[owner.name]
        return [self.udt(i) for i in range(self.tag.shape[0])]

    def udt(self, index):
        """Builds a value for one UDT element."""
        x = index * 1000
        value = {}
        value['dint_array'] = [i + x for i in
                               range(self.tag[index]['dint_array'].shape[0])]
        value['timer'] = {'PRE':x, 'ACC':x + 1, 'EN':1, 'TT':1, 'DN':1}
        value['counter_array'] = [
            {'PRE':x + (i * 100),
             'ACC':x + (i * 100) + 1,
             'CU':1, 'CD':1, 'DN':1, 'OV':1, 'UN':1}
            for i in range(self.tag[index]['counter_array'].shape[0])]
        value['real'] = 1.0 / float(index + 1)
        return value

        
class Complex(Tag, unittest.TestCase):
    """Tests for a complex data type."""
    name = 'udt'
    output_value = ComplexOutputValue()

    def test_array_member_value_type(self):
        """Check array members yield list values."""
        self.assertIsInstance(self.tag.value, list)
        self.assertIsInstance(self.tag[0]['dint_array'].value, list)

    def test_struct_member_value_type(self):
        """Check UDT members yield dict values."""
        self.assertIsInstance(self.tag[0].value, dict)
        self.assertIsInstance(self.tag[0]['timer'].value, dict)


class DescriptionRemoval(Tag, unittest.TestCase):
    """Tests for deleting comments."""
    name = 'desc'

    def test_desc(self):
        """Override for Tag method so no description is set."""
        pass

    def test_del_desc(self):
        """Test deleting all member comments."""
        member = self.tag['dint_array']
        member.description = None
        for i in range(member.shape[0]):
            member[i].description = None
            for bit in range(len(member[i])):
                member[i][bit].description = None

        self.clear_struct(self.tag['timer'])

        member = self.tag['counter_array']
        member.description = None
        for i in range(member.shape[0]):
            self.clear_struct(member[i])

        self.tag['real'].description = None

    def clear_struct(self, struct):
        """Removes descriptions from a structured data type."""
        struct.description = None
        for member in struct.names:
            struct[member].description = None
            try:
                bits = len(struct[member])
            except TypeError:
                pass
            else:
                for bit in range(bits):
                    struct[member][bit].description = None


class Base(Tag, unittest.TestCase):
    """Tests for base tags."""
    name = 'base'
    attrs = ['producer', 'remote_tag']

    def test_access(self):
        """Confirms getting and setting an attribute raises an exception."""
        for attr in self.attrs:
            with self.assertRaises(TypeError):
                getattr(self.tag, attr)
            with self.assertRaises(TypeError):
                setattr(self.tag, '')

    def test_element_order(self):
        """Ensure Description is the first element."""
        # Force creation of a new description by first removing any
        # existing one.
        self.tag.description = None
        self.tag.description = 'description'

        self.assertEqual(self.tag.child_elements[0].tagName, 'Description')


class Consumed(Tag, unittest.TestCase):
    """Tests for consumed tags."""
    name = 'consumed'
    attrs = ['producer', 'remote_tag']

    def test_get_valid(self):
        """Ensures an attribute's value is a non-empty string."""
        for attr in self.attrs:
            value = getattr(self.tag, attr)
            self.assertIsInstance(value, str)
            self.assertGreater(len(value), 0)

    def test_set_nonstring(self):
        """Attempts to set an attribute to a non-string value."""
        for attr in self.attrs:
            with self.assertRaises(TypeError):
                setattr(self.tag, attr, 0)

    def test_set_empty(self):
        """Attempts to set an attribute to an empty string."""
        for attr in self.attrs:
            with self.assertRaises(ValueError):
                setattr(self.tag, attr, '')

    def test_set_valid(self):
        """Tests setting attributes to legal values."""
        for attr in self.attrs:
            old = getattr(self.tag, attr)
            new = '_'.join(('new', old))
            setattr(self.tag, attr, new)

    def test_element_order(self):
        """Ensure ConsumedInfo element is before a Description."""
        # Force creation of a new description by first removing any
        # existing one.
        self.tag.description = None
        self.tag.description = 'description'

        self.assertEqual(self.tag.child_elements[0].tagName, 'ConsumeInfo')


def setUpModule():
    """Opens the test project."""
    global prj
    prj = fixture.setup()


def tearDownModule():
    """Writes the output project."""
    fixture.teardown(prj)
