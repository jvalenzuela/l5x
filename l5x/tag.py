"""
Objects implementing tag access.
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


class TagDataDescriptor(object):
    """Descriptor class to dispatch attribute access to a data object.

    Used by Tag objects to pass access to a specific attribute on to the
    Data element which handles the implementation.
    """
    def __init__(self, attr):
        self.attr = attr

    def __get__(self, tag, owner=None):
        return getattr(tag.data, self.attr)

    def __set__(self, tag, value):
        setattr(tag.data, self.attr, value)


class ConsumeDescriptor(object):
    """Descriptor class for accessing consumed tag properties."""
    def __init__(self, attr):
        self.attr = attr

    def __get__(self, tag, owner=None):
        if self.is_consumed(tag):
            info = self.get_info(tag)
            return str(info.getAttribute(self.attr))

        else:
            raise TypeError('Not a consumed tag')
        
    def __set__(self, tag, value):
        if not self.is_consumed(tag):
            raise TypeError('Not a consumed tag')
        
        # Producer names must be non-empty strings.
        if not isinstance(value, str):
            raise TypeError('Producer must be a string')
        if len(value) == 0:
            raise ValueError('Producer string cannot be empty')

        info = self.get_info(tag)
        info.setAttribute(self.attr, value)

    def is_consumed(self, tag):
        """Checks to see if this is a consumed tag."""
        return tag.element.getAttribute('TagType') == 'Consumed'

    def get_info(self, tag):
        """Retrieves the ConsumeInfo XML element."""
        return tag.get_child_element('ConsumeInfo')


class Tag(ElementAccess):
    """Base class for a single tag."""
    description = ElementDescription(['ConsumeInfo'])
    data_type = AttributeDescriptor('DataType', True)
    value = TagDataDescriptor('value')
    shape = TagDataDescriptor('shape')
    names = TagDataDescriptor('names')
    producer = ConsumeDescriptor('Producer')
    remote_tag = ConsumeDescriptor('RemoteTag')

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
        """Dispatches len queries to the base data type object."""
        return len(self.data)

    def clear_raw_data(self):
        """Removes the unformatted data element.
        
        Called anytime a data value is set to avoid conflicts with
        modified decorated data elements.
        """
        for e in self.child_elements:
            if (e.tagName == 'Data') and (not e.hasAttribute('Format')):
                data = self.element.removeChild(e)
                data.unlink()
                break


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
        """Updates, creates, or removes a comment."""
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

        if value is not None:
            cdata.set(value)
        else:
            comments.element.removeChild(cdata.element)

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
        if args[0].tagName.startswith('Array'):

            # Two array accessor types are possible depending on if the
            # the array is a structure member.
            if args[0].tagName == ('ArrayMember'):
                array_type = ArrayMember
            else:
                array_type = Array

            array = object.__new__(array_type)
            array_args = [cls]
            array_args.extend(args)
            array.__init__(*array_args, **kwds)
            return array

        # Non-array tags return a instance of the original type; an explicit
        # call to __init__ is not required as the returned instance
        # is the original class.
        else:
            return object.__new__(cls)

    def __init__(self, element, tag, parent=None):
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

    In addition to the usual value and description access, integer indices
    are used for bit-level references.
    """
    value = IntegerValue()

    def __getitem__(self, bit):
        """Gets an object to access a single bit."""
        self.validate_bit_number(bit)
        return Bit(self.element, self.tag, self, bit)

    def validate_bit_number(self, bit):
        """Verifies a given bit index is within range."""
        if not isinstance(bit, int):
            raise TypeError('Bit indices must be integers.')
        if (bit < 0) or (bit >= self.bits):
            raise IndexError('Bit index out of range')

    def __len__(self):
        """Returns the width of the integer."""
        return self.bits


class SINT(Integer):
    """Base class for 8-bit signed integers."""
    bits = 8
    ctype = ctypes.c_int8
    value_min = -128
    value_max = 127


class INT(Integer):
    """Base class for 16-bit signed integers."""
    bits = 16
    ctype = ctypes.c_int16
    value_min = -32768
    value_max = 32767


class DINT(Integer):
    """Base class for 32-bit signed integers."""
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


