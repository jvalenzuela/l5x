"""
Unit tests for the array module.
"""

from l5x import (array, tag)
from tests import fixture
import copy
import io
import itertools
import xml.etree.ElementTree as ElementTree
import unittest


class BaseTag(object):
    """Base class for creating mock tag arrays."""

    def create_array_tag(self, datatype, dim, data):
        """Creates a mock top-level array tag."""
        self.element = fixture.create_tag_element(datatype, data=data, dim=dim)
        self.prj = fixture.create_project()
        self.array = tag.Tag(self.element, self.prj, None)

    def get_array_raw_data(self):
        """Returns the array's raw data content."""
        # The project must be written to flush the modified raw data buffer
        # back to the XML document.
        buf = io.BytesIO()
        self.prj.write(buf)

        data_element = self.element.find('Data')
        return list(bytes.fromhex(data_element.text))


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


class IndexSingleDimensionTag(unittest.TestCase):
    """Tests for indexing a single-dimensional array as a top-level tag."""

    def setUp(self):
        prj = fixture.create_project()
        element = fixture.create_tag_element('SINT', data=[0] * 3, dim=(3,))
        self.array = tag.Tag(element, prj, None)

    def test_invalid_type(self):
        """Ensure non-integer indices raise an exception."""
        with self.assertRaises(TypeError):
            self.array['spam']

    def test_negative(self):
        """Ensure negative indices raise an exception."""
        with self.assertRaises(IndexError):
            self.array[-1]

    def test_out_of_range(self):
        """Ensure indices beyond the end of the array raise an exception."""
        with self.assertRaises(IndexError):
            self.array[3]

    def test_valid_range(self):
        """Ensure indices within the array are accepted."""
        [self.array[i] for i in range(3)]


class IndexMultiDimensionTag(unittest.TestCase):
    """Tests for indexing a multi-dimensional array as a top-level tag."""

    def setUp(self):
        prj = fixture.create_project()
        element = fixture.create_tag_element('SINT', data=[0] * 60,
                                             dim=(3, 4, 5))
        self.array = tag.Tag(element, prj, None)

    def test_invalid_type(self):
        """Ensure non-integer indices raise an exception."""
        with self.assertRaises(TypeError):
            self.array['spam']
        for i in range(5):
            with self.assertRaises(TypeError):
                self.array[i]['spam']
            for j in range(4):
                with self.assertRaises(TypeError):
                    self.array[i][j]['spam']

    def test_negative(self):
        """Ensure negative indices raise an exception."""
        with self.assertRaises(IndexError):
            self.array[-1]
        for i in range(5):
            with self.assertRaises(IndexError):
                self.array[i][-1]
            for j in range(4):
                with self.assertRaises(IndexError):
                    self.array[i][j][-1]

    def test_out_of_range(self):
        """Ensure indices beyond the end of the array raise an exception."""
        with self.assertRaises(IndexError):
            self.array[5]
        for i in range(3):
            with self.assertRaises(IndexError):
                self.array[i][4]
            for j in range(4):
                with self.assertRaises(IndexError):
                    self.array[i][j][3]

    def test_valid_range(self):
        """Ensure indices within the array are accepted."""
        for i in range(5):
            self.array[i]
            for j in range(4):
                self.array[i][j]
                for k in range(3):
                    self.array[i][j][k]


