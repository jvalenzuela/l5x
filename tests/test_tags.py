"""
Unittests for tag access.
"""

import ctypes
from tests import fixture
from l5x import (dom, tag)
import l5x
import math
import unittest
import xml.dom.minidom
import xml.etree.ElementTree as ElementTree


def create_tag(name, data_type, parent=None, attrs={}, value=None, dim=None):
    """Creates a mock tag object."""
    attrs['Name'] = name
    attrs['DataType'] = data_type
    if dim is not None:
        attrs['Dimensions'] = dim
    tag_element = ElementTree.Element('Tag', attrs)

    if parent is not None:
        parent.append(tag_element)

    # Create a raw Data element.
    ElementTree.SubElement(tag_element, 'Data')

    # Add the decorated Data element with an initial value.
    data = ElementTree.SubElement(tag_element, 'Data', {'Format':'Decorated'})
    if value is None:
        ElementTree.SubElement(data, 'DataValue')
    else:
        data.append(value)

    return l5x.tag.Tag(tag_element, None)


class Scope(unittest.TestCase):
    """Tests for a tag scope."""
    def setUp(self):
        parent = ElementTree.Element('parent')
        tags = ElementTree.SubElement(parent, 'Tags')
        [create_tag(name, 'DINT', tags) for name in ['foo', 'bar', 'baz']]
        self.scope = l5x.tag.Scope(parent, None)

    def test_names(self):
        """Test names attribute returns a non-empty list of strings."""
        self.assertGreater(len(self.scope.tags.names), 0)
        for tag in self.scope.tags.names:
            self.assertIsInstance(tag, str)
            self.assertGreater(len(tag), 0)

    def test_name_index(self):
        """Ensure tags can be indexed by name."""
        for name in self.scope.tags.names:
            self.scope.tags[name]

    def test_name_read_only(self):
        """Verify list of names cannot be directly modified."""
        with self.assertRaises(AttributeError):
            self.scope.tags.names = 'foo'

    def test_invalid_index(self):
        """Verify accessing a nonexistent tag raises an exception."""
        with self.assertRaises(KeyError):
            self.scope.tags['not_a_tag']


class Tag(object):
    """Base class for testing a tag."""
    def setUp(self):
        initial_value = self.initial_value()
        try:
            dim = self.dim
        except AttributeError:
            dim = None
        self.tag = create_tag('test_tag', self.data_type, value=initial_value)

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
        self.tag.value = self.tag.value
        self.assert_no_raw_data_element()

    def assert_no_raw_data_element(self):
        """Confirms any undecorated data element has been removed."""
        data = self.tag.element.findall('Data')
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].attrib['Format'], 'Decorated')

    def get_value_element(self):
        """Finds the element containing the top-level decorated value.

        The tag name will vary depending on data type, however, it will always
        be the only child of the decorated Data element.
        """
        parent = self.tag.element.find("Data[@Format='Decorated']")
        children = parent.findall('*')
        return children[0]


class Data(unittest.TestCase):
    """Unit tests for the base Data class."""
    class DummyType(l5x.tag.Data):
        """Mock subclass; the Data class is never instantiated directly."""
        pass

    def test_array(self):
        """Confirm array data is delegated to an Array object."""
        element = ElementTree.Element('Array', {'Dimensions':'1'})
        data = self.DummyType(element, None)
        self.assertIsInstance(data, l5x.tag.Array)

    def test_array_member(self):
        """Confirm array member data is delegated to an ArrayMember object."""
        element = ElementTree.Element('ArrayMember', {'Dimensions':'1'})
        data = self.DummyType(element, None)
        self.assertIsInstance(data, l5x.tag.ArrayMember)

    def test_name_operand(self):
        """Confirm data identified by Name are separated by dots."""
        e = ElementTree.Element('udt')
        udt = self.DummyType(e, None)

        e = ElementTree.SubElement(udt.element, 'member', {'Name':'foo'})
        member = self.DummyType(e, None, udt)

        e = ElementTree.SubElement(member.element, 'submember', {'Name':'bar'})
        submember = self.DummyType(e, None, member)

        self.assertEqual(submember.operand, '.FOO.BAR')

    def test_index_operand(self):
        """Confirm data identified by Index have no separators."""
        e = ElementTree.Element('array')
        array = self.DummyType(e, None)

        e = ElementTree.SubElement(array.element, 'member', {'Index':'[42]'})
        member = self.DummyType(e, None, array)

        e = ElementTree.SubElement(member.element, 'submember', {'Index':'[0]'})
        submember = self.DummyType(e, None, member)

        self.assertEqual(submember.operand, '[42][0]')


