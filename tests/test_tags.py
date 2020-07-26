"""
Unittests for tag access.
"""

import copy
import ctypes
from tests import fixture
from l5x import (dom, tag)
import itertools
import l5x
import math
import unittest
import xml.etree.ElementTree as ElementTree


class Scope(unittest.TestCase):
    """Tests for a tag scope."""
    def setUp(self):
        e = fixture.parse_xml("""<Program Name="MainProgram" TestEdits="false" MainRoutineName="MainRoutine" Disabled="false">
<Tags>
<Tag Name="bar" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>
<Tag Name="baz" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>
<Tag Name="foo" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>
</Tags>
<Routines>
<Routine Name="MainRoutine" Type="RLL"/>
</Routines>
</Program>""")
        self.scope = l5x.tag.Scope(e, None)

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
        e = fixture.parse_xml(self.src_xml)
        self.tag = l5x.tag.Tag(e, None)

        # Initialize a fresh copy of the source XML value, if available.
        try:
            self.src_value = copy.deepcopy(self.xml_value)
        except AttributeError:
            pass

    def test_invalid_desc(self):
        """Ensure non-string types raise an exception."""
        with self.assertRaises(TypeError):
            self.tag.description = 0

    def test_data_type_read(self):
        """Confirm reading the data type returns the correct attribute value."""
        self.assertEqual(self.tag.data_type,
                         self.tag.element.attrib['DataType'])

    def test_data_type_write(self):
        """Confirm an exception is raised when changing the data type."""
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
        element = fixture.parse_xml("""<Array DataType="DINT" Dimensions="1" Radix="Decimal">
<Element Index="[0]" Value="0"/>
</Array>""")
        data = self.DummyType(element, None)
        self.assertIsInstance(data, l5x.tag.Array)

    def test_array_member(self):
        """Confirm array member data is delegated to an ArrayMember object."""
        element = fixture.parse_xml("""<ArrayMember Name="dint_array" DataType="DINT" Dimensions="1" Radix="Decimal">
<Element Index="[0]" Value="0"/>
</ArrayMember>""")
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
    src_xml = """<Tag Name="sint" TagType="Base" DataType="SINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00</Data>
<Data Format="Decorated">
<DataValue DataType="SINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>"""

    xml_value = 0
    bits = 8
    value_min = -128
    value_max = 127


class TestINT(Integer, unittest.TestCase):
    src_xml = """<Tag Name="int" TagType="Base" DataType="INT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00</Data>
<Data Format="Decorated">
<DataValue DataType="INT" Radix="Decimal" Value="0"/>
</Data>
</Tag>"""

    xml_value = 0
    bits = 16
    value_min = -32768
    value_max = 32767


class TestDINT(Integer, unittest.TestCase):
    src_xml = """<Tag Name="dint" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>"""

    xml_value = 0
    bits = 32
    value_min = -2147483648
    value_max = 2147483647


class TestBOOL(Tag, unittest.TestCase):
    """BOOL type tests."""
    src_xml = """<Tag Name="bool" TagType="Base" DataType="BOOL" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00</Data>
<Data Format="Decorated">
<DataValue DataType="BOOL" Radix="Decimal" Value="0"/>
</Data>
</Tag>"""

    xml_value = 0

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
    src_xml = """<Tag Name="real" TagType="Base" DataType="REAL" Radix="Float" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="REAL" Radix="Float" Value="0.0"/>
</Data>
</Tag>"""

    xml_value = 0.0

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