class WriteValueErrors(BaseTag, unittest.TestCase):
    """Exception tests for writing invalid values."""

    def test_single_dimensional_member_invalid_type(self):
        """
        Confirm an exception is raised when writing an invalid type to
        the value of a member in a single-dimensional array.
        """
        self.create_array_tag('SINT', (3,), [0] * 3)
        with self.assertRaises(TypeError):
            self.array[0].value = 'not an int'

    def test_multi_dimensional_member_invalid_type(self):
        """
        Confirm an exception is raised when writing an invalid type to
        the value of a member in a multi-dimensional array.
        """
        self.create_array_tag('SINT', (3, 3), [0] * 9)
        with self.assertRaises(TypeError):
            self.array[1][1].value = 'not an int'

    def test_single_dimensional_non_list(self):
        """
        Confirm an exception is raised when writing a non-list to
        the entire value of a single-dimensional array.
        """
        self.create_array_tag('SINT', (3,), [0] * 3)
        with self.assertRaises(TypeError):
            self.array.value = set([1, 2, 3])

    def test_multi_dimensional_non_list_top(self):
        """
        Confirm an exception is raised when writing a non-list to
        the top-level value of a multi-dimensional array.
        """
        self.create_array_tag('SINT', (2, 2), [0] * 4)
        with self.assertRaises(TypeError):
            self.array.value = set([1, 2])

    def test_multi_dimensional_non_list_member(self):
        """
        Confirm an exception is raised when writing a list containing
        a non-list member to a multi-dimensional array.
        """
        self.create_array_tag('SINT', (2, 2), [0] * 4)
        with self.assertRaises(TypeError):
            self.array.value = [[0, 0], set([1, 2])]

    def test_single_dimensional_too_long(self):
        """
        Confirm an exception is raised when writing a list exceeding
        the array size of a single-dimensional array.
        """
        self.create_array_tag('SINT', (3,), [0] * 3)
        with self.assertRaises(IndexError):
            self.array.value = [0] * 4

    def test_multi_dimensional_too_long(self):
        """
        Confirm an exception is raised when writing a nested list
        containing one member exceeding the array size of a
        multi-dimensional array.
        """
        self.create_array_tag('SINT', (2, 2), [0] * 4)
        with self.assertRaises(IndexError):
            self.array.value = [[0, 0], [0, 0, 0]]


class MemberValueAtomicSingleDimensionTag(BaseTag):
    """
    Mixin class defining tests for reading and writing single member values of
    a single-dimensional array of atomic data types.
    """

    dim = (3,)

    def test_read_data_type(self):
        """Confirm the correct type when reading element values."""
        self.create_array_tag(self.data_type, self.dim, self.raw_data)
        for i in range(self.dim[0]):
            self.assertIsInstance(self.array[i].value, type(self.values[i]))

    def test_read_data_value(self):
        """Confirm the correct value when reading element values."""
        self.create_array_tag(self.data_type, self.dim, self.raw_data)
        for i in range(self.dim[0]):
            self.assertEqual(self.array[i].value, self.values[i])

    def test_write_data(self):
        """Confirm writing values properly updates the raw data."""
        # Initialize raw data of all zeros.
        self.create_array_tag(self.data_type, self.dim,
                              [0] * len(self.raw_data))

        # Write values to every element.
        for i in range(self.dim[0]):
            self.array[i].value = self.values[i]

        # Verify resulting raw data.
        raw = self.get_array_raw_data()
        self.assertEqual(raw, self.raw_data)


class MemberValueAtomicMultiDimensionTag(BaseTag):
    """
    Mixin class defining tests for reading and writing single member values of
    a multi-dimensional array of atomic data types.
    """

    dim = (2, 3, 4)

    def test_read_data_type(self):
        """Confirm the correct type when reading element values."""
        self.create_array_tag(self.data_type, self.dim,
                              [0] * len(self.raw_data))
        for i, j, k in self.iter_dim():
            self.assertIsInstance(self.array[k][j][i].value,
                                  type(self.values[k][j][i]))

    def test_read_data_value(self):
        """Confirm the correct value when reading element values."""
        self.create_array_tag(self.data_type, self.dim, self.raw_data)
        for i, j, k in self.iter_dim():
            self.assertEqual(self.array[k][j][i].value, self.values[k][j][i])

    def test_write_data(self):
        """Confirm writing values properly updates the raw data."""
        # Initialize a target array of zeros.
        self.create_array_tag(self.data_type, self.dim,
                              [0] * len(self.raw_data))

        # Write to every member value.
        for i, j, k in self.iter_dim():
            self.array[k][j][i].value = self.values[k][j][i]

        # Confirm the raw data buffer matches.
        raw = self.get_array_raw_data()
        self.assertEqual(raw, self.raw_data)

    def iter_dim(self):
        """Generates an iterator of all possible dimensions."""
        return itertools.product(*[range(i) for i in self.dim])


