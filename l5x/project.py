"""

"""

from .dom import (ElementAccess, ElementDict, AttributeDescriptor)
from .module import Module
from .tag import Scope
import xml.dom.minidom


class InvalidFile(Exception):
    """ """
    pass


class Project(ElementAccess):
    """Top-level container for en entire Logix project.

    """
    def __init__(self, filename):
        """ """
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
    """Accessor object for the controller device.

    Controller-scoped tags are available via the tags attribute.
        controller.tags.names() - List of tag names.
        controller.tags[tag_name] - Accessor object to read or modify tag
                                    properties. See Tag class.

    Communication path may be accessed through the comm_path attribute.
        current_path = controller.comm_path
        controller.comm_path = a_new_path
    """
    comm_path = AttributeDescriptor('CommPath')


if __name__ == '__main__':
    prj = Project('l5x1.L5X')
    print(prj.controller.tags.names)
    print(len(prj.controller.tags['ar2']))
    print(len(prj.controller.tags['ar2'][0]))
    print(len(prj.controller.tags['ar2'][0][0]))
    print(len(prj.controller.tags['ar2'][0][0][0]))
    #prj.write('out.L5X')