class Integer(Tag):
    """Base class for testing integer data types."""
    def initial_value(self):
        """Creates an initial value element for the mock tag."""
        return ElementTree.Element('DataValue', {'Value':'0'})

    def test_type(self):
        """Verify correct data type string."""
        self.assertEqual(self.tag.data_type, self.data_type)

    def test_length(self):
        """Test len() returns number of bits."""
        self.assertEqual(len(self.tag), self.bits)

    def test_value_read(self):
        """Verify value read returns the attribute converted to an integer."""
        value = 42
        self.set_value(value)
        self.assertEqual(self.tag.value, value)

    def test_value_write(self):
        """Verify new values are properly written to the correct attribute."""
        self.tag.value = 42
        value = self.get_value()
        self.assertEqual(value, 42)

    def test_value_write_type(self):
        """Verify setting the value to a non-integer raises an exception."""
        with self.assertRaises(TypeError):
            self.tag.value = '42'

    def test_value_out_of_range(self):
        """Ensure setting out-of-range values raise an exception."""
        try:
            with self.assertRaises(ValueError):
                self.tag.value = self.value_min - 1
            with self.assertRaises(ValueError):
                self.tag.value = self.value_max + 1

        # Ignore type errors on Python 2.7.x if the out-of-range
        # test value is promoted to long.
        except TypeError:
            pass
                
    def test_value_min(self):
        """Confirm the minimum value is accepted."""
        self.tag.value = self.value_min

    def test_value_max(self):
        """Confirm the maximum value is accepted."""
        self.tag.value = self.value_max

    def test_invalid_bit_indices(self):
        """Verify invalid bit indices raise an exception."""
        with self.assertRaises(IndexError):
            self.tag[-1]
        with self.assertRaises(IndexError):
            self.tag[self.bits]

    def test_bit_index_type(self):
        """Verify non-integer bit indices raise an exception."""
        with self.assertRaises(TypeError):
            self.tag['foo']

    def test_bit_value_read(self):
        """Confirm non-sign bits reflect the current integer value."""
        for bit in range(self.bits - 1):
            # Check setting only the target bit.
            value = 1 << bit
            self.set_value(value)
            for test_bit in range(self.bits):
                if test_bit == bit:
                    test_value = 1
                else:
                    test_value = 0
                self.assertEqual(self.tag[test_bit].value, test_value)

            # Check setting all except the target bit.
            value = ~(1 << bit)
            self.set_value(value)
            for test_bit in range(self.bits):
                if test_bit == bit:
                    test_value = 0
                else:
                    test_value = 1
                self.assertEqual(self.tag[test_bit].value, test_value)

    def test_bit_value_write(self):
        """Confirm writing non-sign bits properly update the integer value."""
        for bit in range(self.bits - 1):
            # Check setting only the target bit.
            self.set_value(0)
            self.tag[bit].value = 1
            value = self.get_value()
            self.assertEqual(value, 1 << bit)

            # Check clearing only the target bit.
            self.set_value(-1)
            self.tag[bit].value = 0
            value = self.get_value()
            self.assertEqual(value, ~(1 << bit))

    def test_sign_bit_read(self):
        """Confirm MSB is treated as the sign when reading a value."""
        sign_bit = self.bits - 1
        min_negative = -(1 << sign_bit)
        self.set_value(min_negative)
        self.assertEqual(self.tag[sign_bit].value, 1)

    def test_sign_bit_write(self):
        """Confirm MSB is treated as the sign bit when writing a value."""
        sign_bit = self.bits - 1
        min_negative = -(1 << sign_bit)
        self.tag[sign_bit].value = 1
        value = self.get_value()
        self.assertEqual(value, min_negative)

    def test_bit_write_type(self):
        """Confirm an exception is raised when setting a bit to a non-integer."""
        with self.assertRaises(TypeError):
            self.tag[0].value = 'foo'

    def test_bit_value_range(self):
        """Ensure bit values other than 0 or 1 raise an exception."""
        with self.assertRaises(ValueError):
            self.tag[0].value = -1
        with self.assertRaises(ValueError):
            self.tag[0].value = 2

    def test_bit_desc_read(self):
        """Confirm reading an existing bit description."""
        for bit in range(self.bits):
            comment_text = "comment for bit {0}".format(bit)
            self.add_bit_description(bit, comment_text)
            self.assertEqual(self.tag[bit].description, comment_text)

    def test_bit_desc_read_none(self):
        """Confirm reading a nonexistent bit description."""
        for bit in range(self.bits):
            self.assertIsNone(self.tag[bit].description)

    def test_bit_desc_read_none_other(self):
        """Confirm reading a nonexistent bit comment when other comments exist."""
        for bit in range(self.bits):
            self.assertIsNone(self.tag[bit].description)

            # Add the comment after checking to create unrelated comments
            # for the next bit.
            comment_text = "comment for bit {0}".format(bit)
            self.add_bit_description(bit, comment_text)

    def test_bit_desc_write_new(self):
        """Confirm creating a new bit description."""
        for bit in range(self.bits):
            comment = "bit {0}".format(bit)
            self.tag[bit].description = comment
            self.assert_bit_description(bit, comment)

    def test_bit_desc_overwrite(self):
        """Confirm overwriting an existing bit description."""
        for bit in range(self.bits):
            old = "old bit {0} comment".format(bit)
            self.add_bit_description(bit, old)
            new = "new bit {0} comment".format(bit)
            self.tag[bit].description = new
            self.assert_bit_description(bit, new)

    def test_bit_desc_del(self):
        """Confirm removal of an existing bit description."""
        for bit in range(self.bits):
            desc = "bit {0} comment".format(bit)
            self.add_bit_description(bit, desc)
            self.tag[bit].description = None
            path = "Comments/Comment[@Operand='.{0}']".format(bit)
            comment = self.tag.element.findall(path)
            self.assertEqual(len(comment), 0)

    def test_bit_value_raw_data(self):
        """Ensure undecorated data is cleared when setting a single bit."""
        self.tag[0].value = 1
        self.assert_no_raw_data_element()

    def get_value(self):
        """Returns the value currently stored in the XML attribute."""
        element = self.get_value_element()
        return int(element.attrib['Value'])

    def set_value(self, value):
        """Updates the value stored in the XML attribute."""
        element = self.get_value_element()
        element.attrib['Value'] = str(value)

    def add_bit_description(self, bit, text):
        """Creates a bit description."""
        comments = self.tag.element.find('Comments')
        if comments is None:
            comments = ElementTree.SubElement(self.tag.element, 'Comments')
        operand = ".{0}".format(bit)
        comment = ElementTree.SubElement(comments, 'Comment',
                                         {'Operand':operand})
        cdata = ElementTree.SubElement(comment, dom.CDATA_TAG)
        cdata.text = text

    def assert_bit_description(self, bit, text):
        """Tests to ensure a description for a specific bit exists."""
        # Confirm a single Comments element under the tag parent.
        comments = self.tag.element.findall('Comments')
        self.assertEqual(len(comments), 1)

        # Confirm a single Comment with matching operand.
        path = "Comment[@Operand='.{0}']".format(bit)
        comment = comments[0].findall(path)
        self.assertEqual(len(comment), 1)

        # Confirm a single CDATA child with matching text.
        cdata = [e for e in comment[0].iter()]
        del cdata[0] # Exclude the Comment parent.
        self.assertEqual(len(cdata), 1)
        self.assertEqual(cdata[0].tag, dom.CDATA_TAG)
        self.assertEqual(cdata[0].text, text)