class ArrayValueAtomicSingleDimensionTag(BaseTag):
    """
    Mixin class defining tests for reading and writing the composite
    value of a single-dimensional array of atomic data types.
    """

    dim = (3,)

    def test_read_data_type(self):
        """Confirm reading the value yields a list."""
        self.create_array_tag(self.data_type, self.dim, self.raw_data)
        self.assertIsInstance(self.array.value, list)

    def test_read_data_value(self):
        """Confirm reading the value yields the correct values."""
        self.create_array_tag(self.data_type, self.dim, self.raw_data)
        self.assertEqual(self.array.value, self.values)

    def test_write_all_data(self):
        """
        Confirm writing a list containing all members properly updates
        the raw data.
        """
        # Initialize a target array of ones.
        self.create_array_tag(self.data_type, self.dim,
                              [0xff] * len(self.raw_data))
        self.array.value = self.values
        raw = self.get_array_raw_data()
        self.assertEqual(raw, self.raw_data)


class ArrayValueAtomicMultiDimensionTag(BaseTag):
    """
    Mixin class defining tests for reading and writing the composite
    value of a multi-dimensional array of atomic data types.
    """

    dim = (2, 3, 4)

    def test_read_data_type(self):
        """
        Confirm reading the value yields a list for every dimension
        except the last.
        """
        self.create_array_tag(self.data_type, self.dim, self.raw_data)
        value = self.array.value
        self.assertIsInstance(value, list)
        for i in range(self.dim[0]):
            self.assertIsInstance(value[i], list)
            for j in range(self.dim[1]):
                self.assertIsInstance(value[i][j], list)

    def test_read_member_values(self):
        """Confirm reading correct values for all list elements."""
        self.create_array_tag(self.data_type, self.dim, self.raw_data)
        self.assertEqual(self.array.value, self.values)

    def test_write_all_data(self):
        """
        Confirm writing nested lists containing all members properly
        updates the raw data.
        """
        # Initialize a target array of ones.
        self.create_array_tag(self.data_type, self.dim,
                              [0xff] * len(self.raw_data))
        self.array.value = self.values
        raw = self.get_array_raw_data()
        self.assertEqual(raw, self.raw_data)


class SintSingleDimension(object):
    """Mixin class providing mock data for a single-dimensional SINT array."""

    data_type = 'SINT'
    raw_data = list(range(1 * 3))
    values = [0, 1, 2]


class SintMultiDimension(object):
    """Mixin class providing mock data for a multi-dimensional SINT array."""

    data_type = 'SINT'
    raw_data = list(range(1 * 2 * 3 * 4))
    values = [
        [
            [0, 1],
            [2, 3],
            [4, 5]
        ],
        [
            [6, 7],
            [8, 9],
            [10, 11]
        ],
        [
            [12, 13],
            [14, 15],
            [16, 17]
        ],
        [
            [18, 19],
            [20, 21],
            [22, 23]
        ]
    ]


class IntSingleDimension(object):
    """Mixin class providing mock data for a single-dimensional INT array."""

    data_type = 'INT'
    raw_data = list(range(2 * 3))
    values = [0x0100, 0x0302, 0x0504]


class IntMultiDimension(object):
    """Mixin class providing mock data for a multi-dimensional INT array."""

    data_type = 'INT'
    raw_data = list(range(2 * 2 * 3 * 4))
    values = [
        [
            [256, 770],
            [1284, 1798],
            [2312, 2826]
        ],
        [
            [3340, 3854],
            [4368, 4882],
            [5396, 5910]
        ],
        [
            [6424, 6938],
            [7452, 7966],
            [8480, 8994]
        ],
        [
            [9508, 10022],
            [10536, 11050],
            [11564, 12078]
        ]
    ]


