"""

"""

from .dom import (ElementAccess, ElementDict, AttributeDescriptor,
                  ElementDescription, CDATAElement)
import ctypes


class Scope(ElementAccess):
    """Container to hold a group of tags within a specific scope."""
    def __init__(self, element):
        ElementAccess.__init__(self, element)
        tag_element = self.get_child_element('Tags')
        self.tags = ElementDict(tag_element, 'Name', Tag)


class Value(object):
    """Descriptor class for accessing a tag's top-level value."""
    def __get__(self, tag, owner=None):
        return tag.data.value

    def __set__(self, tag, value):
        tag.data.value = value


class Shape(object):
    """Descriptor class for accessing array tags' shape attribute."""
    def __get__(self, tag, owner=None):
        return tag.data.shape


class Tag(ElementAccess):
    """Base class for a single tag."""
    description = ElementDescription()
    value = Value()
    shape = Shape()
    data_type = AttributeDescriptor('DataType', True)

    def __init__(self, element):
        ElementAccess.__init__(self, element)

        data_class = base_data_types.get(self.data_type, Structure)
        self.data = data_class(self.get_data_element(), self)

    def get_data_element(self):
        """Returns the decorated data XML element.

        This is always the sole element contained with the decorated Data
        element.
        """
        for e in self.child_elements:
            if ((e.tagName == 'Data')
                and (e.getAttribute('Format') == 'Decorated')):
                return ElementAccess(e).child_elements[0]

    def __getitem__(self, key):
        """
        Indices are passed to the data object to access members of compound
        data types.
        """
        return self.data[key]

    def __len__(self):
        """ """
        return len(self.data)

    def clear_raw_data(self):
        """Removes the unformatted data element.
        
        Called anytime a data value is set to avoid conflicts with
        modified decorated data elements.
        """
        for e in self.child_elements:
            if (e.tagName == 'Data') and (not e.getAttribute('Format')):
                data = self.element.removeChild(e)
                data.unlink()


class Comment(object):
    """Descriptor class for accessing descriptions of individual tag members.

    These descriptions are stored in the Comments element directly under
    the enclosing Tag element. The instance's operand attribute is used
    to find the correct Comment element.
    """
    def __get__(self, instance, owner=None):
        """Returns the data's description."""
        try:
            comments = self.get_comments(instance)
        except AttributeError:
            return None

        try:
            element = self.get_comment_element(instance, comments)
        except KeyError:
            return None

        return str(CDATAElement(element))

    def __set__(self, instance, value):
        """ """
        # Get the enclosing Comments element, creating one if necessary.
        try:
            comments = self.get_comments(instance)
        except AttributeError:
            comments = self.create_comments(instance)

        # Find the matching Comment element and set the new text
        # or create a new Comment if none exists.
        try:
            element = self.get_comment_element(instance, comments)
        except KeyError:
            cdata = CDATAElement(parent=comments, name='Comment',
                                 attributes={'Operand':instance.operand})
            comments.element.appendChild(cdata.element)
        else:
            cdata = CDATAElement(element)

        cdata.set(value)

    def get_comments(self, instance):
        """Acquires an access object for the tag's Comments element."""
        try:
            element =  instance.tag.get_child_element('Comments')
        except KeyError:
            raise AttributeError()

        return ElementAccess(element)

    def create_comments(self, instance):
        """Creates a new Comments container element.

        Used if the top-level tag element did not contain a Comments element.
        The Comments element must be located immediately before any Data
        elements.
        """
        new = instance.create_element('Comments')
        data = instance.tag.get_child_element('Data')
        instance.tag.element.insertBefore(new, data)
        return ElementAccess(new)

    def get_comment_element(self, instance, comments):
        """Acquires the Comment element of the instance's operand."""
        for element in comments.child_elements:
            if element.getAttribute('Operand') == instance.operand:
                return element

        raise KeyError()