class TestSINT(Integer, unittest.TestCase):
    data_type = 'SINT'
    bits = 8
    value_min = -128
    value_max = 127


class TestINT(Integer, unittest.TestCase):
    data_type = 'INT'
    bits = 16
    value_min = -32768
    value_max = 32767


class TestDINT(Integer, unittest.TestCase):
    data_type = 'DINT'
    bits = 32
    value_min = -2147483648
    value_max = 2147483647


class TestBOOL(Tag, unittest.TestCase):
    """BOOL type tests."""
    data_type = 'BOOL'

    def initial_value(self):
        """Creates an initial value element for the mock tag."""
        return ElementTree.Element('DataValue', {'Value':'0'})

    def test_value_read(self):
        """Confirm reading the current value."""
        value = self.get_value_element()
        value.attrib['Value'] = '1'
        self.assertEqual(self.tag.value, 1)

    def test_value_write(self):
        """Confirm writing a new value."""
        self.tag.value = 1
        value = self.get_value_element()
        self.assertEqual(int(value.attrib['Value']), 1)

    def test_value_invalid_type(self):
        """Confirm an exception is raised when writing a non-integer value."""
        with self.assertRaises(TypeError):
            self.tag.value = False

    def test_out_of_range_value(self):
        """Test exception when setting values other than 0 or 1."""
        for x in [-1, 2]:
            with self.assertRaises(ValueError):
                self.tag.value = x


class TestREAL(Tag, unittest.TestCase):
    """REAL type tests."""
    data_type = 'REAL'

    def initial_value(self):
        """Creates an initial value element for the mock tag."""
        return ElementTree.Element('DataValue', {'Value':'0.0'})

    def test_value_read(self):
        """Confirm reading the current value."""
        value = self.get_value_element()
        value.attrib['Value'] = str(math.pi)
        self.assertAlmostEqual(self.tag.value, math.pi)

    def test_value_write(self):
        """Confirm writing a new value."""
        self.tag.value = math.e
        value = self.get_value_element()
        self.assertAlmostEqual(float(value.attrib['Value']), math.e)

    def test_value_invalid_type(self):
        """Confirm an exception is raised when writing a non-float value."""
        with self.assertRaises(TypeError):
            self.tag.value = 'not a float'

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