class DintSingleDimension(object):
    """Mixin class providing mock data for a single-dimensional DINT array."""

    data_type = 'DINT'
    raw_data = list(range(4 * 3))
    values = [50462976, 117835012, 185207048]


class DintMultiDimension(object):
    """Mixin class providing mock data for a multi-dimensional DINT array."""

    data_type = 'DINT'
    raw_data = list(range(4 * 2 * 3 * 4))
    values = [
        [
            [50462976, 117835012],
            [185207048, 252579084],
            [319951120, 387323156]
        ],
        [
            [454695192, 522067228],
            [589439264, 656811300],
            [724183336, 791555372]
        ],
        [
            [858927408, 926299444],
            [993671480, 1061043516],
            [1128415552, 1195787588]
        ],
        [
            [1263159624, 1330531660],
            [1397903696, 1465275732],
            [1532647768, 1600019804]
        ]
    ]


class LintSingleDimension(object):
    """Mixin class providing mock data for a single-dimensional LINT array."""

    data_type = 'LINT'
    raw_data = list(range(8 * 3))
    values = [506097522914230528, 1084818905618843912, 1663540288323457296]


class LintMultiDimension(object):
    """Mixin class providing mock data for a multi-dimensional LINT array."""

    data_type = 'LINT'
    raw_data = list(range(8 * 2 * 3 * 4))
    values = [
        [
            [506097522914230528, 1084818905618843912],
            [1663540288323457296, 2242261671028070680],
            [2820983053732684064, 3399704436437297448]
        ],
        [
            [3978425819141910832, 4557147201846524216],
            [5135868584551137600, 5714589967255750984],
            [6293311349960364368, 6872032732664977752]
        ],
        [
            [7450754115369591136, 8029475498074204520],
            [8608196880778817904, 9186918263483431288],
            [-8681104427521506944, -8102383044816893560]
        ],
        [
            [-7523661662112280176, -6944940279407666792],
            [-6366218896703053408, -5787497513998440024],
            [-5208776131293826640, -4630054748589213256]
        ]
    ]


# The values in the following REAL data classes were chosen for the
# following reasons:
#
# 1. They represent a set of unique, floating-point values, so each array
#    member can be positively identified.
# 2. The floating-point values are exact integers for easy equality testing.
# 3. They have unique, non-zero, non-repeating raw data bytes.

class RealSingleDimension(object):
    """Mixin class providing mock data for a single-dimensional REAL array."""

    data_type = 'REAL'
    raw_data = [
        0x40, 0xDA, 0x23, 0x48, 0x80, 0xDA,
        0x23, 0x48, 0xC0, 0xDA, 0x23, 0x48
    ]
    values = [167785.0, 167786.0, 167787.0]


class RealMultiDimension(object):
    """Mixin class providing mock data for a multi-dimensional REAL array."""

    data_type = 'REAL'
    raw_data = [
        0x40, 0xDA, 0x23, 0x48, 0x80, 0xDA, 0x23, 0x48, 0xC0, 0xDA, 0x23,
        0x48, 0x40, 0xDB, 0x23, 0x48, 0x80, 0xDB, 0x23, 0x48, 0xC0, 0xDB,
        0x23, 0x48, 0x40, 0xDC, 0x23, 0x48, 0x80, 0xDC, 0x23, 0x48, 0xC0,
        0xDC, 0x23, 0x48, 0x40, 0xDD, 0x23, 0x48, 0x80, 0xDD, 0x23, 0x48,
        0xC0, 0xDD, 0x23, 0x48, 0x40, 0xDE, 0x23, 0x48, 0x80, 0xDE, 0x23,
        0x48, 0xC0, 0xDE, 0x23, 0x48, 0x40, 0xDF, 0x23, 0x48, 0x80, 0xDF,
        0x23, 0x48, 0xC0, 0xDF, 0x23, 0x48, 0x40, 0xE0, 0x23, 0x48, 0x80,
        0xE0, 0x23, 0x48, 0xC0, 0xE0, 0x23, 0x48, 0x40, 0xE1, 0x23, 0x48,
        0x80, 0xE1, 0x23, 0x48, 0xC0, 0xE1, 0x23, 0x48
    ]
    values = [
        [
            [167785.0, 167786.0],
            [167787.0, 167789.0],
            [167790.0, 167791.0]
        ],
        [
            [167793.0, 167794.0],
            [167795.0, 167797.0],
            [167798.0, 167799.0]
        ],
        [
            [167801.0, 167802.0],
            [167803.0, 167805.0],
            [167806.0, 167807.0]
        ],
        [
            [167809.0, 167810.0],
            [167811.0, 167813.0],
            [167814.0, 167815.0]
        ]
    ]