class TestSingleDimensionalArray(Tag, unittest.TestCase):
    """Single-dimensional array tests."""
    src_xml = """<Tag Name="array" TagType="Base" DataType="DINT" Dimensions="3" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00 00 00 00 00 00 00 00 00</Data>
<Data Format="Decorated">
<Array DataType="DINT" Dimensions="3" Radix="Decimal">
<Element Index="[0]" Value="0"/>
<Element Index="[1]" Value="0"/>
<Element Index="[2]" Value="0"/>
</Array>
</Data>
</Tag>"""

    xml_value = [0, 0, 0]

    def test_shape(self):
        """Ensure shape is a tuple with the correct dimensions.."""
        self.assertEqual(self.tag.shape, (3,))
            
    def test_index_type(self):
        """Ensure non-integer indices raise an exception."""
        with self.assertRaises(TypeError):
            self.tag['not an int']
            
    def test_index_range(self):
        """Ensure negative and indices beyond the end raise exceptions."""
        for i in [-1, self.tag.shape[0]]:
            with self.assertRaises(IndexError):
                self.tag[i]

    def test_value_read(self):
        """Confirm reading the top-level value returns a list of values."""
        new = [100 + i for i in range(self.tag.shape[0])]
        for i in range(len(new)):
            element = self.get_value_element(i)
            element.attrib['Value'] = str(new[i])
        self.assertEqual(self.tag.value, new)

    def test_element_value_read(self):
        """Confirm reading a single value."""
        for i in range(self.tag.shape[0]):
            value = i + 10
            element = self.get_value_element(i)
            element.attrib['Value'] = str(value)
            self.assertEqual(self.tag[i].value, value)

    def test_value_write(self):
        """Confirm setting a new value to all elements with a list."""
        new = [100 + i for i in range(self.tag.shape[0])]
        self.tag.value = new
        for i in range(len(new)):
            element = self.get_value_element(i)
            value = int(element.attrib['Value'])
            self.assertEqual(value, new[i])

    def test_value_write_short(self):
        """Confirm setting a value to a list with fewer elements starts overwriting at the beginning."""
        new = [100 + i for i in range(self.tag.shape[0] - 1)]
        self.tag.value = new
        for i in range(self.tag.shape[0]):
            element = self.get_value_element(i)
            try:
                value = new[i]
            except IndexError:
                value = 0
            self.assertEqual(value, int(element.attrib['Value']))

    def test_value_write_too_long(self):
        """Confirm an exception is raised when setting the value to a list that is too long."""
        with self.assertRaises(IndexError):
            self.tag.value = [0] * (self.tag.shape[0] + 1)

    def test_element_value_write(self):
        """Confirm writing a single element."""
        for i in range(self.tag.shape[0]):
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


class TestMultiDimensionalArray(Tag, unittest.TestCase):
    """Multi-dimensional array tests"""
    src_xml = """<Tag Name="array" TagType="Base" DataType="DINT" Dimensions="2 3 4" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>01 00 00 00 02 00 00 00 03 00 00 00 04 00 00 00 
05 00 00 00 06 00 00 00 07 00 00 00 08 00 00 00 
09 00 00 00 0A 00 00 00 0B 00 00 00 0C 00 00 00 
0D 00 00 00 0E 00 00 00 0F 00 00 00 10 00 00 00 
11 00 00 00 12 00 00 00 13 00 00 00 14 00 00 00 
15 00 00 00 16 00 00 00 17 00 00 00 18 00 00 00</Data>
<Data Format="Decorated">
<Array DataType="DINT" Dimensions="2,3,4" Radix="Decimal">
<Element Index="[0,0,0]" Value="1"/>
<Element Index="[0,0,1]" Value="2"/>
<Element Index="[0,0,2]" Value="3"/>
<Element Index="[0,0,3]" Value="4"/>
<Element Index="[0,1,0]" Value="5"/>
<Element Index="[0,1,1]" Value="6"/>
<Element Index="[0,1,2]" Value="7"/>
<Element Index="[0,1,3]" Value="8"/>
<Element Index="[0,2,0]" Value="9"/>
<Element Index="[0,2,1]" Value="10"/>
<Element Index="[0,2,2]" Value="11"/>
<Element Index="[0,2,3]" Value="12"/>
<Element Index="[1,0,0]" Value="13"/>
<Element Index="[1,0,1]" Value="14"/>
<Element Index="[1,0,2]" Value="15"/>
<Element Index="[1,0,3]" Value="16"/>
<Element Index="[1,1,0]" Value="17"/>
<Element Index="[1,1,1]" Value="18"/>
<Element Index="[1,1,2]" Value="19"/>
<Element Index="[1,1,3]" Value="20"/>
<Element Index="[1,2,0]" Value="21"/>
<Element Index="[1,2,1]" Value="22"/>
<Element Index="[1,2,2]" Value="23"/>
<Element Index="[1,2,3]" Value="24"/>
</Array>
</Data>
</Tag>"""

    xml_value = [
        [
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 11, 12]
        ],
        [
            [13, 14, 15, 16],
            [17, 18, 19, 20],
            [21, 22, 23, 24]
        ]
    ]

    def test_shape_values(self):
        """Verify correct dimension values."""
        self.assertEqual(self.tag.shape[0], len(self.src_value[0][0]))
        self.assertEqual(self.tag.shape[1], len(self.src_value[0]))
        self.assertEqual(self.tag.shape[2], len(self.src_value))

    def test_value_read(self):
        """Verify reading values for each dimension."""
        self.assertEqual(self.tag.value, self.src_value)

        for i in range(len(self.tag.value)):
            self.assertEqual(self.tag.value[i], self.src_value[i])

            for j in range(len(self.tag.value[i])):
                self.assertEqual(self.tag.value[i][j], self.src_value[i][j])

    def test_value_write_single(self):
        """Verify writing a single element value."""
        self.src_value[1][2][3] = 123
        self.tag[1][2][3].value = 123
        self.assert_element_values()

    def test_value_write_subarray(self):
        """Verify writing a subarray value."""
        self.src_value[0][0] = [1000, 1001, 1002, 1003]
        self.tag[0][0].value = [1000, 1001, 1002, 1003]
        self.assert_element_values()

    def test_value_write_all(self):
        """Verify writing a nested list to the top-level value."""
        new_values = [
            [
                [-1, -2, -3, -4],
                [-5, -6, -7, -8],
                [-9, -10, -11, -12]
            ],
            [
                [-13, -14, -15, -16],
                [-17, -18, -19, -20],
                [-21, -22, -23, -24]
            ]
        ]
        self.src_value = new_values
        self.tag.value = new_values
        self.assert_element_values()

    def assert_element_values(self):
        """Confirms all element values match the source array."""
        # Iterate though all the source array values and confirm a
        # matching XML element value.
        indices = [range(self.tag.shape[x]) for x in range(len(self.tag.shape))]
        indices.reverse()
        for subscript in itertools.product(*indices):
            # Acquire the value stored in the XML attribute.
            index = "[{0}]".format(','.join([str(i) for i in subscript]))
            element = self.tag.element.find(
                'Data/Array/*[@Index="{0}"]'.format(index))
            xml_value = int(element.attrib['Value'])

            # Descend through the source array to select the single value
            # for the given subscript.
            src_value = self.src_value
            for i in subscript:
                src_value = src_value[i]

            self.assertEqual(xml_value, src_value)

        # Iterate through all the XML value elements and confirm a
        # matching source array value.
        for element in self.tag.element.findall('Data/Array/*'):
            index = [int(x) for x in element.attrib['Index'][1:-1].split(',')]
            xml_value = int(element.attrib['Value'])

            # Descend through the source array to select the single value
            # for the given index.
            src_value = self.src_value
            for i in index:
                src_value = src_value[i]

            self.assertEqual(xml_value, src_value)

    def test_subarray_description(self):
        """Confirm descriptions are not permitted for subarrays."""
        ar = self.tag
        for i in range(len(self.tag.shape) - 1):
            ar = ar[0]
            with self.assertRaises(TypeError):
                ar.description
            with self.assertRaises(TypeError):
                ar.description = 'test'


