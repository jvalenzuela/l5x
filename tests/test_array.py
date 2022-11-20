"""
Unit tests for the array module.
"""

from l5x import (array, tag)
from tests import fixture
import xml.etree.ElementTree as ElementTree
import unittest


class ArrayDetect(unittest.TestCase):
    """Unit tests for the is_array function."""

    def test_tag_non_array(self):
        """Confirm a non-array tag is not detected as an array."""
        e = ElementTree.Element('Tag')
        self.assertFalse(array.is_array(e))

    def test_tag_array_single(self):
        """Confirm a single-dimensional array tag is detected as an array."""
        e = ElementTree.Element('Tag')
        e.attrib['Dimensions'] = '1'
        self.assertTrue(array.is_array(e))

    def test_tag_array_multi(self):
        """Confirm a multi-dimensional array tag is detected as an array."""
        e = ElementTree.Element('Tag')
        e.attrib['Dimensions'] = '1 2'
        self.assertTrue(array.is_array(e))

    def test_udt_non_array(self):
        """Confirm a non-array UDT member is not detected as an array."""
        e = ElementTree.Element('Member')
        e.attrib['Dimension'] = '0'
        self.assertFalse(array.is_array(e))

    def test_udt_array(self):
        """Confirm an array UDT member is detected as an array."""
        e = ElementTree.Element('Member')
        e.attrib['Dimension'] = '1'
        self.assertTrue(array.is_array(e))


class ParseDim(unittest.TestCase):
    """Unit tests for parsing dimension attributes."""

    def test_tag(self):
        """Verify a top-level tag's dimensions."""

        # Tags may have between 1 and 3 dimensions, inclusive.
        for size in range(1, 4):
            expected = tuple([x + 1 for x in range(size)])
            e = ElementTree.Element('Tag')
            e.attrib['Dimensions'] = self._dim_str(expected)
            ar = type('TestArray', (array.Base, ), {'element': e})
            self.assertEqual(expected, ar.get_dim())

    def test_udt(self):
        """Verify a UDT member's dimension."""

        # UDT's may only have a single dimension.
        expected = (5, )

        e = ElementTree.Element('Member')
        e.attrib['Dimension'] = self._dim_str(expected)
        ar = type('TestArray', (array.Base, ), {'element': e})
        self.assertEqual(expected, ar.get_dim())

    def _dim_str(self, dim):
        """Generates an attribute string from a given set of dimensions."""
        return ' '.join([str(x) for x in reversed(dim)])


class RawSize(unittest.TestCase):
    """Unit tests for computing raw data sizes of non-BOOL arrays."""

    def _define_array(self, member_size, dim):
        """Creates a mock array class with a given member size and dimension."""
        ar_attrib = {}

        # Create the XML element with dimensions.
        element = ElementTree.Element('TestElement')
        element.attrib['Dimensions'] = ' '.join([str(x) for x in dim])
        ar_attrib['element'] = element

        # Define a dummy data type with the desired raw size.
        ar_attrib['member_type'] = type('Dummy', (object, ),
                                        {'raw_size': member_size})

        return type('TestArray', (array.Array, ), ar_attrib)

    def test_single(self):
        """Validate the size of a single-dimensional array."""
        ar = self._define_array(4, (4, ))
        self.assertEqual(16, ar.raw_size)

    def test_multi(self):
        """Validate the size of a multi-dimensional array."""
        ar = self._define_array(4, (2, 2, 2))
        self.assertEqual(32, ar.raw_size)

    def test_no_pad(self):
        """Validate the size of an array that does not require a tail pad."""
        ar = self._define_array(2, (16, ))
        self.assertEqual(32, ar.raw_size)

    def test_pad(self):
        """Validate the size of an array that requires tail padding."""
        # Iterate through sizes 5-8, which should all be padded to 8 bytes.
        for i in range(5, 9):
            ar = self._define_array(1, (i, ))
            self.assertEqual(8, ar.raw_size)


class BoolRawSize(unittest.TestCase):
    """Unit tests for computing the raw data size of BOOL arrays."""

    def test_bool(self):
        """Validate the size of a BOOL array."""
        element = ElementTree.Element('TestElement')
        ar = type('TestArray', (array.BoolArray, ), {'element': element})
        for d in [32, 64]:
            element.attrib['Dimensions'] = str(d)
            self.assertEqual(d // 8, ar.raw_size)


class ShapeRead(object):
    """Superclass defining test methods for reading the shape attribute."""

    def test_shape_type(self):
        """Confirm the returned shape is a tuple."""
        self.assertIsInstance(self.array.shape, tuple)

    def test_dimension_type(self):
        """Confirm members of the shape tuple are integers."""
        [self.assertIsInstance(d, int) for d in self.array.shape]

    def test_dim_value(self):
        """Confirm all dimension members match the definition."""
        self.assertEqual(self.dim, self.array.shape)


class ShapeReadTag(ShapeRead):
    """
    Superclass for tests reading the shape attribute of a top-level
    array tag.
    """

    def setUp(self):
        prj = fixture.create_project()
        element = fixture.create_tag_element(self.data_type, dim=self.dim)
        self.array = tag.Tag(element, prj, None)


class ShapeReadMember(ShapeRead):
    """
    Superclass for tests reading the shape attribute of an array member
    of a structured data type.
    """

    def setUp(self):
        prj = fixture.create_project()
        element = fixture.create_member_element(self.data_type, dim=self.dim)
        base = prj.get_data_type(element)
        member_type = type('test', (tag.Member, base), {})
        self.array = member_type(None, None, None)


class ShapeReadNonBoolTagSingle(ShapeReadTag, unittest.TestCase):
    """
    Unit tests for reading the shape attribute of a single-dimensional
    array of a non-BOOL data type as a top-level tag.
    """

    data_type = 'SINT'
    dim = (8,)


class ShapeReadNonBoolTagMulti(ShapeReadTag, unittest.TestCase):
    """
    Unit tests for reading the shape attribute of a multi-dimensional array
    of a non-BOOL data type as a top-level tag.
    """

    data_type = 'SINT'
    dim = (5, 4, 3)


class ShapeReadBoolTag(ShapeReadTag, unittest.TestCase):
    """
    Unit tests for reading the shape attribute of a BOOL array as a top-level
    tag.
    """

    data_type = 'BOOL'
    dim = (32,)


class ShapeReadNonBoolMember(ShapeReadMember, unittest.TestCase):
    """
    Unit tests for reading the shape attribute of a structure array member
    of a non-BOOL data type.
    """

    data_type = 'SINT'
    dim = (8,)


class ShapeReadBoolMember(ShapeReadMember, unittest.TestCase):
    """
    Unit tests for reading the shape attribute of a structure BOOL array
    member.
    """

    data_type = 'BOOL'
    dim = (32,)