class SintMemberValueSingleDimension(
        MemberValueAtomicSingleDimensionTag,
        SintSingleDimension,
        unittest.TestCase):
    """
    Composite class testing single member value access to a single-dimensional
    array of SINTs.
    """
    pass


class SintMemberValueMultiDimension(
        MemberValueAtomicMultiDimensionTag,
        SintMultiDimension,
        unittest.TestCase):
    """
    Composite class testing single member value access to a multi-dimensional
    array of SINTs.
    """
    pass


class SintArrayValueSingleDimension(
        ArrayValueAtomicSingleDimensionTag,
        SintSingleDimension,
        unittest.TestCase):
    """
    Composite class testing array value access to a single-dimensional
    array of SINTs.
    """
    pass


class SintArrayValueMultiDimension(
        ArrayValueAtomicMultiDimensionTag,
        SintMultiDimension,
        unittest.TestCase):
    """
    Composite class testing array value access to a multi-dimensional
    array of SINTs.
    """
    pass


class IntMemberValueSingleDimension(
        MemberValueAtomicSingleDimensionTag,
        IntSingleDimension,
        unittest.TestCase):
    """
    Composite class testing single member value access to a single-dimensional
    array of INTs.
    """
    pass


class IntMemberValueMultiDimension(
        MemberValueAtomicMultiDimensionTag,
        IntMultiDimension,
        unittest.TestCase):
    """
    Composite class testing single member value access to a multi-dimensional
    array of INTs.
    """
    pass


class IntArrayValueSingleDimension(
        ArrayValueAtomicSingleDimensionTag,
        IntSingleDimension,
        unittest.TestCase):
    """
    Composite class testing array value access to a single-dimensional
    array of INTs.
    """


class IntArrayValueMultiDimension(
        ArrayValueAtomicMultiDimensionTag,
        IntMultiDimension,
        unittest.TestCase):
    """
    Composite class testing array value access to a multi-dimensional
    array of INTs.
    """
    pass


class DintMemberValueSingleDimension(
        MemberValueAtomicSingleDimensionTag,
        DintSingleDimension,
        unittest.TestCase):
    """
    Composite class testing single member value access to a single-dimensional
    array of DINTs.
    """
    pass


class DintMemberValueMultiDimension(
        MemberValueAtomicMultiDimensionTag,
        DintMultiDimension,
        unittest.TestCase):
    """
    Composite class testing single member value access to a multi-dimensional
    array of DINTs.
    """
    pass


class DintArrayValueSingleDimension(
        ArrayValueAtomicSingleDimensionTag,
        DintSingleDimension,
        unittest.TestCase):
    """
    Composite class testing array value access to a single-dimensional
    array of DINTs.
    """
    pass


class DintArrayValueMultiDimension(
        ArrayValueAtomicMultiDimensionTag,
        DintMultiDimension,
        unittest.TestCase):
    """
    Composite class testing array value access to a multi-dimensional
    array of DINTs.
    """
    pass


class LintMemberValueSingleDimension(
        MemberValueAtomicSingleDimensionTag,
        LintSingleDimension,
        unittest.TestCase):
    """
    Composite class testing single member value access to a single-dimensional
    array of LINTs.
    """
    pass