class ArrayResize(Tag):
    """Base class for array resizing tests."""
    def test_shape(self):
        """Ensure the tag's shape value is updated."""
        self.resize()
        self.assertEqual(self.tag.shape, self.dim)

    def test_tag_dimensions_attr(self):
        """Ensure the top-level Tag element's Dimensions attribute is set."""
        self.resize()
        dims = ' '.join(reversed([str(x) for x in self.dim]))
        self.assertEqual(dims, self.tag.element.attrib['Dimensions'])

    def test_array_dimensions_attr(self):
        """Ensures the Array element's Dimensions attribute is set."""
        self.resize()
        dims = ','.join(reversed([str(x) for x in self.dim]))
        array = self.tag.element.find('Data/Array')
        self.assertEqual(dims, array.attrib['Dimensions'])

    def test_raw_data_removed(self):
        """Ensure the original raw data array is deleted."""
        self.resize()
        self.assert_no_raw_data_element()

    def test_indices(self):
        """Confirm element indices match the new shape."""
        self.resize()

        # Get indices from all the XML elements.
        array = self.tag.element.find('Data/Array')
        xml_idx = set([e.attrib['Index'] for e in array])

        # Create indices from the expected dimensions.
        ranges = [range(self.dim[i]) for i in range(len(self.dim))]
        ranges.reverse()
        new_idx = set()
        for idx in itertools.product(*ranges):
            new_idx.add("[{0}]".format(','.join([str(x) for x in idx])))

        self.assertEqual(xml_idx, new_idx)


class ArrayResizeAddDimension(ArrayResize, unittest.TestCase):
    """Tests for resizing an array by adding a dimension."""
    src_xml = """<Tag Name="array" TagType="Base" DataType="DINT" Dimensions="2" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00 01 00 00 00</Data>
<Data Format="Decorated">
<Array DataType="DINT" Dimensions="2" Radix="Decimal">
<Element Index="[0]" Value="0"/>
<Element Index="[1]" Value="1"/>
</Array>
</Data>
</Tag>"""

    xml_value = [0, 1]

    def resize(self):
        """Adds a new dimension."""
        self.dim = (3, 4)
        self.tag.shape = self.dim