class TestSingleDimensionalArray(Tag, unittest.TestCase):
    """Single-dimensional array tests."""
    data_type = 'DINT'
    dim = '3'

    def initial_value(self):
        """Generates an initial array value element."""
        attr = {'DataType':'DINT',
                'Dimensions':self.dim}
        array = ElementTree.Element('Array', attr)

        for i in range(int(self.dim)):
            attr = {'Index':"[{0}]".format(i),
                    'Value':'0'}
            ElementTree.SubElement(array, 'Element', attr)

        return array

    def test_shape(self):
        """Ensure shape is a tuple with the correct dimensions.."""
        self.assertEqual(self.tag.shape, (int(self.dim),))

    def test_resize_invalid_type(self):
        """Test attempting to resize with a non-tuple raises an exception."""
        with self.assertRaises(TypeError):
            self.tag.shape = 5

    def test_resize_num_dims(self):
        """Test resizing with invalid dimension quantity raises an exception."""
        for shape in [(), (1, 2, 3, 4)]:
            with self.assertRaises(ValueError):
                self.tag.shape = shape

    def test_resize_dim_type(self):
        """Ensure resizing with non-integer dimensions raises an exception."""
        with self.assertRaises(TypeError):
            self.tag.shape = ('foo',)

    def test_resize_dim_range(self):
        """Test resizing with dimensions less than 1 raises an exception."""
        with self.assertRaises(ValueError):
            self.tag.shape = (0,)
            
    def test_index_type(self):
        """Ensure non-integer indices raise an exception."""
        with self.assertRaises(TypeError):
            self.tag['not an int']
            
    def test_index_range(self):
        """Ensure negative and indices beyond the end raise exceptions."""
        for i in [-1, int(self.dim)]:
            with self.assertRaises(IndexError):
                self.tag[i]

    def test_value_read(self):
        """Confirm reading the top-level value returns a list of values."""
        new = [100 + i for i in range(int(self.dim))]
        for i in range(len(new)):
            element = self.get_value_element(i)
            element.attrib['Value'] = str(new[i])
        self.assertEqual(self.tag.value, new)

    def test_element_value_read(self):
        """Confirm reading a single value."""
        for i in range(int(self.dim)):
            value = i + 10
            element = self.get_value_element(i)
            element.attrib['Value'] = str(value)
            self.assertEqual(self.tag[i].value, value)

    def test_value_write(self):
        """Confirm setting a new value to all elements with a list."""
        new = [100 + i for i in range(int(self.dim))]
        self.tag.value = new
        for i in range(len(new)):
            element = self.get_value_element(i)
            value = int(element.attrib['Value'])
            self.assertEqual(value, new[i])

    def test_value_write_short(self):
        """Confirm setting a value to a list with fewer elements starts overwriting at the beginning."""
        new = [100 + i for i in range(int(self.dim) - 1)]
        self.tag.value = new
        for i in range(int(self.dim)):
            element = self.get_value_element(i)
            try:
                value = new[i]
            except IndexError:
                value = 0
            self.assertEqual(value, int(element.attrib['Value']))

    def test_value_write_too_long(self):
        """Confirm an exception is raised when setting the value to a list that is too long."""
        with self.assertRaises(IndexError):
            self.tag.value = [0] * (int(self.dim) + 1)

    def test_element_value_write(self):
        """Confirm writing a single element."""
        for i in range(int(self.dim)):
            new_value = i * 2
            self.tag[i].value = new_value
            element = self.get_value_element(i)
            self.assertEqual(new_value, int(element.attrib['Value']))

    def test_invalid_value_type(self):
        """Test setting value to a non-list raises an exception."""
        with self.assertRaises(TypeError):
            self.tag.value = 'not a list'

    def test_element_description_read(self):
        """Test reading an existing element description."""
        desc = 'some comment'
        self.set_comment(0, desc)
        self.assertEqual(self.tag[0].description, desc)

    def test_element_description_read_none(self):
        """Test reading a nonexistent element description."""
        self.assertIsNone(self.tag[0].description)

    def test_element_description_new(self):
        """Test creating a new element description."""
        self.tag[0].description = 'foo'
        desc = self.get_comment(0)
        self.assertEqual(desc, 'foo')

    def test_element_description_overwrite(self):
        """Test overwriting an existing element description."""
        self.set_comment(0, 'old')
        self.tag[0].description = 'new'
        desc = self.get_comment(0)
        self.assertEqual(desc, 'new')

    def test_element_description_delete(self):
        """Test removing an existing element description."""
        self.set_comment(0, 'spam')
        self.tag[0].description = None
        desc = self.get_comment(0)
        self.assertIsNone(desc)

    def test_element_description_delete_none(self):
        """Test removing a nonexistent element description."""
        self.tag[0].description = None
        desc = self.get_comment(0)
        self.assertIsNone(desc)

    def test_element_value_raw_data(self):
        """Ensure setting a single element clears undecorated data."""
        self.tag[0].value = 0
        self.assert_no_raw_data_element()

    def get_value_element(self, index):
        """Finds the element containing an element value."""
        path = "Data/Array/Element[@Index='[{0}]']".format(index)
        return self.tag.element.find(path)

    def set_comment(self, index, text):
        """Creates a comment for a single element."""
        comments = ElementTree.SubElement(self.tag.element, 'Comments')
        operand = "[{0}]".format(index)
        comment = ElementTree.SubElement(comments, 'Comment',
                                         {'Operand':operand})
        cdata = ElementTree.SubElement(comment, dom.CDATA_TAG)
        cdata.text = text

    def get_comment(self, index):
        """Finds a comment for a single element."""
        path = "Comments/Comment[@Operand='[{0}]']/{1}".format(index,
                                                               dom.CDATA_TAG)
        element = self.tag.element.find(path)
        try:
            return element.text
        except AttributeError:
            return None


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


