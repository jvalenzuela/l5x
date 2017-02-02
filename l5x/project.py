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
from lxml import etree
import io
import re


class InvalidFile(Exception):
    """Raised if the given .L5X file was not a proper L5X export."""
    pass


class Project(ElementAccess):
    """Top-level container for an entire Logix project."""
    def __init__(self, filename):
        self._load(filename)

        ctl_element = self.get_child_element('Controller')
        self.controller = Controller(ctl_element)

        progs = self.controller.get_child_element('Programs')
        self.programs = ElementDict(progs, 'Name', Scope)

        mods = self.controller.get_child_element('Modules')
        self.modules = ElementDict(mods, 'Name', Module)

    def _load(self, filename):
        """Parses the source project file."""
        parser = etree.XMLParser(strip_cdata=False)

        try:
            self.etree = etree.parse(filename, parser)
        except etree.XMLSyntaxError as e:
            raise InvalidFile("XML parsing error: {0}".format(str(e)))

        self.root = self.etree.getroot()

        # Simple verification that the XML document is indeed an
        # RSLogix export.
        if self.root.tag != 'RSLogix5000Content':
            raise InvalidFile('Not an L5X file.')

    def write(self, filename):
        """Outputs the document to a new file."""
        buf = etree.tostring(self.etree, encoding='UTF-8', standalone=True)
        s = str(buf, encoding='UTF-8')
        s = self._fixup_cdata_newlines(s)
        with open(filename, 'wb') as f:
            f.write(s.encode())

    def _fixup_cdata_newlines(self, s):
        """Corrects newline sequences within CDATA elements.

        The lxml parsing process reduces \r\n combinations to a single \n,
        which is not interpreted correctly by RSLogix. This method restores
        the original carriage return and newline.
        """
        re_cdata = re.compile(r"<!\[CDATA\[.*?\]\]>", re.DOTALL)

        # Construct a list of CDATA content containing newlines.
        cdata = [m.group() for m in re_cdata.finditer(s) if '\n' in m.group()]

        # Replace the CDATA sections with expanded newline endings.
        for txt in cdata:
            new = txt.replace('\n', '\r\n')
            s = s.replace(txt, new, 1)

        return s


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
