"""
Objects implementing tag access.
"""

from l5x import dom
import copy
import itertools
import xml.etree.ElementTree as ElementTree


class Scope(object):
    """Container to hold a group of tags within a specific scope."""
    def __init__(self, element, prj, lang):
        self.element = element
        tag_element = element.find('Tags')
        self.tags = dom.ElementDict(tag_element, 'Name', Tag,
                                    value_args=[prj, lang])


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


class Data(object):
    """
    Base class for subclasses that handle the two ways data can be
    instantiated:

    1. As a top-level tag. The term top-level is used here to indicate the
       data is the complete tag; it does not refer to the tag's scope,
       controller or program. Depending on the data type, a top-level tag
       may contain members, which are handled by case 2.

    2. As a member of a composite data type. This includes array items
       and structure(UDT) members. These can be nested to any depth where
       one member contains additional members, such as would occur if a UDT
       with an array member. All member instances are ultimately part of one
       top-level tag instance, described in case 1.

    These two subclasses only handle details on how the data is instantiated;
    they do not define any specifics regarding the type of data. They must
    be combined with other mixin classes which define an actual data type
    or array; the resulting class is then instantiated to represent an
    actual piece of data.
    """

    data_type = dom.AttributeDescriptor('DataType', True)


class Tag(Data):
    """Mixin class for data instantiated as a top-level tag."""

    description = dom.ElementDescription(['ConsumeInfo'])
    producer = ConsumeDescriptor('Producer')
    remote_tag = ConsumeDescriptor('RemoteTag')

    # Operands are only used to identify comments for submembers, not
    # top-level tags, so this is defined as an empty string for all
    # tag instances.
    operand = ''

    def __new__(cls, element, prj, lang):
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
        else:
            data_type = prj.get_data_type(element)
            name = ' '.join(('Tag', element.attrib['Name']))
            tag_cls = type(name, (cls, data_type), {})
            tag = object.__new__(tag_cls)
            tag.__init__(element, prj, lang)
            return tag

    def __init__(self, element, prj, lang):
        self.element = element
        self.lang = lang
        self.raw_data = prj.get_tag_data_buffer(element)

        # Call the constructor for the mixin class handling the data type.
        # The mixin class's __init__ method must define default values for
        # any parameters because none are provided when instantiated as a
        # top-level tag.
        super().__init__()

    @property
    def tag(self):
        """Self-reference for operations that need the parent tag attribute."""
        return self


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


class Member(Data):
    """Mixin class for data that is part of a composite data type."""

    description = Comment()

    def __init__(self, tag, raw_data, operand, *args):
        self.tag = tag
        self.raw_data = raw_data
        self.operand = operand

        # Pass any additional arguments to the mixin class specific to the
        # data type being constructed.
        super().__init__(*args)


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
