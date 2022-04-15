"""
This module contains items for implementing tag arrays, both for top-level
tags and UDT array members.
"""


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
