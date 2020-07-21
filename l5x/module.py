"""
Objects for accessing a set of I/O modules.
"""

from .dom import (ElementDict, AttributeDescriptor)


class SafetyNetworkNumber(object):
    """Descriptor class for accessing safety network numbers."""
    ATTRIBUTE_NAME = 'SafetyNetwork'
    PREFIX = '16#0000'

    def __init__(self, element_path='.'):
        self.element_path = element_path

    def __get__(self, instance, owner=None):
        """Returns the current SNN.

        Removes the prefix, unused 16 most-significant bits, and underscores.
        """
        element = self.get_target_element(instance)
        self.check_is_safety(element)
        snn = element.attrib[self.ATTRIBUTE_NAME][len(self.PREFIX):]
        return snn.replace('_', '')

    def __set__(self, instance, value):
        """Sets a new SNN."""
        element = self.get_target_element(instance)
        self.check_is_safety(element)
        if not isinstance(value, str):
            raise TypeError('Safety network number must be a hex string')
        new = value.replace('_', '')

        # Ensure valid hex string.
        try:
            x = int(new, 16)
        except ValueError:
            raise ValueError('Safety network number must be a hex string')

        # Generate a zero-padded string and enforce 24-bit limit.
        padded = "{0:012X}".format(x)
        if not len(padded) == 12:
            raise ValueError('Value must be 24-bit, 12 hex characters')

        # Add radix prefix and insert underscores for the final output string.
        fields = [self.PREFIX]
        for word in range(3):
            start = word * 4
            end = start + 4
            fields.append(padded[start:end])

        element.attrib[self.ATTRIBUTE_NAME] = '_'.join(fields)

    def get_target_element(self, instance):
        """Finds the element containing the safety network number attribute."""
        return instance.element.find(self.element_path)

    def check_is_safety(self, element):
        """Confirms the target port/module is safety and has a SNN."""
        try:
            element.attrib[self.ATTRIBUTE_NAME]
        except KeyError:
            try:
                id = element.attrib['Name']
            except KeyError:
                id = "{0}({1})".format(element.attrib['Id'],
                                       element.attrib['Type'])
            msg = "{0} {1} does not support a safety network number.".format(
                element.tag, id)
            raise TypeError(msg)


class NatAddress(AttributeDescriptor):
    """Descriptor class for accessing port NAT addresses."""
    def to_xml(self, port, new_address):
        """
        Override for the default converter method to enforce custom validations
        specifc to NAT addresses.
        """
        # The port must already be configured for NAT, i.e. the NAT XML
        # attribute must already exist.
        if not self.name in port.element.attrib:
            raise TypeError("Port {0}({1}) is not configured for NAT.".format(
                port.element.attrib["Id"], port.element.attrib["Type"]))

        # Disallow None as removing the NAT address is not permitted.
        if not isinstance(new_address, str):
            raise TypeError("NAT address must be a string.")

        return new_address


class Module(object):
    """Accessor object for a communication module."""
    snn = SafetyNetworkNumber()

    def __init__(self, element):
        self.element = element
        ports_element = element.find('Ports')
        self.ports = ElementDict(ports_element, 'Id', Port, key_type=int)


class Port(object):
    """Accessor object for a module's port."""
    address = AttributeDescriptor('Address')
    nat_address = NatAddress('NATActualAddress')
    type = AttributeDescriptor('Type', True)
    snn = SafetyNetworkNumber()

    def __init__(self, element):
        self.element = element
