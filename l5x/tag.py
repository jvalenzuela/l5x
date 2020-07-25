"""
Objects implementing tag access.
"""

from l5x import dom
import copy
import ctypes
import itertools
import xml.etree.ElementTree as ElementTree


class Scope(object):
    """Container to hold a group of tags within a specific scope."""
    def __init__(self, element, lang):
        self.element = element
        tag_element = element.find('Tags')
        self.tags = dom.ElementDict(tag_element, 'Name', Tag,
                                    value_args=[lang])


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
        """Returns the current consumed tag property."""
        self.check_consumed(tag)
        info = self.get_info(tag)
        return info.attrib[self.attr]
        
    def __set__(self, tag, value):
        """Sets a new consumed tag property."""
        self.check_consumed(tag)
        
        # Producer names must be non-empty strings.
        if not isinstance(value, str):
            raise TypeError('Producer must be a string')
        if len(value) == 0:
            raise ValueError('Producer string cannot be empty')

        info = self.get_info(tag)
        info.attrib[self.attr] = value

    def check_consumed(self, tag):
        """Verifies this is a consumed tag."""
        if tag.element.attrib['TagType'] != 'Consumed':
            raise TypeError("Tag {0} is not a consumed tag".format(
                tag.element.attrib['Name']))

    def get_info(self, tag):
        """Retrieves the ConsumeInfo XML element."""
        return tag.element.find('ConsumeInfo')


class Tag(object):
    """Base class for a single tag."""
    description = dom.ElementDescription(['ConsumeInfo'])
    data_type = dom.AttributeDescriptor('DataType', True)
    value = TagDataDescriptor('value')
    shape = TagDataDescriptor('shape')
    names = TagDataDescriptor('names')
    producer = ConsumeDescriptor('Producer')
    remote_tag = ConsumeDescriptor('RemoteTag')

    def __new__(cls, element, lang):
        """
        Intercepts the creation of a new tag object to determine if
        the target tag is an alias, in which case an alias tag object
        is returned instead of a Tag.
        """
        if element.attrib['TagType'] == 'Alias':
            alias = object.__new__(AliasTag)
            alias.__init__(element, lang)
            return alias

        # Normal base tag; return an instance of this class.
        return object.__new__(cls)

    def __init__(self, element, lang):
        self.element = element
        self.lang = lang
        data_class = base_data_types.get(self.data_type, Structure)
        self.data = data_class(self.get_data_element(), self)

    def get_data_element(self):
        """Returns the decorated data XML element.

        This is always the sole element contained with the decorated Data
        element.
        """
        data = self.element.find("Data[@Format='Decorated']/*")

        if data is None:
            name = self.element.attrib['Name']
            raise RuntimeError("Decoded data content not found for {0} tag. "
                               "Ensure Encode Source Protected Content option "
                               "is disabled when saving L5X.".format(name))

        return data

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
        """Removes any data elements other than decorated.
        
        Called anytime a data value is set to avoid conflicts with
        modified decorated data elements.
        """
        undecorated_data = []
        for e in self.element.iterfind('Data'):
            try:
                format = e.attrib['Format']
            except KeyError:
                undecorated_data.append(e)
            else:
                if format != 'Decorated':
                    undecorated_data.append(e)

        [self.element.remove(e) for e in undecorated_data]


class AliasFor(object):
    """Descriptor class to access the AliasFor attribute."""
    def __get__(self, tag, owner=None):
        return tag.element.attrib['AliasFor']

    def __set__(self, tag, value):
        if not isinstance(value, str):
            raise TypeError('Alias tag name must be a string.')
        if not value.strip():
            raise ValueError('Alias tag name must be a non-empty string.')
        tag.element.attrib['AliasFor'] = value
        self.remove_operand_comments(tag)

    def remove_operand_comments(self, tag):
        """Deletes any comments for the tag's operands.

        This is done because the new alias target data type is unknown,
        and comments from previous operands may not be valid for the
        new tag.
        """
        comments = tag.element.find('Comments')
        if comments is not None:
            tag.element.remove(comments)


class AliasTag(object):
    """Handler for accessing alias tags."""
    description = dom.ElementDescription()
    alias_for = AliasFor()

    def __init__(self, element, lang):
        self.element = element
        self.lang = lang


