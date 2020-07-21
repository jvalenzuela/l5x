"""
Internal XML DOM helper inteface objects.
"""

import xml.etree.ElementTree as ElementTree


# Logix uses CDATA sections to enclose certain content, such as rung
# comments and tag descriptions. This inappropriate use of CDATA is
# difficult to maintain when parsing and generating XML as CDATA is not
# intended to be used as semantic markup. Without special handling only
# possible with the DOM API, these CDATA sections are merged into the
# surrounding text, which then does not import correctly into Logix.
# To simplify the application and allow use of the ElementTree API,
# CDATA sections are converted into normal elements before parsing,
# then back to CDATA when the project is written. This is the tag name
# used do enclose the original CDATA content.
CDATA_TAG = 'CDATAContent'


class CDATAElement(object):
    """
    This class manages access to CDATA content contained within a dedicated
    XML element, such as for tag descriptions and comments. An example
    construct would be:

    <parent> <!-- Parent element must already exist. -->

      <!--
      This and its single CDATA child can either be preexisting or
      created by this class.
      -->
      <comment>
        <CDATAContent>Foo Bar</CDATAContent>
      </comment>

    </parent>
    """
    def __init__(self, element=None, parent=None, name=None, attributes={}):
        # Find the CDATA child if a target element was given.
        try:
            self.cdata_element = element.find(CDATA_TAG)

        # Create a new element and CDATA grandchild under the parent if no
        # element was given.
        except AttributeError:
            self.cdata_parent = ElementTree.SubElement(parent, name, attributes)
            self.cdata_element = ElementTree.SubElement(self.cdata_parent,
                                                        CDATA_TAG)

        else:
            self.cdata_parent = element

    def __str__(self):
        """Returns the current string content."""
        if self.cdata_element.text is None:
            return ''
        return self.cdata_element.text

    def set(self, s):
        """Sets the CDATA section content."""
        self.cdata_element.text = s


def get_localized_cdata(parent, language):
    """Retrieves a CDATA string from a parent element."""
    # Single-language projects contain text directly under the parent
    # element.
    if language is None:
        element = parent

    # Multi-language projects keep text for each language in child
    # elements identified by the Lang attribute.
    else:
        path = "*[@Lang='{0}']".format(language)
        element = parent.find(path)
        if element is None:
            return None

    return CDATAElement(element)


def modify_localized_cdata(parent, language, text):
    """Alters CDATA content under a parent element."""
    cdata = get_localized_cdata(parent, language)
    cdata.set(text)


def create_localized_cdata(parent, language, text):
    """Creates new CDATA content under a parent element."""
    # Single-language projects store the CDATA directly under the
    # parent element.
    if language is None:
        ElementTree.SubElement(parent, CDATA_TAG)
        cdata = CDATAElement(parent)

    # Multi-language projects keep the CDATA in localized child elements
    # identified with the Lang attribute.
    else:
        tag_name = ''.join(('Localized', parent.tag))
        attr = {'Lang':language}
        cdata = CDATAElement(parent=parent, name=tag_name, attributes=attr)

    cdata.set(text)


def remove_localized_cdata(grandparent, parent, language):
    """Removes an element containing CDATA content."""
    # For multi-language projects, remove only the child associated
    # with the given language.
    if language is not None:
        cdata = get_localized_cdata(parent, language)
        if cdata is not None:
            parent.remove(cdata.cdata_parent)

    # Remove the entire parent element for single-language projects,
    # or if no comments remain in other languages.
    if (language is None) or (len(parent) == 0):
        grandparent.remove(parent)


