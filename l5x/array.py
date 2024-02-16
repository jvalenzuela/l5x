"""
This module contains items for implementing tag arrays, both for top-level
tags and UDT array members.
"""

from l5x import (atomic, tag)
import functools
import operator


def is_array(element):
    """Determines if a given element defines an array."""
    # Tags are an array if they contain a Dimensions attribute.
    if element.tag == 'Tag':
        is_array = 'Dimensions' in element.attrib

    # UDT members always have a Dimension attribute, but are only an array
    # if the dimension is non-zero.
    else:
        is_array = int(element.attrib['Dimension']) != 0

    return is_array


def define_new(element, data_type):
    """Creates a class to access an array defined by a given XML element.

    This is called in two cases:

    1. During the creation of a top-level array tag.
    2. When defining an array structure member.
    """

    # Select the appropriate array base class.
    if element.attrib['DataType'] == 'BOOL':
        base_cls = BoolArray
    else:
        base_cls = Array

    # The new class name is an arbitrary combination of relevant fields.
    name = ' '.join(['Array', element.tag, element.attrib['Name']])

    new_cls = type(name, (base_cls, ), {'element':element})
    set_member_type(new_cls, data_type)
    set_subarray_type(new_cls, element)

    return new_cls


def set_member_type(array_cls, data_type):
    """Creates a class to represent the members of a given array."""

    # Like the parent array class, the new class name is arbitrary.
    name = ' '.join([array_cls.__name__, 'Member',])

    bases = (tag.Member, data_type)

    # Array members reference the same element that defines the array itself.
    attrib =  {'element':array_cls.element}

    array_cls.member_type = type(name, bases, attrib)


def set_subarray_type(array_cls, element):
    """Defines a type that can be instantiated to handle a subarray."""
    # A subarray type is not required for single-dimensional arrays.
    if len(array_cls.get_dim()) == 1:
        return

    # The subarray class name is arbitrary.
    name = ' '.join(['Subarray', element.tag, element.attrib['Name']])

    array_cls.subarray_type = type(name, (Subarray, tag.Member, array_cls), {})


class Value(object):
    """Descriptor class for accessing array values.

    This handles the value of an array or subarray as a whole, not
    values of individual members, which are handled by instances of the
    member type.
    """
    def __get__(self, array, owner=None):
        return [array[i].value for i in range(array.shape[array.which_dim])]

    def __set__(self, array, value):
        if not isinstance(value, list):
            raise TypeError('Value must be a list')
        if len(value) > array.shape[array.which_dim]:
            raise IndexError('Source list is too large')

        for i in range(len(value)):
            array[i].value = value[i]


class Shape(object):
    """Descriptor class to access an array's dimensions."""

    def __get__(self, array, owner=None):
        return array.get_dim()


class Base(object):
    """Base class for all array types."""

    value = Value()
    shape = Shape()

    def __init__(self, subarray_dim=()):
        self.subarray_dim = subarray_dim

    def __getitem__(self, index):
        """Returns an object targeting the given index.

        This will be one of two types:

        1. If the accumulated indices plus this index as sufficient to
           satisfy all dimensions, then the an object representing a
           single member will be returned.

        2. If all dimensions have not yet been specified, an array object
           will be created representing a subarray containing the
           as-yet unspecified indices.
        """
        if not isinstance(index, int):
            raise TypeError('Array indices must be integers')

        if (index < 0) or (index >= self.shape[self.which_dim]):
            raise IndexError('Array index out of range')

        new_dim = list(self.subarray_dim)
        new_dim.insert(0, index)

        # Return a member object if the given index plus subarray indices
        # satisfies all dimensions.
        if len(new_dim) == len(self.shape):
            return self.get_member_object(index)

        # Return a subarray if the accumulated indices do not yet satisfy
        # all dimensions.
        else:
            buf = self.get_buffer(index)
            operand = self.get_operand(index)
            return self.subarray_type(self.tag, buf, operand, tuple(new_dim))

    @property
    def which_dim(self):
        """
        Determines which dimension the next index will be applied to.

        For example, if the parent array is three-dimensional array, and the
        first dimension has been given to create this subarray, the next
        index will be applied to shape[1].
        """
        return len(self.shape) - len(self.subarray_dim) - 1

    def get_operand(self, index):
        """Builds a string identifying an element at a given index.

        This is used to identify comments applied to individual elements.
        """
        dim = list(self.subarray_dim)

        # Dimensions are supplied in logical order, i.e., Dim0 is dim[0],
        # however, they need to be reversed here because they are displayed
        # with the most-significant dimension first.
        dim.reverse()

        # Add the given index as the least-significant dimension.
        dim.append(index)

        dim_str = ','.join([str(d) for d in dim])

        return "{0}[{1}]".format(self.operand, dim_str)

    @classmethod
    def get_dim(cls):
        """Extracts the array's dimensions from the array's element.

        This is implemented as a class method because the array's raw data
        size is dependent on the dimensions, and needs to be available
        before an instance of the array is created.
        """
        try:
            attrib = cls.element.attrib['Dimensions']
        except KeyError:
            attrib = cls.element.attrib['Dimension']

        dims = [int(x) for x in attrib.split()]

        # Dimensions are given as most-significant first, e.g.,
        # "<Dim2> <Dim1> <Dim0>", so they must be reversed so DimX can be
        # indexed as d[X].
        dims.reverse()

        return tuple(dims)