class Comment(object):
    """Descriptor class for accessing descriptions of individual tag members.

    These descriptions are stored in the Comments element directly under
    the enclosing Tag element. The instance's operand attribute is used
    to find the correct Comment element.
    """
    def __get__(self, instance, owner=None):
        """Returns the data's description."""
        # Acquire the overall Comments parent element.
        comments = instance.tag.element.find('Comments')
        if comments is None:
            return None

        # Locate the Comment child with the matching operand.
        try:
            element = self.get_comment_element(instance, comments)
        except KeyError:
            return None

        cdata = dom.get_localized_cdata(element, instance.tag.lang)
        if cdata is None:
            return None
        return str(cdata)

    def __set__(self, instance, value):
        """Updates, creates, or removes a comment."""
        if value is not None:
            if self.__get__(instance) is None:
                self.create(instance, value)
            else:
                self.modify(instance, value)
        else:
            self.delete(instance)

    def create(self, instance, text):
        """Creates a new comment."""
        # Get the parent Comments element, creating one if necessary.
        comments = instance.tag.element.find('Comments')
        if comments is None:
            comments = self.create_comments(instance)

        # Find or create a Comment element with matching operand to store
        # the new comment text.
        try:
            # Single-language projects will not have an existing Comment
            # element because no localized comments are possible in other
            # languages.
            if instance.tag.lang is None:
                raise KeyError()

            # A matching Comment element may already exist in multilanguage
            # projects, containing comments in other languages.
            else:
                comment = self.get_comment_element(instance, comments)

        # Create a new Comment element with the target operand.
        except KeyError:
            comment = ElementTree.SubElement(comments, 'Comment',
                                             {'Operand':instance.operand})

        dom.create_localized_cdata(comment, instance.tag.lang, text)

    def modify(self, instance, text):
        """Alters an existing comment."""
        comments_parent = instance.tag.element.find('Comments')
        comment = self.get_comment_element(instance, comments_parent)
        dom.modify_localized_cdata(comment, instance.tag.lang, text)

    def delete(self, instance):
        """Removes a comment."""
        # Acquire the overall Comments parent element.
        comments = instance.tag.element.find('Comments')
        if comments is None:
            return

        # Locate the Comment child with the matching operand.
        try:
            comment = self.get_comment_element(instance, comments)
        except KeyError:
            return

        # Remove the Comment or LocalizedComment containing the actual text.
        dom.remove_localized_cdata(comments, comment, instance.tag.lang)

        # Remove the entire Comments parent element if no other comments for any
        # operands remain.
        if len(comments) == 0:
            instance.tag.element.remove(comments)

    def create_comments(self, instance):
        """Creates a new Comments container element.

        Used if the top-level tag element did not contain a Comments element.
        The Comments element must be located immediately before any Data
        elements.
        """
        comments = ElementTree.Element('Comments')

        # Locate the index of the Data child element.
        child_tags = [e.tag for e in instance.tag.element.iterfind('*')]
        data_index = child_tags.index('Data')

        instance.tag.element.insert(data_index, comments)
        return comments

    def get_comment_element(self, instance, comments):
        """Acquires the Comment element of the instance's operand."""
        path = "Comment[@Operand='{0}']".format(instance.operand)
        element = comments.find(path)
        if element is None:
            raise KeyError()
        return element


class Data(object):
    """Base class for objects providing access to tag values and comments."""
    description = Comment()

    def __new__(cls, *args, **kwds):
        """
        Intercepts creation of a new data object if the XML element
        indicates it is an array, in which case an array access object
        is created instead for the given data type.
        """
        if args[0].tag.startswith('Array'):

            # Two array accessor types are possible depending on if the
            # the array is a structure member.
            if args[0].tag == ('ArrayMember'):
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
        self.element = element
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
            # One of two possible XML attributes determine how this data is
            # identified.
            try:
                # Array members use the Index attribute, which is appended to
                # the operand string without an additional separator; the
                # enclosing square brackets are included in the attribute
                # value.
                operand = self.element.attrib['Index']
                sep = ''
            except KeyError:
                # All other operands use the Name attribute, which is
                # separated from other operands by a dot.
                operand = self.element.attrib['Name']
                sep = '.'
                
            self.operand = sep.join((self.parent.operand, operand.upper()))