class ArrayResize(object):
    """Base class for array resizing tests."""
    @classmethod
    def setUpClass(cls):
        cls.tag = prj.controller.tags[cls.name]
        cls.tag.shape = cls.target
        cls.target_strings = [str(s) for s in cls.target]
        cls.target_strings.reverse()

    def test_shape(self):
        """Ensure the tag's shape value is updated."""
        self.assertEqual(self.tag.shape, self.target)

    def test_tag_dimensions_attr(self):
        """Ensure the top-level Tag element's Dimensions attribute is set."""
        attr = self.tag.element.getAttribute('Dimensions')
        dims = ' '.join(self.target_strings)
        self.assertEqual(attr, dims)

    def test_array_dimensions_attr(self):
        """Ensures the Array element's Dimensions attribute is set."""
        attr = self.tag.data.element.getAttribute('Dimensions')
        dims = ','.join(self.target_strings)
        self.assertEqual(attr, dims)

    def test_raw_data_removed(self):
        """Ensure the original raw data array is deleted."""
        for e in self.tag.child_elements:
            if e.tagName == 'Data':
                self.assertTrue(e.hasAttribute('Format'))

    def test_index_order(self):
        """Confirm the correct order of generated indices."""
        indices = self.get_indices()
        self.assertEqual(indices, sorted(indices))

    def test_element_number(self):
        """Confirm the correct number of elements were generated."""
        for i in self.tag.shape:
            try:
                num *= i
            except UnboundLocalError:
                num = i

        self.assertEqual(num, len(self.get_indices()))

    def test_index_range(self):
        """Confirm the generated indices are within the resized shape."""
        for idx in self.get_indices():
            # Reverse the order of dimensions to convert back from the
            # attribute presentation format. Required to match the order
            # of significance used for the array's shape tuple.
            idx = tuple(reversed(idx))

            for dim in range(len(idx)):
                x = idx[dim]
                self.assertGreaterEqual(x, 0)
                self.assertLess(x, self.tag.shape[dim])

    def test_index_length(self):
        """Confirm generated indices have the correct number of dimensions."""
        indices = self.get_indices()
        [self.assertEqual(len(i), len(self.tag.shape)) for i in indices]

    def test_index_unique(self):
        """Confirm all generated indices are unique."""
        s = set()
        for idx in self.get_indices():
            self.assertNotIn(idx, s)
            s.add(idx)
        
    def get_indices(self):
        """Extracts the list of element indices from the array elements.

        Indices are converted into a tuple of integers. Dimension order
        remains the same as the string presentation from the attribute
        value: most-significant dimension stored in the least-significant
        tuple index.
        """
        indices = []
        for e in self.tag.data.child_elements:
            attr = e.getAttribute('Index')[1:-1] # Remove braces.
            indices.append(tuple([int(i) for i in attr.split(',')]))
        return indices


class ArrayResizeSimple(ArrayResize, unittest.TestCase):
    """Tests for resizing an array of simple data types."""
    name = 'array_resize_simple'
    target = (5,)


class ArrayResizeStruct(ArrayResize, unittest.TestCase):
    """Tests to resizing an array of structured data types."""
    name = 'array_resize_struct'
    target = (5, 6, 7)


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

    def test_member_array_resize(self):
        """Ensure member arrays cannot be resized."""
        with self.assertRaises(AttributeError):
            self.tag[0]['dint_array'].shape = (1,)


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


class Consumed(unittest.TestCase):
    """Tests for attributes specific to consumed tags."""
    def setUp(self):
        attrs = {'TagType':'Consumed'}
        self.tag = create_tag('tag_name', 'DINT', attrs=attrs)
        self.consume_info = ElementTree.SubElement(self.tag.element,
                                                   'ConsumeInfo')

    def test_get_producer(self):
        """Confirm producer returns the correct attribute value."""
        self.consume_info.attrib['Producer'] = 'foo'
        self.assertEqual(self.tag.producer, 'foo')

    def test_set_producer(self):
        """Confirm setting the producer alters the correct attribute."""
        self.tag.producer = 'spam'
        self.assertEqual(self.consume_info.attrib['Producer'], 'spam')

    def test_get_remote_tag(self):
        """Confirm remote tag returns the correct attribute value."""
        self.consume_info.attrib['RemoteTag'] = 'bar'
        self.assertEqual(self.tag.remote_tag, 'bar')

    def test_set_remote_tag(self):
        """Confirm setting the remote tag alters the correct attribute."""
        self.tag.remote_tag = 'eggs'
        self.assertEqual(self.consume_info.attrib['RemoteTag'], 'eggs')

    def test_set_nonstring(self):
        """Confirm an exception is raised when setting to a non-string."""
        with self.assertRaises(TypeError):
            self.tag.producer = 0

    def test_set_empty(self):
        """Confirm an exception is raised when setting to an empty string."""
        with self.assertRaises(ValueError):
            self.tag.remote_tag = ''

    def test_not_consumed(self):
        """Confirm access to a base tag raises an exception."""
        self.tag.element.attrib['TagType'] = 'Base'
        with self.assertRaises(TypeError):
            self.tag.producer

    def test_element_order(self):
        """Ensure a Description element is placed after ConsumedInfo."""
        self.tag.description = 'description'
        child_tags = [e.tag for e in self.tag.element.findall('*')]
        self.assertLess(child_tags.index('ConsumeInfo'),
                        child_tags.index('Description'))


