"""
This module contains items for implementing tag arrays, both for top-level
tags and UDT array members.
"""

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


class Base(object):
    """Base class for all array types."""

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
        num_elements = functools.reduce(operator.mul, dim)
        element_size = num_elements * cls.member_type.raw_size

        # Array sizes are rounded up to a 32-bit boundry.
        tail_pad = (4 - (element_size % 4)) % 4

        return element_size + tail_pad


class Array(Base):
    """Base class for arrays of all types except BOOL."""

    raw_size = RawSize()


class BoolRawSize(object):
    """
    Descriptor class to compute the raw storage size of a BOOL array that
    is part of a UDT.

    Since BOOLs are always packed into blocks of 4 bytes(32 bits), the raw
    size is simply the number of bytes. Integer division is also ok because
    the number of bits is always an integer multiple of 8.
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
