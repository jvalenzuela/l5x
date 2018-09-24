"""
Top-level module defining the Project class through which all L5X access
is performed.

The general approach of this package is to provide access to L5X data
through descriptor objects organized under a Project instance in a structure
similar to RSLogix. These descriptor objects modify XML elements through
the __set__() method or return appropriately converted data from the
__get__() method. In this way the application can process L5X projects
without worrying about low-level XML handling.
"""

from .dom import (ElementAccess, ElementDict, AttributeDescriptor)
from .module import (Module, SafetyNetworkNumber)
from .tag import Scope
import io
import re
import xml.etree.ElementTree as ElementTree
import xml.dom.minidom
import xml.parsers.expat


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


class InvalidFile(Exception):
    """Raised if the given .L5X file was not a proper L5X export."""
    pass


class Project(ElementAccess):
    """Top-level container for an entire Logix project."""
    # Opening and closing delimiters for CDATA sections.
    CDATA_DELIMITER = ('<![CDATA[', ']]>')
    CDATA_TAG_DELIMITER = ('<' + CDATA_TAG + '>', '</' + CDATA_TAG + '>')

    def __init__(self, filename):
        # Dummy document used only for generating replacement CDATA sections.
        implementation = xml.dom.minidom.getDOMImplementation()
        self.cdata_converter = implementation.createDocument(None, None, None)

        try:
            doc = xml.dom.minidom.parse(filename)
        except xml.parsers.expat.ExpatError as e:
            msg = xml.parsers.expat.ErrorString(e.code)
            raise InvalidFile("XML parsing error: {0}".format(msg))

        if doc.documentElement.tagName != 'RSLogix5000Content':
            raise InvalidFile('Not an L5X file.')

        ElementAccess.__init__(self, doc.documentElement)

        ctl_element = self.get_child_element('Controller')
        self.controller = Controller(ctl_element)

        progs = self.controller.get_child_element('Programs')
        self.programs = ElementDict(progs, 'Name', Scope)

        mods = self.controller.get_child_element('Modules')
        self.modules = ElementDict(mods, 'Name', Module)

    def replace_cdata(self, doc, to_cdata):
        """Replaces the delimiters surrounding CDATA sections.

        This is used both before parsing to convert CDATA sections into
        a normal element, and before writing to revert the content back
        into a CDATA section.
        """
        # Assign the delimiter sets based on the conversion direction.
        if to_cdata:
            remove_delim = self.CDATA_TAG_DELIMITER
            insert_delim = self.CDATA_DELIMITER
        else:
            remove_delim = self.CDATA_DELIMITER
            insert_delim = self.CDATA_TAG_DELIMITER

        # Construct a regular expression to locate the CDATA content that
        # needs to be replaced.
        re_delim = [re.escape(s) for s in remove_delim]
        exp = re.compile(re_delim[0] + '(?P<text>.*?)' + re_delim[1])

        # Generate a list of replacement pairs(old, new) for all
        # CDATA sections.
        replacements = []
        for match in exp.finditer(doc):
            if to_cdata:
                new = self.cdata_element_to_section(match.group())
            else:
                new = self.cdata_section_to_element(match.group('text'))
            replacements.append((match.group(), new))

        # Replace all CDATA with the new strings.
        for old, new in replacements:
            doc = doc.replace(old, new, 1)

        return doc

    def cdata_section_to_element(self, text):
        """
        Generates a string representation of an XML element with a given
        text content. Used when replacing CDATA sections with elements.
        """
        element = ElementTree.Element(CDATA_TAG)
        element.text = text
        return ElementTree.tostring(element).decode()

    def cdata_element_to_section(self, element):
        """
        Generates a string representation of a CDATA section containing
        the content of an XML element. Used when replacing elements with
        CDATA sections.
        """
        # Parse the string to handle any escape sequences or character
        # references.
        root = ElementTree.fromstring(element)

        # Empty elements have None for text, which cannot be used when
        # creating a CDATA section.
        if root.text is not None:
            text = root.text
        else:
            text = ''

        cdata = self.cdata_converter.createCDATASection(text)
        return cdata.toxml()

    def write(self, filename):
        """Outputs the document to a new file."""
        s = self.doc.toxml()
        with io.open(filename, 'w', encoding='UTF-8') as f:
            f.write(s)


def append_child_element(name, parent):
    """Creates and appends a new child XML element."""
    doc = get_doc(parent)
    new = doc.createElement(name)
    parent.appendChild(new)
    return new


class ControllerSafetyNetworkNumber(SafetyNetworkNumber):
    """Descriptor class for accessing a controller's safety network number.

    This class handles the fact that the controller's safety network number
    is stored as an attribute of the controller's module element rather than
    the top-level controller element. Some additional work is needed to
    direct the superclass's interface to the correct element.
    """
    def __get__(self, instance, owner=None):
        mod = self.get_ctl_module(instance)
        return super(ControllerSafetyNetworkNumber, self).__get__(mod)

    def __set__(self, instance, value):
        mod = self.get_ctl_module(instance)
        super(ControllerSafetyNetworkNumber, self).__set__(mod, value)

    def get_ctl_module(self, instance):
        """Generates an object to access the controller module element.

        While the module's name varies, the controller module is always
        the first child within the Modules element.
        """
        modules = ElementAccess(instance.get_child_element('Modules'))
        return ElementAccess(modules.child_elements[0])


class Controller(Scope):
    """Accessor object for the controller device."""
    comm_path = AttributeDescriptor('CommPath')
    snn = ControllerSafetyNetworkNumber()