class LanguageBase(unittest.TestCase):
    """Base class for tests involving multilanguage comments and descriptions."""
    TARGET_LANGUAGE = 'en-US'

    def setUp(self):
        self.tag = create_tag('tag_name', 'DINT')

    def set_multilanguage(self):
        """Enables multilingual comments."""
        self.tag.lang = self.TARGET_LANGUAGE

    def assert_cdata_content(self, parent, text):
        """
        Verifies a given element contains a single CDATA subelement with a
        matching string. Note, this tests for a CDATA element, not an
        actual CDATA section, as unit tests using this function operate
        using CDATA elements. See CDATA_TAG comments in the dom module
        for details.
        """
        # Confirm the parent element contains a single CDATA subelement.
        children = [e for e in parent.iterfind('*')]
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].tag, dom.CDATA_TAG)

        # Confirm the content of the new CDATA section.
        self.assertEqual(children[0].text, text)

    def assert_no_matching_element(self, path):
        """Verifies a given XPath does not match under the mock tag element."""
        result = self.tag.element.findall(path)
        self.assertEqual(len(result), 0)


class DescriptionLanguage(LanguageBase):
    """Tests for multilanguage descriptions."""
    def test_single_read(self):
        """Confirm reading a description from a single-language project."""
        self.add_description('foo')
        self.assertEqual(self.tag.description, 'foo')

    def test_multi_read(self):
        """
        Confirm reading a description from a multi-language project returns
        only content from the current language.
        """
        self.set_multilanguage()
        self.add_description('pass', self.TARGET_LANGUAGE)
        self.add_description('fail', 'es-AR')
        self.assertEqual(self.tag.description, 'pass')

    def test_single_read_none(self):
        """
        Confirm reading an empty description from a single-language project.
        """
        self.assertIsNone(self.tag.description)

    def test_multi_read_none(self):
        """
        Confirm reading an empty description from a multi-language project.
        """
        self.set_multilanguage()
        self.assertIsNone(self.tag.description)

    def test_multi_read_none_foreign(self):
        """
        Confirm reading an empty description from a multi-language project
        that has descriptions in other languages.
        """
        self.set_multilanguage()
        self.add_description('other', 'es-AR')
        self.assertIsNone(self.tag.description)

    def test_single_new(self):
        """Confirm adding a description to a single-language project."""
        self.tag.description = 'new'
        self.assert_description('new')

    def test_multi_new(self):
        """Confirm adding a description to a multi-language project."""
        self.set_multilanguage()
        self.tag.description = 'new'
        self.assert_localized_description('new', self.TARGET_LANGUAGE)

    def test_multi_new_foreign(self):
        """
        Confirm adding a description to a multi-language project that has
        descriptions in other languages.
        """
        self.set_multilanguage()
        self.add_description('other', 'es-AR')
        self.tag.description = 'new'
        self.assert_localized_description('new', self.TARGET_LANGUAGE)
        self.assert_localized_description('other', 'es-AR')

    def test_single_overwrite(self):
        """
        Confirm overwriting an existing description in a single-language
        project.
        """
        self.add_description('old')
        self.tag.description = 'new'
        self.assert_description('new')

    def test_multi_overwrite(self):
        """
        Confirm overwriting an existing description in a multi-language
        project.
        """
        self.set_multilanguage()
        self.add_description('old', self.TARGET_LANGUAGE)
        self.tag.description = 'new'
        self.assert_localized_description('new', self.TARGET_LANGUAGE)

    def test_multi_overwrite_foreign(self):
        """
        Confirm overwriting an existing description in a multi-language
        project that has descriptions on other languages only affects
        the description in the current language.
        """
        self.set_multilanguage()
        self.add_description('old', self.TARGET_LANGUAGE),
        self.add_description('other', 'es-AR')
        self.tag.description = 'new'
        self.assert_localized_description('new', self.TARGET_LANGUAGE)
        self.assert_localized_description('other', 'es-AR')

    def test_single_delete(self):
        """Confirm removing a description from a single-language project."""
        self.add_description('foo')
        self.tag.description = None
        self.assert_no_matching_element('Description')

    def test_multi_delete(self):
        """Confirm removing a description from a multi-language project."""
        self.set_multilanguage()
        self.add_description('foo', self.TARGET_LANGUAGE)
        self.tag.description = None
        self.assert_no_matching_element('Description')

    def test_multi_delete_foreign(self):
        """
        Confirm removing a description from a multi-language project affects
        only descriptions in the current language.
        """
        self.set_multilanguage()
        self.add_description('foo', self.TARGET_LANGUAGE),
        self.add_description('other', 'es-AR')
        self.tag.description = None

        # Ensure no localized description remains in the current language.
        path = "Description/LocalizedDescription[@Lang='{0}']".format(
            self.TARGET_LANGUAGE)
        self.assert_no_matching_element(path)

        # Ensure descriptions in other languages are unaffected.
        self.assert_localized_description('other', 'es-AR')

    def add_description(self, text, language=None):
        """Adds a description to the mock controller tag."""
        # Find the existing Description element, or create a new one if
        # necessary.
        desc = self.tag.element.find('Description')
        if desc is None:
            desc = ElementTree.SubElement(self.tag.element, 'Description')

        cdata = ElementTree.Element(dom.CDATA_TAG)
        cdata.text = text

        # CDATA text goes directly under the Description element if no
        # language is specified.
        if language is None:
            desc.append(cdata)

        # Otherwise, create a localized element for the given language
        # to contain the CDATA.
        else:
            attr = {'Lang':language}
            local = ElementTree.SubElement(desc, 'LocalizedDescription',
                                           attr)
            local.append(cdata)

    def assert_description(self, text):
        """
        Verifies a single Description element exists under the Tag and
        contains a matching comment.
        """
        desc = self.tag.element.findall('Description')
        self.assertEqual(len(desc), 1)
        self.assert_cdata_content(desc[0], text)

    def assert_localized_description(self, text, language):
        """
        Verifies a single LocalizedDescription element exists under the
        Description element with a language attribute and matching text.
        """
        path = "Description/LocalizedDescription[@Lang='{0}']".format(language)
        local_desc = self.tag.element.findall(path)
        self.assertEqual(len(local_desc), 1)
        self.assert_cdata_content(local_desc[0], text)


