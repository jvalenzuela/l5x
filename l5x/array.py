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