class RawSize(object):
    """
    Descriptor class to compute the number of raw data bytes required to
    store the array when incorporated into a UDT.
    """

    def __get__(self, instance, cls):
        # Compute the storage necessary for all elements.
        dim = cls.get_dim()
        data_size = functools.reduce(operator.mul, dim,
                                     cls.member_type.raw_size)

        # Array sizes are rounded up to a 32-bit boundry.
        tail_pad = (4 - (data_size % 4)) % 4

        return data_size + tail_pad


class Array(Base):
    """Base class for arrays of all types except BOOL."""

    raw_size = RawSize()

    def get_member_object(self, index):
        """Instantiates a member object for a given index."""
        buf = self.get_buffer(index)
        operand = self.get_operand(index)
        return self.member_type(self.tag, buf, operand)

    def get_buffer(self, index):
        """Creates a buffer containing the raw data for a given index.

        The resulting buffer is not necessarily a single element, but rather
        all the elements contained by the array defined by the existing
        subarray indices. For example, if this object is a 2x2 array, the
        subarray indices are empty, then given index contains 2 elements:
        [index,0] and [index,1].
        """
        # The number of dimensions currently consumed are those present
        # in parent arrays plus the one represented by the given index.
        num_dim = len(self.subarray_dim) + 1

        # Determine which dimensions remain unspecified.
        remaining_dim = self.shape[:-num_dim]

        # Compute the size of the buffer represented by the given index,
        # which is the product of all unspecified dimensions and the
        # base type size.
        num_bytes = functools.reduce(operator.mul, remaining_dim,
                                     self.member_type.raw_size)

        start = num_bytes * index
        end = start + num_bytes
        return memoryview(self.raw_data)[start:end]


class BoolRawSize(object):
    """
    Descriptor class to compute the raw storage size of a BOOL array that
    is part of a UDT.

    Since BOOLs are always packed into blocks of 4 bytes(32 bits), the raw
    size is simply the number of bytes. Integer division is also ok because
    the number of BOOLs is always an integer multiple of 8.
    """

    def __get__(self, instance, cls):
        dim = cls.get_dim()
        return dim[0] // 8


class BoolArray(Base):
    """Base class for arrays of BOOL.

    BOOL arrays do not store their elements separately, but rather pack
    them into bytes where each BOOL member is an alias to a single bit,
    i.e, BOOL[32] is 4 bytes, not 32. Also, BOOL arrays are restricted to a
    single dimension that is an integer multiple of 32.
    """

    raw_size = BoolRawSize()

    def get_member_object(self, index):
        """Creates a BOOL object targeting a given index."""
        buf = atomic.BOOL.get_bit_buffer(self.raw_data, index)
        bit = atomic.BOOL.get_bit_position(index)
        operand = self.get_operand(index)
        return self.member_type(self.tag, buf, operand, bit)


class SubarrayDescription(object):
    """Descriptor class for subarray descriptions.

    Raises an exception for an attempts to access descriptions because
    RSLogix does not support commenting subarrays; only individual elements
    may have descriptions.
    """
    e = TypeError
    msg = 'Descriptions for subarrays are not supported'

    def __get__(self, array, owner=None):
        raise self.e(self.msg)

    def __set__(self, array, value):
        raise self.e(self.msg)


class Subarray(object):
    """Mixin class representing a portion of an array.

    Subarray objects are created when a multidimensional array is indexed,
    but the given indices do not yet satisfy all the array's dimensions.
    For example, consider a tag array defined with the dimensions [5, 4, 3],
    tag[0] would be a subarray with the dimensions [4, 3].
    """

    # Override for the superclass description attribute.
    description = SubarrayDescription()