class CommentLanguage(LanguageBase):
    """Tests for multilanguage comments."""
    def test_single_read(self):
        """Confirm reading a comment from a single-language project."""
        self.add_comment('.0', 'foo')
        self.assertEqual(self.tag[0].description, 'foo')

    def test_multi_read(self):
        """
        Confirm reading a comment from a multi-language project returns
        only content from the current language.
        """
        self.set_multilanguage()
        self.add_comment('.0', 'pass', self.TARGET_LANGUAGE),
        self.add_comment('.0', 'fail', 'zh-CN')
        self.assertEqual(self.tag[0].description, 'pass')

    def test_single_read_none(self):
        """
        Confirm reading a nonexistent comment from a single-language project.
        """
        self.assertIsNone(self.tag[0].description)

    def test_multi_read_none_foreign(self):
        """
        Confirm reading a nonexistent comment from a multi-language project
        that has comments in other languages.
        """
        self.set_multilanguage()
        self.add_comment('.0', 'other', 'zh-CN')
        self.assertIsNone(self.tag[0].description)

    def test_single_new(self):
        """Confirm adding a comment to a single-language project."""
        self.tag[0].description = 'new'
        self.assert_comment('.0', 'new')

    def test_multi_new(self):
        """Confirm adding a comment to a multi-language project."""
        self.set_multilanguage()
        self.tag[0].description = 'new'
        self.assert_localized_comment('.0', 'new', self.TARGET_LANGUAGE)

    def test_multi_new_foreign(self):
        """
        Confirm adding a comment to a multi-language project that has
        comments in other languages.
        """
        self.set_multilanguage()
        self.add_comment('.0', 'other', 'zh-CN')
        self.tag[0].description = 'new'
        self.assert_localized_comment('.0', 'new', self.TARGET_LANGUAGE)
        self.assert_localized_comment('.0', 'other', 'zh-CN')

    def test_single_overwrite(self):
        """
        Confirm overwriting an existing comment in a single-language
        project.
        """
        self.add_comment('.0', 'old')
        self.tag[0].description = 'new'
        self.assert_comment('.0', 'new')

    def test_multi_overwrite(self):
        """
        Confirm overwriting an existing comment in a multi-language
        project.
        """
        self.set_multilanguage()
        self.add_comment('.0', 'old', self.TARGET_LANGUAGE)
        self.tag[0].description = 'new'
        self.assert_localized_comment('.0', 'new', self.TARGET_LANGUAGE)

    def test_multi_overwrite_foreign(self):
        """
        Confirm overwriting an existing comment in a multi-language
        project that has comments on other languages only affects
        the comment in the current language.
        """
        self.set_multilanguage()
        self.add_comment('.0', 'old', self.TARGET_LANGUAGE)
        self.add_comment('.0', 'other', 'zh-CN')
        self.tag[0].description = 'new'
        self.assert_localized_comment('.0', 'new', self.TARGET_LANGUAGE)
        self.assert_localized_comment('.0', 'other', 'zh-CN')

    def test_single_delete(self):
        """Confirm removing a comment from a single-language project."""
        self.add_comment('.0', 'foo')
        self.tag[0].description = None
        self.assert_no_matching_element('Comments')

    def test_single_delete_other_operand(self):
        """
        Confirm removing a comment from a single-language project
        does not affect comments for other operands.
        """
        self.add_comment('.0', 'foo')
        self.add_comment('.1', 'bar')
        self.tag[0].description = None

        # Confirm the target comment was removed.
        self.assert_no_matching_element("Comments/Comment[@Operand='.0']")

        # Confirm the unaffected comment remains.
        self.assert_comment('.1', 'bar')

    def test_single_delete_last(self):
        """
        Confirm removing the last comment in a single-language project
        also removes the overall Comments parent element.
        """
        self.add_comment('.0', 'foo')
        self.add_comment('.1', 'bar')
        self.tag[0].description = None
        self.tag[1].description = None
        self.assert_no_matching_element('Comments')

    def test_multi_delete(self):
        """Confirm removing a comment from a multi-language project."""
        self.set_multilanguage()
        self.add_comment('.0', 'foo', self.TARGET_LANGUAGE)
        self.tag[0].description = None
        self.assert_no_matching_element('Comments')

    def test_multi_delete_other_operand(self):
        """
        Confirm removing a comment from a multi-language project
        does not affect comments for other operands.
        """
        self.set_multilanguage()
        self.add_comment('.0', 'foo', self.TARGET_LANGUAGE)
        self.add_comment('.1', 'bar', self.TARGET_LANGUAGE)
        self.tag[0].description = None

        # Confirm the target comment was removed.
        path = "Comments/Comment[@Operand='.0']" \
               "/LocalizedComment[@Lang='{0}']".format(self.TARGET_LANGUAGE)
        self.assert_no_matching_element(path)

        # Confirm the unaffected comment remains.
        self.assert_localized_comment('.1', 'bar', self.TARGET_LANGUAGE)

    def test_multi_delete_last(self):
        """
        Confirm removing the last comment in a multi-language project
        also removes the overall Comments parent element.
        """
        self.set_multilanguage()
        self.add_comment('.0', 'foo', self.TARGET_LANGUAGE)
        self.add_comment('.1', 'bar', self.TARGET_LANGUAGE)
        self.tag[0].description = None
        self.tag[1].description = None
        self.assert_no_matching_element('Comments')

    def test_multi_delete_foreign(self):
        """
        Confirm removing a comment from a multi-language project affects
        only comments in the current language.
        """
        self.set_multilanguage()
        self.add_comment('.0', 'foo', self.TARGET_LANGUAGE)
        self.add_comment('.0', 'bar', 'zh-CN')
        self.tag[0].description = None
        self.assert_localized_comment('.0', 'bar', 'zh-CN')

    def add_comment(self, operand, text, language=None):
        """Creates a comment assigned to a given operand."""
        # Locate the Comments element, creating one if necessary.
        comments = self.tag.element.find('Comments')
        if comments is None:
            comments = ElementTree.SubElement(self.tag.element, 'Comments')

        # Find the Comment element with the matching operand, or
        # create a new one if needed.
        path = "Comment[@Operand='{0}']".format(operand)
        comment = comments.find(path)
        if comment is None:
            attr = {'Operand':operand}
            comment = ElementTree.SubElement(comments, 'Comment', attr)

        cdata = ElementTree.Element(dom.CDATA_TAG)
        cdata.text = text

        # Put the CDATA directly under the Comment element for single-language
        # projects.
        if language is None:
            comment.append(cdata)

        # Create a localized comment for multi-language projects.
        else:
            attr = {'Lang':language}
            localized = ElementTree.SubElement(comment, 'LocalizedComment',
                                               attr)
            localized.append(cdata)

    def assert_comment(self, operand, text):
        """
        Verifies a single Comment element exists under the Comments parent
        with a given operand attribute and text content.
        """
        comment = self.get_comment(operand)
        self.assert_cdata_content(comment, text)

    def assert_localized_comment(self, operand, text, language):
        """
        Verifies a single LocalizedComment element exists under the Comments
        element with a language attribute and matching text.
        """
        comment = self.get_comment(operand)
        path = "LocalizedComment[@Lang='{0}']".format(language)
        localized = comment.findall(path)
        self.assertEqual(len(localized), 1)
        self.assert_cdata_content(localized[0], text)

    def get_comment(self, operand):
        """Finds a Comment element with a matching operand attribute."""
        path = "Comments/Comment[@Operand='{0}']".format(operand)
        comment = self.tag.element.findall(path)
        self.assertEqual(len(comment), 1)
        return comment[0]