class ArrayResizeRemoveDimension(ArrayResize, unittest.TestCase):
    """Tests for resizing an array by removing a dimension."""
    src_xml = """<Tag Name="array" TagType="Base" DataType="DINT" Dimensions="3 2" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00 01 00 00 00 02 00 00 00 03 00 00 00 
04 00 00 00 05 00 00 00</Data>
<Data Format="Decorated">
<Array DataType="DINT" Dimensions="3,2" Radix="Decimal">
<Element Index="[0,0]" Value="0"/>
<Element Index="[0,1]" Value="1"/>
<Element Index="[1,0]" Value="2"/>
<Element Index="[1,1]" Value="3"/>
<Element Index="[2,0]" Value="4"/>
<Element Index="[2,1]" Value="5"/>
</Array>
</Data>
</Tag>"""

    xml_value = [
        [0, 1],
        [2, 3],
        [4, 5]
    ]

    def resize(self):
        """Removes a dimension."""
        self.dim = (2,)
        self.tag.shape = self.dim


class ArrayResizeEnlarge(ArrayResize, unittest.TestCase):
    """Tests for resizing an array by enlarging a dimension."""
    src_xml = """<Tag Name="array" TagType="Base" DataType="DINT" Dimensions="3 2" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00 01 00 00 00 02 00 00 00 03 00 00 00 
04 00 00 00 05 00 00 00</Data>
<Data Format="Decorated">
<Array DataType="DINT" Dimensions="3,2" Radix="Decimal">
<Element Index="[0,0]" Value="0"/>
<Element Index="[0,1]" Value="1"/>
<Element Index="[1,0]" Value="2"/>
<Element Index="[1,1]" Value="3"/>
<Element Index="[2,0]" Value="4"/>
<Element Index="[2,1]" Value="5"/>
</Array>
</Data>
</Tag>"""

    xml_value = [
        [0, 1],
        [2, 3],
        [4, 5]
    ]

    def resize(self):
        """Enlarges a dimension."""
        self.dim = (2, 4)
        self.tag.shape = self.dim


class ArrayResizeReduce(ArrayResize, unittest.TestCase):
    """Tests for resizing an array by shrinking a dimension."""
    src_xml = """<Tag Name="array" TagType="Base" DataType="DINT" Dimensions="4 2" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00 01 00 00 00 02 00 00 00 03 00 00 00 
04 00 00 00 05 00 00 00 06 00 00 00 07 00 00 00</Data>
<Data Format="Decorated">
<Array DataType="DINT" Dimensions="4,2" Radix="Decimal">
<Element Index="[0,0]" Value="0"/>
<Element Index="[0,1]" Value="1"/>
<Element Index="[1,0]" Value="2"/>
<Element Index="[1,1]" Value="3"/>
<Element Index="[2,0]" Value="4"/>
<Element Index="[2,1]" Value="5"/>
<Element Index="[3,0]" Value="6"/>
<Element Index="[3,1]" Value="7"/>
</Array>
</Data>
</Tag>"""

    xml_value = [
        [0, 1],
        [2, 3],
        [4, 5],
        [6, 7]
    ]

    def resize(self):
        """Shrinks a dimension."""
        self.dim = (2, 3)
        self.tag.shape = self.dim


class ArrayResizeInvalid(Tag, unittest.TestCase):
    """Tests for illegal array resizing."""
    src_xml = """<Tag Name="array" TagType="Base" DataType="DINT" Dimensions="3" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>01 00 00 00 02 00 00 00 03 00 00 00</Data>
<Data Format="Decorated">
<Array DataType="DINT" Dimensions="3" Radix="Decimal">
<Element Index="[0]" Value="1"/>
<Element Index="[1]" Value="2"/>
<Element Index="[2]" Value="3"/>
</Array>
</Data>
</Tag>"""

    xml_value = [1, 2, 3]

    def test_too_many_dimensions(self):
        """Confirm an exception is raised for more than 3 dimensions."""
        with self.assertRaises(ValueError):
            self.tag.shape = (1, 2, 3, 4)

    def test_zero_dimensions(self):
        """Confirm an exception is raised for no dimensions."""
        with self.assertRaises(ValueError):
            self.tag.shape = ()

    def test_non_tuple(self):
        """Confirm an exception is raised for a non-tuple shape."""
        with self.assertRaises(TypeError):
            self.tag.shape = 42

    def test_negative_size(self):
        """Confirm an exception is raised for a negative dimension."""
        with self.assertRaises(ValueError):
            self.tag.shape = (-1,)

    def test_zero_size(self):
        """Confirm an exception is raised for a dimension of zero."""
        with self.assertRaises(ValueError):
            self.tag.shape = (0,)

    def test_non_integer(self):
        """Confirm an exception is raised for a non-integer dimension."""
        with self.assertRaises(TypeError):
            self.tag.shape = (5.0,)