class Data(ElementAccess):
    """Base class for objects providing access to tag values and comments."""
    description = Comment()

    # XML attribute names that contain the string used to build the operand.
    # The type of attribute also determines the separator character used
    # to concentate the operand with the parent's: array indices use nothing
    # and everything else uses a dot.
    operand_attributes = {'Name':'.', 'Index':''}

    def __new__(cls, *args, **kwds):
        """
        Intercepts creation of a new data object if the XML element
        indicates it is an array, in which case an array access object
        is created instead for the given data type.
        """
        if args[0].tagName == 'Array':
            array = object.__new__(Array, *args, **kwds)
            array_args = [cls]
            array_args.extend(args)
            array.__init__(*array_args, **kwds)
            return array

        else:
            return object.__new__(cls, *args, **kwds)

    def __init__(self, element, tag, parent=None):
        """

        """
        ElementAccess.__init__(self, element)
        self.tag = tag
        self.parent = parent
        self.build_operand()

    def build_operand(self):
        """Constructs the identifier for comment operands.

        A tag's top-level data type has no parent and does not require
        an operand; it's description is placed in the dedicated Description
        element. These objects get an empty operand string for child
        members to use.

        Operands for sub-members are formed by appending their name
        to their parent's operand. Names are converted to upper-case
        because Logix uses only capital letters in operand attributes
        for some reason.
        """
        if self.parent is None:
            self.operand = ''
        else:
            for attr in self.operand_attributes.keys():
                if self.element.hasAttribute(attr):
                    sep = self.operand_attributes[attr]
                    name = self.element.getAttribute(attr).upper()
                    break
                
            self.operand = sep.join((self.parent.operand, name))


class IntegerValue(object):
    """Descriptor class for accessing an integer's value."""
    def __get__(self, instance, owner=None):
        return int(instance.element.getAttribute('Value'))

    def __set__(self, instance, value):
        """Sets a new value."""
        if not isinstance(value, int):
            raise TypeError('Value must be an integer')
        if (value < instance.value_min) or (value > instance.value_max):
            raise ValueError('Value out of range')
        instance.element.setAttribute('Value', str(value))
        instance.tag.clear_raw_data()


class Integer(Data):
    """Base class for integer data types.

    In addition to the usual value and description access, numeric indices
    are used for bit-level references.
    """
    value = IntegerValue()

    def __getitem__(self, bit):
        """Gets an object to access a single bit."""
        self.validate_bit_number(bit)
        return Bit(self.element, self.tag, self, bit)

    def validate_bit_number(self, bit):
        """Verifies a given bit index is within range."""
        if (bit < 0) or (bit >= self.bits):
            raise IndexError('Bit index out of range')

    def __len__(self):
        """Returns the width of the integer."""
        return self.bits


class SINT(Integer):
    """ """
    bits = 8
    ctype = ctypes.c_int8
    value_min = -128
    value_max = 127


class INT(Integer):
    """ """
    bits = 16
    ctype = ctypes.c_int16
    value_min = -32768
    value_max = 32767


class DINT(Integer):
    """ """
    bits = 32
    ctype = ctypes.c_int32
    value_min = -2147483648
    value_max = 2147483647


class BitValue(object):
    """Descriptor class for values of individual integer bits.

    Bit access utilizes exact-width, signed ctype integers for
    bit-level operations which are then translated back to the parent
    integer's value. This ensures correct results when the sign bit
    is accessed.
    """
    def __get__(self, bit, owner=None):
        cvalue = self.get_ctype(bit)
        if cvalue.value & bit.mask.value:
            return 1
        else:
            return 0

    def __set__(self, bit, bit_value):
        if not isinstance(bit_value, int):
            raise TypeError('Bit values must be integers')
        elif (bit_value < 0) or (bit_value > 1):
            raise ValueError('Bit values may only be 0 or 1')

        cvalue = self.get_ctype(bit)
        if bit_value:
            cvalue.value |= bit.mask.value
        else:
            cvalue.value &= ~bit.mask.value
        bit.parent.value = int(cvalue.value)

    def get_ctype(self, bit):
        """Returns the parent integer's value as a ctype."""
        return bit.parent.ctype(bit.parent.value)


class Bit(Data):
    """Provides access to individual bits within an integer."""
    value = BitValue()
    description = Comment()

    def __init__(self, element, tag, parent, bit):
        self.bit = bit
        Data.__init__(self, element, tag, parent)
        self.mask = parent.ctype(1 << bit)

    def build_operand(self):
        """Method override to create an operand based on the bit number."""
        self.operand = '.'.join((self.parent.operand, str(self.bit)))


class BOOL(Data):
    """Tag access for BOOL data types."""
    value = IntegerValue()
    value_min = 0
    value_max = 1


