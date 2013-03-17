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
from .module import Module
from .tag import Scope
import xml.dom.minidom


class InvalidFile(Exception):
    """Raised if the given .L5X file was not a proper L5X export."""
    pass


class Project(ElementAccess):
    """Top-level container for an entire Logix project."""
    def __init__(self, filename):
        doc = xml.dom.minidom.parse(filename)
        if doc.documentElement.tagName != 'RSLogix5000Content':
            raise InvalidFile('Not an L5X file.')

        ElementAccess.__init__(self, doc.documentElement)

        ctl_element = self.get_child_element('Controller')
        self.controller = Controller(ctl_element)

        progs = self.controller.get_child_element('Programs')
        self.programs = ElementDict(progs, 'Name', Scope)

        mods = self.controller.get_child_element('Modules')
        self.modules = ElementDict(mods, 'Name', Module)

    def write(self, filename):
        """Outputs the document to a new file."""
        f = open(filename, 'w')
        self.doc.writexml(f, encoding='UTF-8')
        f.close()


def append_child_element(name, parent):
    """Creates and appends a new child XML element."""
    doc = get_doc(parent)
    new = doc.createElement(name)
    parent.appendChild(new)
    return new


class Controller(Scope):
    """Accessor object for the controller device."""
    comm_path = AttributeDescriptor('CommPath')