class Structure(Tag, unittest.TestCase):
    """Structured data tag tests."""
    src_xml = """<Tag Name="timer" TagType="Base" DataType="TIMER" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 E0 FF FF FF FF FE FF FF FF</Data>
<Data Format="Decorated">
<Structure DataType="TIMER">
<DataValueMember Name="PRE" DataType="DINT" Radix="Decimal" Value="-1"/>
<DataValueMember Name="ACC" DataType="DINT" Radix="Decimal" Value="-2"/>
<DataValueMember Name="EN" DataType="BOOL" Value="1"/>
<DataValueMember Name="TT" DataType="BOOL" Value="1"/>
<DataValueMember Name="DN" DataType="BOOL" Value="1"/>
</Structure>
</Data>
</Tag>"""

    xml_value = {
        'PRE':-1,
        'ACC':-2,
        'EN':1,
        'TT':1,
        'DN':1
    }

    def test_invalid_value_type(self):
        """Test setting value to a non-dict raises an exception."""
        with self.assertRaises(TypeError):
            self.tag.value = 'not a dict'

    def test_value_read(self):
        """Confirm reading the top-level value returns a correct dict."""
        self.assertDictEqual(self.tag.value, self.src_value)

    def test_value_write(self):
        """Confirm writing a dict to the top-level value.."""
        self.src_value = {'PRE':42, 'ACC':142, 'EN':0, 'TT':0, 'DN':0}
        self.tag.value = self.src_value
        self.assert_member_values()

    def test_value_write_partial(self):
        """Confirm writing a partial dict to the top-level value."""
        new_values = {'PRE':-100}
        self.tag.value = new_values
        self.src_value.update(new_values)
        self.assert_member_values()

    def test_nonstring_index(self):
        """Verify non-string indices raise an exception."""
        with self.assertRaises(TypeError):
            self.tag[0].value

    def test_invalid_index(self):
        """Verify indices for nonexistent members raise an exception."""
        with self.assertRaises(KeyError):
            self.tag['foo'].value

    def test_member_value_read(self):
        """Test reading individual member values."""
        for name in self.src_value:
            self.assertEqual(self.tag[name].value, self.src_value[name])

    def test_member_value_write(self):
        """Test writing individual member values."""
        new_values = {
            'PRE':200,
            'ACC':300,
            'EN':0,
            'TT':0,
            'DN':0
        }

        for name in self.src_value:
            self.tag[name].value = new_values[name]
            self.src_value[name] = new_values[name]
            self.assert_member_values()

    def test_names_read(self):
        """Confirm the names attributes contains all members."""
        src_names = set(self.src_value.keys())
        tag_names = set(self.tag.names)
        self.assertEqual(src_names, tag_names)

    def test_names_write(self):
        """
        Confirm an exception is raised when attempting to write to the
        names attribute.
        """
        with self.assertRaises(AttributeError):
            self.tag.names = 'fail'

    def test_write_clear_raw_data(self):
        """
        Confirm writing a dict to the top-level value clears undecorated data.
        """
        self.tag.value = self.src_value
        self.assert_no_raw_data_element()

    def test_member_write_clear_raw_data(self):
        """Ensure setting a single member clears undecorated data."""
        self.tag['PRE'].value = 0
        self.assert_no_raw_data_element()

    def assert_member_values(self):
        """Confirms the value of all data members match the source dict."""
        st = self.tag.element.find('Data/Structure')

        # Confirm all XML values match the source dict.
        for e in st:
            value = int(e.attrib['Value'])
            name = e.attrib['Name']
            self.assertEqual(self.src_value[name], value)

        # Confirm all source dict members match the XML values.
        for name in self.src_value:
            e = st.find('*[@Name="{0}"]'.format(name))
            value = int(e.attrib['Value'])
            self.assertEqual(self.src_value[name], value)


class Compound(Tag, unittest.TestCase):
    """Tests for a data types containing nested arrays and structures."""
    src_xml = """<Tag Name="udt" TagType="Base" DataType="udt" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00</Data>
<Data Format="Decorated">
<Structure DataType="udt">
<ArrayMember Name="dint_array" DataType="DINT" Dimensions="10" Radix="Decimal">
<Element Index="[0]" Value="0"/>
<Element Index="[1]" Value="0"/>
<Element Index="[2]" Value="0"/>
<Element Index="[3]" Value="0"/>
<Element Index="[4]" Value="0"/>
<Element Index="[5]" Value="0"/>
<Element Index="[6]" Value="0"/>
<Element Index="[7]" Value="0"/>
<Element Index="[8]" Value="0"/>
<Element Index="[9]" Value="0"/>
</ArrayMember>
</Structure>
</Data>
</Tag>"""

    def test_member_array_resize(self):
        """Ensure member arrays cannot be resized."""
        with self.assertRaises(AttributeError):
            self.tag['dint_array'].shape = (1,)