class IntegerValue(object):
    """Descriptor class for accessing an integer's value."""
    def __get__(self, instance, owner=None):
        return int(instance.element.attrib['Value'])

    def __set__(self, instance, value):
        """Sets a new value."""
        if (not isinstance(value, int)) or isinstance(value, bool):
            raise TypeError('Value must be an integer')
        if (value < instance.value_min) or (value > instance.value_max):
            raise ValueError('Value out of range')
        instance.element.attrib['Value'] = str(value)
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
        return float(instance.element.attrib['Value'])

    def __set__(self, instance, value):
        if not isinstance(value, float):
            raise TypeError('Value must be a float')

        # Check for NaN and infinite values.
        try:
            value.as_integer_ratio()
        except (OverflowError, ValueError):
            raise ValueError('NaN and infinite values are not supported')
            
        instance.element.attrib['Value'] = str(value)
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
        if element.tag == 'Element':
            self.element = element.find('Structure')

        self.members = dom.ElementDict(self.element, 'Name', base_data_types,
                                   'DataType', Structure,
                                   value_args=[tag, self])

    def __getitem__(self, member):
        """Indexing a structure yields an individual member."""
        if not isinstance(member, str):
            raise TypeError('Structure indices must be strings')
        return self.members[member]


class ArrayValue(object):
    """Descriptor class for accessing multiple values in an array."""
    def __get__(self, array, owner=None):
        dim = len(array.shape) - len(array.address) - 1
        return [array[i].value for i in range(array.shape[dim])]

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
        dims = [int(d) for d in array.element.attrib['Dimensions'].split(',')]

        # Dimensions are stored most-significant first(Dim2, Dim1, Dim0) in the
        # XML attribute; reversing them makes DimX = shape[X].
        dims.reverse()

        return tuple(dims)

    def __set__(self, array, value):
        # Prevent resizing UDT array members.
        if not array.element.tag == 'Array':
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
        self.address = address

        # Array members are identified in XML by the Index attribute,
        # not element order, and may include more than one dimension, so
        # the usual list-type access does not suffice. The object initialized
        # here builds a dictionary of child elements(array members) keyed
        # by the Index attribute that can then be accessed with traditional
        # array notation.
        self.members = dom.ElementDict(self.element, 'Index', self.data_class,
                                       value_args=[self.tag, self])

    def __getitem__(self, index):
        """Returns an access object for the given index.

        Multidimensional arrays will return new Array objects with the
        accumulated address until all dimensions are satisfied, which
        will then return the data access object for that item.
        """
        if not isinstance(index, int):
            raise TypeError('Array indices must be integers')

        # Add the given index to the current accumulated address.
        dim = len(self.shape) - len(self.address) - 1
        if (index < 0) or (index >= self.shape[dim]):
            raise IndexError('Array index out of range')
        new_address = list(self.address)
        new_address.insert(0, index)

        # If the newly formed address set satisifies all dimensions
        # return an access object for the member.
        if len(new_address) == len(self.shape):
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
        self.set_dimensions(new_shape)
        self.tag.clear_raw_data()

        # Make a copy of the first element before stripping all old values.
        template = self.element.find('Element')

        self.remove_elements()

        # Generate new elements based on a new set of indices.
        indices = self.build_new_indices(new_shape)
        [self.append_element(template, i) for i in indices]

    def set_dimensions(self, shape):
        """Updates the Dimensions attributes with a given shape.

        Array tag elements have two dimension attributes: one in the top-level
        Tag element, and another in the Array child element.
        """
        new = list([str(x) for x in shape])
        new.reverse() # Logix lists dimensions most-significant first.

        # Top-level Tag element uses space for separators.
        value = ' '.join(new)
        self.tag.element.attrib['Dimensions'] = value

        # Array element uses comma for separators.
        value = ','.join(new)
        self.element.attrib['Dimensions'] = value

    def remove_elements(self):
        """Deletes all (array)Element elements."""
        [self.element.remove(e) for e in self.element.findall('*')]

    def build_new_indices(self, shape):
        """Constructs a set of all indices for a given array shape."""
        indices = [range(x) for x in shape]
        indices.reverse() # Indices are listed most-significant first.
        return itertools.product(*indices)

    def append_element(self, template, index):
        """Generates and appends a new element from a template."""
        new = copy.deepcopy(template)
        index_attr = "[{0}]".format(','.join([str(i) for i in index]))
        new.attrib['Index'] = index_attr
        self.element.append(new)


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