class RealValue(object):
    """Descriptor class for accessing REAL values."""
    def __get__(self, instance, owner=None):
        return float(instance.element.getAttribute('Value'))

    def __set__(self, instance, value):
        if not isinstance(value, float):
            raise TypeError('Value must be a float')

        # Check for NaN and infinite values.
        try:
            value.as_integer_ratio()
        except (OverflowError, ValueError):
            raise ValueError('NaN and infinite values are not supported')
            
        instance.element.setAttribute('Value', str(value))
        instance.tag.clear_raw_data()


class REAL(Data):
    """Tag access for REAL data types."""
    value = RealValue()


class StructureValue(object):
    """Descriptor class for accessing multiple structure values.

    Values are expressed as a dictionary with member names as keys.
    """
    def __get__(self, struct, owner=None):
        member_names = struct.members.names
        return dict(zip(member_names, [struct[m].value for m in member_names]))

    def __set__(self, struct, value):
        if not isinstance(value, dict):
            raise TypeError('Value must be a dictionary')
        for m in value.keys():
            struct[m].value = value[m]
        struct.tag.clear_raw_data()


class Structure(Data):
    """Accessor class for structured data types."""
    value = StructureValue()

    def __init__(self, element, tag, parent=None):
        Data.__init__(self, element, tag, parent)
        self.members = ElementDict(element, 'Name', base_data_types,
                                   'DataType', Structure,
                                   member_args=[tag, self])

    def __getitem__(self, member):
        """Indexing a structure yields an individual member."""
        if not isinstance(member, str):
            raise TypeError('Structure indices must be strings')
        return self.members[member]


class ArrayValue(object):
    """Descriptor class for accessing multiple values in an array."""
    def __get__(self, array, owner=None):
        dim = len(array.dims) - len(array.address) - 1
        return [array[i].value for i in range(array.dims[dim])]

    def __set__(self, array, value):
        if not isinstance(value, list):
            raise TypeError('Value must be a list')
        if len(value) > array.shape[len(array.shape) - len(array.address) - 1]:
            raise IndexError('Source list is too large')

        for i in range(len(value)):
            array[i].value = value[i]

        array.tag.clear_raw_data()


class ArrayDescription(Comment):
    """Descriptor class array descriptions.

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


class ArrayShape(object):
    """Descriptor class to acquire an array's dimensions."""
    def __get__(self, array, owner=None):
        return tuple(array.dims)


class Array(Data):
    """Access object for arrays of any data type.

    """
    value = ArrayValue()
    description = ArrayDescription()
    shape = ArrayShape()

    def __init__(self, data_class, element, tag, parent=None, address=[]):
        Data.__init__(self, element, tag, parent)
        self.data_class = data_class
        self.dims = [int(d) for d in
                     element.getAttribute('Dimensions').split(',')]
        self.dims.reverse()
        self.address = address
        self.members = ElementDict(element, 'Index', data_class,
                                   member_args=[tag, self])

    def __getitem__(self, index):
        """Returns an access object for the given index.

        Multidimensional arrays will return new Array objects with the
        accumulated address until all dimensions are satisfied, which
        will then return the data access object for that item.
        """
        if not isinstance(index, int):
            raise TypeError('Array indices must be integers')

        # Add the given index to the current accumulated address.
        dim = len(self.dims) - len(self.address) - 1
        if (index < 0) or (index >= self.dims[dim]):
            raise IndexError('Array index out of range')
        new_address = list(self.address)
        new_address.insert(0, index)

        # If the newly formed address set satisifies all dimensions
        # return an access object for the member.
        if len(new_address) == len(self.dims):
            # Address values are reversed because the display order is
            # most-significant first.
            new_address.reverse()

            key = "[{0}]".format(','.join([str(i) for i in new_address]))
            return self.members[key]

        # The new address does not yet specify a single element if the key
        # was not found. Return a new array access object to handle
        # access to the new address by instantiating the data type,
        # which will result in an Array instance through Data.__new__().
        else:
            return self.data_class(self.element, self.tag, self.parent,
                                   new_address)

    
base_data_types = {'SINT':SINT,
                   'INT':INT,
                   'DINT':DINT,
                   'BOOL':BOOL,
                   'REAL':REAL}