class Base(unittest.TestCase):
    """Tests for base, i.e. not produced or consumed, tags."""
    def setUp(self):
        """Creates a mock base tag."""
        e = fixture.parse_xml("""<Tag Name="dint" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.tag = l5x.tag.Tag(e, None)

    def test_producer_read(self):
        """Confirm reading the producer attribute raises an exception."""
        with self.assertRaises(TypeError):
            self.tag.producer

    def test_producer_write(self):
        """Confirm writing the producer attribute raises an exception."""
        with self.assertRaises(TypeError):
            self.tag.producer = 'foo'

    def test_remote_tag_read(self):
        """Confirm reading the remote tag attribute raises an exception."""
        with self.assertRaises(TypeError):
            self.tag.remote_tag

    def test_remote_tag_write(self):
        """Confirm writing the remote tag attribute raises an exception."""
        with self.assertRaises(TypeError):
            self.tag.remote_tag = 'foo'

    def test_description_element_order(self):
        """Ensure a description is created as tag element's first child."""
        self.tag.description = 'description'
        first_child = self.tag.element.find('*')
        self.assertEqual(first_child.tag, 'Description')


class Consumed(unittest.TestCase):
    """Tests for attributes specific to consumed tags."""
    def setUp(self):
        e = fixture.parse_xml("""<Tag Name="dint" TagType="Consumed" DataType="DINT" Radix="Decimal" ExternalAccess="Read/Write">
<ConsumeInfo Producer="producer" RemoteTag="source_tag" RemoteInstance="0" RPI="20"/>
<Data>00 00 00 00</Data>
<ForceData>00 00 00 00 00 00 00 00 00 00 00 00</ForceData>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.tag = l5x.tag.Tag(e, None)

    def test_get_producer(self):
        """Confirm producer returns the correct attribute value."""
        self.assertEqual(self.tag.producer, 'producer')

    def test_set_producer(self):
        """Confirm setting the producer alters the correct attribute."""
        self.tag.producer = 'spam'
        consume_info = self.tag.element.find('ConsumeInfo')
        self.assertEqual(consume_info.attrib['Producer'], 'spam')

    def test_get_remote_tag(self):
        """Confirm remote tag returns the correct attribute value."""
        self.assertEqual(self.tag.remote_tag, 'source_tag')

    def test_set_remote_tag(self):
        """Confirm setting the remote tag alters the correct attribute."""
        self.tag.remote_tag = 'eggs'
        consume_info = self.tag.element.find('ConsumeInfo')
        self.assertEqual(consume_info.attrib['RemoteTag'], 'eggs')

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

    def create_tag(self, xml_str):
        e = fixture.parse_xml(xml_str)
        self.tag = l5x.tag.Tag(e, None)

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
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Description>
<![CDATA[foo]]>
</Description>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.assertEqual(self.tag.description, 'foo')

    def test_multi_read(self):
        """
        Confirm reading a description from a multi-language project returns
        only content from the current language.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Description>
<LocalizedDescription Lang="en-US">
<![CDATA[pass]]>
</LocalizedDescription>
<LocalizedDescription Lang="zh-CN">
<![CDATA[fail]]>
</LocalizedDescription>
</Description>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.assertEqual(self.tag.description, 'pass')

    def test_single_read_none(self):
        """
        Confirm reading an empty description from a single-language project.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.assertIsNone(self.tag.description)

    def test_multi_read_none(self):
        """
        Confirm reading an empty description from a multi-language project.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.assertIsNone(self.tag.description)

    def test_multi_read_none_foreign(self):
        """
        Confirm reading an empty description from a multi-language project
        that has descriptions in other languages.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Description>
<LocalizedDescription Lang="zh-CN">
<![CDATA[fail]]>
</LocalizedDescription>
</Description>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.assertIsNone(self.tag.description)

    def test_single_new(self):
        """Confirm adding a description to a single-language project."""
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.tag.description = 'new'
        self.assert_description('new')

    def test_multi_new(self):
        """Confirm adding a description to a multi-language project."""
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.tag.description = 'new'
        self.assert_localized_description('new', self.TARGET_LANGUAGE)

    def test_multi_new_foreign(self):
        """
        Confirm adding a description to a multi-language project that has
        descriptions in other languages.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Description>
<LocalizedDescription Lang="zh-CN">
<![CDATA[other]]>
</LocalizedDescription>
</Description>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.tag.description = 'new'
        self.assert_localized_description('new', self.TARGET_LANGUAGE)
        self.assert_localized_description('other', 'zh-CN')

    def test_single_overwrite(self):
        """
        Confirm overwriting an existing description in a single-language
        project.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Description>
<![CDATA[foo]]>
</Description>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.tag.description = 'new'
        self.assert_description('new')

    def test_multi_overwrite(self):
        """
        Confirm overwriting an existing description in a multi-language
        project.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Description>
<LocalizedDescription Lang="en-US">
<![CDATA[old]]>
</LocalizedDescription>
</Description>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.tag.description = 'new'
        self.assert_localized_description('new', self.TARGET_LANGUAGE)

    def test_multi_overwrite_foreign(self):
        """
        Confirm overwriting an existing description in a multi-language
        project that has descriptions on other languages only affects
        the description in the current language.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Description>
<LocalizedDescription Lang="en-US">
<![CDATA[old]]>
</LocalizedDescription>
<LocalizedDescription Lang="zh-CN">
<![CDATA[other]]>
</LocalizedDescription>
</Description>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.tag.description = 'new'
        self.assert_localized_description('new', self.TARGET_LANGUAGE)
        self.assert_localized_description('other', 'zh-CN')

    def test_single_delete(self):
        """Confirm removing a description from a single-language project."""
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Description>
<![CDATA[foo]]>
</Description>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.tag.description = None
        self.assert_no_matching_element('Description')

    def test_multi_delete(self):
        """Confirm removing a description from a multi-language project."""
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Description>
<LocalizedDescription Lang="en-US">
<![CDATA[old]]>
</LocalizedDescription>
</Description>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.tag.description = None
        self.assert_no_matching_element('Description')

    def test_multi_delete_foreign(self):
        """
        Confirm removing a description from a multi-language project affects
        only descriptions in the current language.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Description>
<LocalizedDescription Lang="en-US">
<![CDATA[old]]>
</LocalizedDescription>
<LocalizedDescription Lang="zh-CN">
<![CDATA[other]]>
</LocalizedDescription>
</Description>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.tag.description = None

        # Ensure no localized description remains in the current language.
        path = "Description/LocalizedDescription[@Lang='{0}']".format(
            self.TARGET_LANGUAGE)
        self.assert_no_matching_element(path)

        # Ensure descriptions in other languages are unaffected.
        self.assert_localized_description('other', 'zh-CN')

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
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<![CDATA[foo]]>
</Comment>
</Comments>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.assertEqual(self.tag[0].description, 'foo')

    def test_multi_read(self):
        """
        Confirm reading a comment from a multi-language project returns
        only content from the current language.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<LocalizedComment Lang="en-US">
<![CDATA[pass]]>
</LocalizedComment>
<LocalizedComment Lang="zh-CN">
<![CDATA[fail]]>
</LocalizedComment>
</Comment>
</Comments>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.assertEqual(self.tag[0].description, 'pass')

    def test_single_read_none(self):
        """
        Confirm reading a nonexistent comment from a single-language project.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.assertIsNone(self.tag[0].description)

    def test_multi_read_none_foreign(self):
        """
        Confirm reading a nonexistent comment from a multi-language project
        that has comments in other languages.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<LocalizedComment Lang="zh-CN">
<![CDATA[other]]>
</LocalizedComment>
</Comment>
</Comments>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.assertIsNone(self.tag[0].description)

    def test_single_new(self):
        """Confirm adding a comment to a single-language project."""
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.tag[0].description = 'new'
        self.assert_comment('.0', 'new')

    def test_multi_new(self):
        """Confirm adding a comment to a multi-language project."""
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.tag[0].description = 'new'
        self.assert_localized_comment('.0', 'new', self.TARGET_LANGUAGE)

    def test_multi_new_foreign(self):
        """
        Confirm adding a comment to a multi-language project that has
        comments in other languages.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<LocalizedComment Lang="zh-CN">
<![CDATA[other]]>
</LocalizedComment>
</Comment>
</Comments>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.tag[0].description = 'new'
        self.assert_localized_comment('.0', 'new', self.TARGET_LANGUAGE)
        self.assert_localized_comment('.0', 'other', 'zh-CN')

    def test_single_overwrite(self):
        """
        Confirm overwriting an existing comment in a single-language
        project.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<![CDATA[foo]]>
</Comment>
</Comments>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.tag[0].description = 'new'
        self.assert_comment('.0', 'new')

    def test_multi_overwrite(self):
        """
        Confirm overwriting an existing comment in a multi-language
        project.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<LocalizedComment Lang="en-US">
<![CDATA[old]]>
</LocalizedComment>
</Comment>
</Comments>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.tag[0].description = 'new'
        self.assert_localized_comment('.0', 'new', self.TARGET_LANGUAGE)

    def test_multi_overwrite_foreign(self):
        """
        Confirm overwriting an existing comment in a multi-language
        project that has comments on other languages only affects
        the comment in the current language.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<LocalizedComment Lang="en-US">
<![CDATA[old]]>
</LocalizedComment>
<LocalizedComment Lang="zh-CN">
<![CDATA[other]]>
</LocalizedComment>
</Comment>
</Comments>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.tag[0].description = 'new'
        self.assert_localized_comment('.0', 'new', self.TARGET_LANGUAGE)
        self.assert_localized_comment('.0', 'other', 'zh-CN')

    def test_single_delete(self):
        """Confirm removing a comment from a single-language project."""
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<![CDATA[foo]]>
</Comment>
</Comments>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.tag[0].description = None
        self.assert_no_matching_element('Comments')

    def test_single_delete_other_operand(self):
        """
        Confirm removing a comment from a single-language project
        does not affect comments for other operands.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<![CDATA[foo]]>
</Comment>
<Comment Operand=".1">
<![CDATA[bar]]>
</Comment>
</Comments>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
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
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<![CDATA[foo]]>
</Comment>
<Comment Operand=".1">
<![CDATA[bar]]>
</Comment>
</Comments>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.tag[0].description = None
        self.tag[1].description = None
        self.assert_no_matching_element('Comments')

    def test_multi_delete(self):
        """Confirm removing a comment from a multi-language project."""
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<LocalizedComment Lang="en-US">
<![CDATA[old]]>
</LocalizedComment>
</Comment>
</Comments>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.tag[0].description = None
        self.assert_no_matching_element('Comments')

    def test_multi_delete_other_operand(self):
        """
        Confirm removing a comment from a multi-language project
        does not affect comments for other operands.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<LocalizedComment Lang="en-US">
<![CDATA[foo]]>
</LocalizedComment>
</Comment>
<Comment Operand=".1">
<LocalizedComment Lang="en-US">
<![CDATA[bar]]>
</LocalizedComment>
</Comment>
</Comments>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
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
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<LocalizedComment Lang="en-US">
<![CDATA[foo]]>
</LocalizedComment>
</Comment>
<Comment Operand=".1">
<LocalizedComment Lang="en-US">
<![CDATA[bar]]>
</LocalizedComment>
</Comment>
</Comments>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.tag[0].description = None
        self.tag[1].description = None
        self.assert_no_matching_element('Comments')

    def test_multi_delete_foreign(self):
        """
        Confirm removing a comment from a multi-language project affects
        only comments in the current language.
        """
        self.create_tag("""<Tag Name="tag" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<LocalizedComment Lang="en-US">
<![CDATA[foo]]>
</LocalizedComment>
<LocalizedComment Lang="zh-CN">
<![CDATA[other]]>
</LocalizedComment>
</Comment>
</Comments>
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>""")
        self.set_multilanguage()
        self.tag[0].description = None
        self.assert_localized_comment('.0', 'other', 'zh-CN')

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


class AliasFor(unittest.TestCase):
    """Tests for the alias_for attribute of alias tags."""
    def setUp(self):
        e = fixture.parse_xml(r"""<Tag Name="alias" TagType="Alias" Radix="Decimal" AliasFor="tag" ExternalAccess="Read/Write">
<Comments>
<Comment Operand=".0">
<![CDATA[alias operand comment]]>
</Comment>
</Comments>
</Tag>""")
        self.tag = l5x.tag.Tag(e, None)

    def test_alias_read(self):
        """Confirm reading the alias_for attribute returns the correct value."""
        self.assertEqual(self.tag.alias_for,
                         self.tag.element.attrib['AliasFor'])

    def test_alias_write(self):
        """Confirm writing the alias updates the XML attribute."""
        self.tag.alias_for = 'foo'
        self.assertEqual(self.tag.element.attrib['AliasFor'], 'foo')

    def test_remove_comments_on_alias_write(self):
        """Confirm all comments are removed when the alias is changed."""
        self.tag.alias_for = 'bar'
        comments = self.tag.element.find('Comments')
        self.assertIsNone(comments)

    def test_write_non_string_alias(self):
        """Confirm an exception is raised when writing a non-string alias."""
        with self.assertRaises(TypeError):
            self.tag.alias_for = 42

    def test_write_empty_alias(self):
        """Confirm an exception is raised when writing an empty alias string."""
        with self.assertRaises(ValueError):
            self.tag.alias_for = '  '
