"""
Objects for accessing a set of I/O modules.
"""

from .dom import (ElementAccess, ElementDict, AttributeDescriptor)


class Module(ElementAccess):
    """Accessor object for a communication module."""
    def __init__(self, element):
        ElementAccess.__init__(self, element)
        
        ports_element = self.get_child_element('Ports')
        self.ports = ElementDict(ports_element, 'Id', Port, key_type=int)


class Port(ElementAccess):
    """Accessor object for a module's port."""
    address = AttributeDescriptor('Address')
    type = AttributeDescriptor('Type', True)
