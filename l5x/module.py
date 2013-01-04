"""
Objects for accessing a set of I/O modules.
"""

from .dom import (ElementAccess, ElementDict, AttributeDescriptor)


class Module(ElementAccess):
    """Accessor object for a communication module.

    Communication ports may be accessed via the ports attribute.
        mod.ports.names() - List of available port numbers.
        mod.ports[id] - Read/write access to a port; id is an integer.
                        See Port class.
    """
    def __init__(self, element):
        ElementAccess.__init__(self, element)
        
        ports_element = self.get_child_element('Ports')
        self.ports = ElementDict(ports_element, 'Id', Port, key_type=int)


class Port(ElementAccess):
    """Accessor object for a module's port.

    Address may be read or written with the address attribute:
        current_address = port.address
        port.address = a_new_address
    """
    address = AttributeDescriptor('Address')