class StructureNames(object):
    """Descriptor class for accessing structure member names."""
    def __get__(self, struct, owner=None):
        return struct.members.names

    def __set__(self, struct, owner=None):
        raise AttributeError('Read-only attribute.')


class Structure(Data):
    """Accessor class for structured data types."""
    value = StructureValue()
    names = StructureNames()

    def __init__(self, element, tag, parent=None):
        Data.__init__(self, element, tag, parent)

        # If this structure is an array member the given XML element
        # is just the enclosing array member; the XML element directly
        # holding the structure's data is the first child: a Structure
        # XML element.
        if element.tagName == 'Element':
            self.element = self.get_child_element('Structure')

        self.members = ElementDict(self.element, 'Name', base_data_types,
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

    def __set__(self, array, value):
        # Prevent resizing UDT array members.
        if not array.element.tagName == 'Array':
            raise AttributeError('Member arrays cannot be resized.')

        self.check_shape(value)
        array.resize(value)

    def check_shape(self, shape):
        """Validates a new target shape before resizing."""
        if not isinstance(shape, tuple):
            raise TypeError('Array shape must be a tuple')

        dims = len(shape)
        if (dims < 1) or (dims > 3):
            raise ValueError('Arrays must have between 1 and 3 dimensions')

        for d in shape:
            if not isinstance(d, int):
                raise TypeError('Array dimensions must be integers')

            if d < 1:
                raise ValueError('Array dimension must be >= 1')


class Array(Data):
    """Access object for arrays of any data type."""
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

    def resize(self, new_shape):
        """Alters the array's size."""
        self.dims = new_shape
        self.set_dimensions(new_shape)
        self.tag.clear_raw_data()

        # Make a copy of the first element before stripping all old values.
        template = self.get_child_element('Element').cloneNode(True)

        self.remove_elements()

        # Generate new elements based on a new set of indices.
        indices = self.build_new_indices(new_shape)
        [self.append_element(template, i) for i in indices]

        template.unlink()

    def set_dimensions(self, shape):
        """Updates the Dimensions attributes with a given shape.

        Array tag elements have two dimension attributes: one in the top-level
        Tag element, and another in the Array child element.
        """
        new = list([str(x) for x in shape])
        new.reverse() # Logix lists dimensions most-significant first.

        # Top-level Tag element uses space for separators.
        value = ' '.join(new)
        self.tag.element.setAttribute('Dimensions', value)

        # Array element uses comma for separators.
        value = ','.join(new)
        self.element.setAttribute('Dimensions', value)

    def remove_elements(self):
        """Deletes all (array)Element elements."""
        for e in self.child_elements:
            self.element.removeChild(e)
            e.unlink()

    def build_new_indices(self, shape):
        """Constructs a set of indices based on a given array shape.

        This method recursively iterates through every value of every
        dimension. The returned list contains every index combination
        ordered by iterating through dimensions from least to
        most-significant. This order is important because Logix requires
        indices to be arranged in this manner.
        """
        # Extract the most-significant dimension to iterate though, returning
        # an empty list if all dimension levels have been consumed.
        try:
            dim = shape[-1]
        except IndexError:
            return []

        indices = []
        for i in range(dim):

            # If additional dimension levels remain, create indices
            # for each combination.
            next = self.build_new_indices(shape[:-1])
            for j in next:
                l = [i]
                l.extend(j)
                indices.append(l)

            # If only one dimension level was given, the index contains
            # only the dimension's current value.
            if not next:
                indices.append([i])

        return indices

    def append_element(self, template, index):
        """Generates and appends a new element from a template."""
        new = template.cloneNode(True)
        index_attr = "[{0}]".format(','.join([str(i) for i in index]))
        new.setAttribute('Index', index_attr)
        self.element.appendChild(new)


class ArrayMember(Array):
    """Access object for arrays which are structure members.

    Permits access to a description for the entire member. Preventing
    comments for subarrays is unnecessary as array members may only be
    one-dimensional.
    """
    description = Comment()

    
base_data_types = {'SINT':SINT,
                   'INT':INT,
                   'DINT':DINT,
                   'BOOL':BOOL,
                   'REAL':REAL}