class ElementDescription(object):
    """Descriptor class for accessing a top-level Description element.

    Description elements contain a CDATA comment for some type of
    container element, such as a Tag or Module.
    """
    def __init__(self, follow=[]):
        """Store a list of elements which must preceed the description."""
        self.follow = follow

    def __get__(self, instance, owner=None):
        """Returns the current description string."""
        desc = instance.element.find('Description')
        if desc is not None:
            cdata = get_localized_cdata(desc, instance.lang)
            if cdata is not None:
                return str(cdata)

        return None

    def __set__(self, instance, value):
        """Modifies the description text."""
        # Set a new description if given a string value.
        if isinstance(value, str):
            # See if the given description should replace an existing one
            # or be created as an entirely new element.
            if self.__get__(instance) is not None:
                self.modify(instance, value)
            else:
                self.create(instance, value)

        # A value of None removes any existing description.
        elif value is None:
            self.remove(instance)

        else:
            raise TypeError('Description must be a string or None')

    def modify(self, instance, value):
        """Alters the content of an existing description."""
        desc = instance.element.find('Description')
        modify_localized_cdata(desc, instance.lang, value)

    def create(self, instance, value):
        """Creates a new description when one does not previously exist."""

        # The Description element directly contains the text content in
        # single-language projects.
        if instance.lang is None:
            desc = ElementTree.Element('Description')
            self.insert_description(instance, desc)

        # Multi-language projects use localized child elements under
        # Description for each language.
        else:
            # Locate the Description tag, or create a new one if necessary.
            desc = instance.element.find('Description')
            if desc is None:
                desc = ElementTree.Element('Description')
                self.insert_description(instance, desc)

        create_localized_cdata(desc, instance.lang, value)

    def insert_description(self, instance, desc):
        """
        Inserts the Description element as a child of the parent instance
        based on any elements that must come first.
        """
        dest_index = 0 # Default to the first child.

        # Iterate through the child elements looking for any that
        # need to preceed the description.
        i = 0
        for e in instance.element:
            if e.tag in self.follow:
                dest_index = i + 1
            i += 1

        instance.element.insert(dest_index, desc)

    def remove(self, instance):
        """Implements deleting a description."""
        desc = instance.element.find('Description')
        if desc is not None:
            remove_localized_cdata(instance.element, desc, instance.lang)


class AttributeDescriptor(object):
    """Generic descriptor class for accessing an XML element's attribute."""
    def __init__(self, name, read_only=False):
        self.name = name
        self.read_only = read_only

    def __get__(self, instance, owner=None):
        try:
            raw = instance.element.attrib[self.name]
        except KeyError:
            return None
        else:
            return self.from_xml(raw)

    def __set__(self, instance, value):
        if self.read_only is True:
            raise AttributeError('Attribute is read-only')
        new_value = self.to_xml(instance, value)
        if new_value is not None:
            instance.element.attrib[self.name] = new_value

        # Delete the attribute if value is None, ignoring the case if the
        # attribute didn't exist to begin with.
        else:
            try:
                del instance.element.attrib[self.name]
            except KeyError:
                pass

    def from_xml(self, value):
        """Default converter for reading attribute string.

        Can be overridden in subclasses to provide custom conversion.
        """
        return str(value)

    def to_xml(self, instance, value):
        """Default converter for writing attribute string.

        Subclasses may implement custom conversions from user values
        by overriding this method. Must return a string or None.
        """
        if (value is not None) and (not isinstance(value, str)):
            raise TypeError('Value must be a string')
        return value


class ElementDictNames(object):
    """Descriptor class to get a list of an ElementDict's members."""
    def __get__(self, instance, owner=None):
        return [instance.key_type(e.attrib[instance.key_attr])
                for e in instance.parent.iterfind('*')]

    def __set__(self, instance, owner=None):
        """Raises an exception upon an attempt to modify; this is read-only."""
        raise AttributeError('Read-only attribute.')


class ElementDict(object):
    """Container which provides access to a group of XML elements.

    Operates similar to a dictionary where a child element is referenced
    by index notation to find the child with the matching key attribute.
    Instead of returning the actual XML element, a new object is
    instantiated and returned which is used to handle access to the child's
    data.
    """
    names = ElementDictNames()

    def __init__(self, parent, key_attr, value_type, type_attr=None,
                 dfl_type=None, key_type=str, value_args=[]):
        self.parent = parent
        self.key_attr = key_attr
        self.value_type = value_type
        self.type_attr = type_attr
        self.dfl_type = dfl_type
        self.key_type = key_type
        self.value_args = value_args

    def __getitem__(self, key):
        """Return a member class suitable for accessing a child element."""
        xpath = "*[@{0}='{1}']".format(self.key_attr, key)
        element = self.parent.find(xpath)
        if element is None:
            raise KeyError("{0} not found".format(key))
        return self.create_value_object(element)

    def create_value_object(self, element):
        """Instantiates an object returned as the value."""
        args = [element]
        args.extend(self.value_args)

        # Use the same type for all child objects if the given value type
        # is a class.
        try:
            return self.value_type(*args)

        # If the value type is a mapping, use the given attribute to select
        # the appropriate type.
        except TypeError:
            type_name = element.attrib[self.type_attr]
            return self.value_type.get(type_name, self.dfl_type)(*args)
