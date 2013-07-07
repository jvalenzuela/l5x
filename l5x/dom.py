"""
Internal XML DOM helper inteface objects.
"""

import xml.dom


class ChildElements(object):
    """Descriptor class to acquire a list of child elements."""
    def __get__(self, accessor, owner=None):
        nodes = accessor.element.childNodes
        return [n for n in nodes if n.nodeType == n.ELEMENT_NODE]

        
class ElementAccess(object):
    """Generic base interface for accessing an XML element."""
    child_elements = ChildElements()

    def __init__(self, element):
        self.element = element
        self.get_doc()

    def get_doc(self):
        """Extracts a reference to the top-level XML document."""
        node = self.element
        while node.parentNode != None:
            node = node.parentNode
        self.doc = node

    def get_child_element(self, name):
        """Finds a child element with a specific tag name."""
        for e in self.child_elements:
            if (e.tagName == name):
                return e

        raise KeyError()

    def create_element(self, name, attributes={}):
        """Wrapper to create a new element with a set of attributes."""
        new = self.doc.createElement(name)
        for attr in attributes.keys():
            new.setAttribute(attr, attributes[attr])
        return new

    def append_child(self, node):
        """Appends a node to the element's set of children."""
        self.element.appendChild(node)


class CDATAElement(ElementAccess):
    """
    This class manages access to CDATA content contained within a dedicated
    XML element. Examples of uses are tag descriptions and comments.
    """
    def __init__(self, element=None, parent=None, name=None, attributes={}):
        """
        When instantiated this can access an existing element or create
        a new one.
        """
        if element is not None:
            ElementAccess.__init__(self, element)
            self.get_existing()
        else:
            element = parent.create_element(name, attributes)
            ElementAccess.__init__(self, element)

            # Add the child CDATA section.
            self.node = parent.doc.createCDATASection('')
            self.append_child(self.node)

    def get_existing(self):
        """Locates a CDATA node within an existing element."""
        for child in self.element.childNodes:
            if child.nodeType == child.CDATA_SECTION_NODE:
                self.node = child

        # Verify a CDATA node was found.
        try:
            s = str(self)
        except AttributeError:
            raise AttributeError('No CDATA node found')

    def __str__(self):
        """Returns the current string content."""
        return self.node.data

    def set(self, s):
        """Sets the CDATA section content."""
        self.node.data = s


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
        try:
            element = instance.get_child_element('Description')
        except KeyError:
            return None
        cdata = CDATAElement(element)
        return str(cdata)

    def __set__(self, instance, value):
        """Modifies the description text."""
        # Set a new description if given a string value, creating a new
        # element if necessary.
        if isinstance(value, str):
            try:
                element = instance.get_child_element('Description')
            except KeyError:
                cdata = self.create(instance)
            else:
                cdata = CDATAElement(element)

            cdata.set(value)

        # A value of None removes any existing description.
        elif value is None:
            try:
                element = instance.get_child_element('Description')
            except KeyError:
                pass
            else:
                instance.element.removeChild(element)
                element.unlink()

        else:
            raise TypeError('Description must be a string or None')

    def create(self, instance):
        """Creates a new Description element."""
        new = CDATAElement(parent=instance, name='Description')

        # Search for any elements listed in the follow attribute.
        follow = None
        for e in instance.child_elements:
            if e.tagName in self.follow:
                follow = e

        # Create as first child if no elements to follow were found.
        if follow is None:
            instance.element.insertBefore(new.element,
                                          instance.element.firstChild)

        # If any follow elements exist, insert the new description
        # element after the last one found. DOM node operations do not
        # provide an append-after method so an insert-remove-insert
        # procedure is used.
        else:
            instance.element.insertBefore(new.element, follow)
            instance.element.removeChild(follow)
            instance.element.insertBefore(follow, new.element)

        return new


class AttributeDescriptor(object):
    """Generic descriptor class for accessing an XML element's attribute."""
    def __init__(self, name, read_only=False):
        self.name = name
        self.read_only = read_only

    def __get__(self, instance, owner=None):
        if (instance.element.hasAttribute(self.name)):
            raw = instance.element.getAttribute(self.name)
            return self.from_xml(raw)
        return None

    def __set__(self, instance, value):
        if self.read_only is True:
            raise AttributeError('Attribute is read-only')
        new_value = self.to_xml(value)
        if new_value is not None:
            instance.element.setAttribute(self.name, new_value)

        # Delete the attribute if value is None, ignoring the case if the
        # attribute didn't exist to begin with.
        else:
            try:
                instance.element.removeAttribute(self.name)
            except xml.dom.NotFoundErr:
                pass

    def from_xml(self, value):
        """Default converter for reading attribute string.

        Can be overridden in subclasses to provide custom conversion.
        """
        return str(value)

    def to_xml(self, value):
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
        return instance.members.keys()

    def __set__(self, instance, owner=None):
        """Raises an exception upon an attempt to modify; this is read-only."""
        raise AttributeError('Read-only attribute.')


class ElementDict(ElementAccess):
    """Container which provides access to a group of XML elements.

    Operates similar to a dictionary where a child element is referenced
    by index notation to find the child with the matching key attribute.
    Instead of returning the actual XML element, a member class is
    instantiated and returned which is used to handle access to the child's
    data.
    """
    names = ElementDictNames()

    def __init__(self, parent, key_attr, types, type_attr=None, dfl_type=None,
                 key_type=str, member_args=[]):
        ElementAccess.__init__(self, parent)
        self.types = types
        self.type_attr = type_attr
        self.dfl_type = dfl_type
        self.member_args = member_args

        member_elements = self.child_elements
        keys = [key_type(e.getAttribute(key_attr)) for e in member_elements]
        self.members = dict(zip(keys, member_elements))

    def __getitem__(self, key):
        """Return a member class suitable for accessing a child element."""
        try:
            element = self.members[key]
        except KeyError:
            raise KeyError("{0} not found".format(key))

        args = [element]
        args.extend(self.member_args)

        try:
            return self.types(*args)
        except TypeError:
            if self.type_attr is not None:
                type_name = element.getAttribute(self.type_attr)
            else:
                type_name = key
            return self.types.get(type_name, self.dfl_type)(*args)
