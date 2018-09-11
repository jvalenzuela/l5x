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

    # Characters from CDATA content that must be converted into escape
    # sequences when the CDATA section is replaced with a normal tag.
    cdata_escapes = [
        # Amperstand must be first because it appears in other patterns.
        # Handling it first keeps the search-replace algorithm simple.
        ('&', '&amp;'),

        ('<', '&lt;')
    ]

    def __init__(self, filename):
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
        exp = re.compile(re_delim[0] + '(?P<text>.*)' + re_delim[1])

        # Generate a list of replacement pairs(old, new) for all
        # CDATA sections.
        replacements = []
        for match in exp.finditer(doc):
            # Replace reserved characters within the text.
            text = match.group('text')
            for pair in self.cdata_escapes:
                # Set the order of symbol replacement based on the
                # conversion direction.
                if to_cdata:
                    pair = list(pair)
                    pair.reverse()

                text = text.replace(*pair)

            # Generate a new string containing the CDATA content.
            new = "{0[0]}{1}{0[1]}".format(insert_delim, text)

            replacements.append((match.group(), new))

        # Replace all CDATA with the new strings.
        for old, new in replacements:
            doc = doc.replace(old, new, 1)

        return doc

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