class LintMemberValueMultiDimension(
        MemberValueAtomicMultiDimensionTag,
        LintMultiDimension,
        unittest.TestCase):
    """
    Composite class testing single member value access to a multi-dimensional
    array of LINTs.
    """
    pass


class LintArrayValueSingleDimension(
        ArrayValueAtomicSingleDimensionTag,
        LintSingleDimension,
        unittest.TestCase):
    """
    Composite class testing array value access to a single-dimensional
    array of LINTs.
    """
    pass


class LintArrayValueMultiDimension(
        ArrayValueAtomicMultiDimensionTag,
        LintMultiDimension,
        unittest.TestCase):
    """
    Composite class testing array value access to a multi-dimensional
    array of LINTs.
    """
    pass


class RealMemberValueSingleDimension(
        MemberValueAtomicSingleDimensionTag,
        RealSingleDimension,
        unittest.TestCase):
    """
    Composite class testing single member value access to a single-dimensional
    array of REALs.
    """
    pass


class RealMemberValueMultiDimension(
        MemberValueAtomicMultiDimensionTag,
        RealMultiDimension,
        unittest.TestCase):
    """
    Composite class testing single member value access to a multi-dimensional
    array of REALs.
    """
    pass


class RealArrayValueSingleDimension(
        ArrayValueAtomicSingleDimensionTag,
        RealSingleDimension,
        unittest.TestCase):
    """
    Composite class testing array value access to a single-dimensional
    array of REALs.
    """
    pass


class RealArrayValueMultiDimension(
        ArrayValueAtomicMultiDimensionTag,
        RealMultiDimension,
        unittest.TestCase):
    """
    Composite class testing array value access to a multi-dimensional
    array of REALs.
    """
    pass


class MemberValueBool(BaseTag, unittest.TestCase):
    """Tests for accessing the value of a single member in a BOOL array."""

    dim = (64,)

    def test_read_type(self):
        """Confirm the correct type of value is read."""
        data = [0] * 8
        self.create_array_tag('BOOL', self.dim, data)
        for i in range(self.dim[0]):
            self.assertIsInstance(self.array[i].value, int)

    def test_read_value(self):
        """Confirm the correct value is read."""
        for i in range(self.dim[0]):
            # Create a data buffer with only one bit set to 1.
            data = [0] * 8
            data[i // 8] = 1 << i % 8
            self.create_array_tag('BOOL', self.dim, data)

            # Check the value of every member.
            for j in range(self.dim[0]):
                expected = 1 if i == j else 0
                self.assertEqual(expected, self.array[j].value)

    def test_write_one(self):
        """Confirm writing a one value correctly updates the raw data."""
        for i in range(self.dim[0]):
            data = [0] * 8
            self.create_array_tag('BOOL', self.dim, data)
            self.array[i].value = 1
            raw = self.get_array_raw_data()
            data[i // 8] = 1 << i % 8
            self.assertEqual(data, raw)

    def test_write_zero(self):
        """Confirm writing a zero value correctly updates the raw data."""
        for i in range(self.dim[0]):
            data = [0xff] * 8
            self.create_array_tag('BOOL', self.dim, data)
            self.array[i].value = 0
            raw = self.get_array_raw_data()
            data[i // 8] &= ~(1 << i % 8)
            self.assertEqual(data, raw)

    def test_write_invalid_range(self):
        """Confirm writing an integer other than 0 or 1 raises an exception."""
        for i in range(self.dim[0]):
            data = [0] * 8
            self.create_array_tag('BOOL', self.dim, data)
            with self.assertRaises(ValueError):
                self.array[i].value = -1
            with self.assertRaises(ValueError):
                self.array[i].value = 2

    def test_write_invalid_type(self):
        """Confirm writing an incorrect data type raises an exception."""
        data = [0] * 8
        self.create_array_tag('BOOL', self.dim, data)
        for i in range(self.dim[0]):
            with self.assertRaises(TypeError):
                self.array[i].value = 'spam'
