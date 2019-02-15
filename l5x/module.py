"""
Objects for accessing a set of I/O modules.
"""

from .dom import (ElementAccess, ElementDict, AttributeDescriptor)


class SafetyNetworkNumber(object):
    """Descriptor class for accessing safety network numbers."""
    ATTRIBUTE_NAME = 'SafetyNetwork'
    PREFIX = '16#0000'
    def __get__(self, instance, owner=None):
        """Returns the current SNN.

        Removes the prefix, unused 16 most-significant bits, and underscores.
        """
        self.check_is_safety(instance.element)
        snn = instance.element.attrib[self.ATTRIBUTE_NAME][len(self.PREFIX):]
        return snn.replace('_', '')

    def __set__(self, instance, value):
        """Sets a new SNN."""
        self.check_is_safety(instance.element)
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

        instance.element.attrib[self.ATTRIBUTE_NAME] = '_'.join(fields)

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


class Module(object):
    """Accessor object for a communication module."""
    snn = SafetyNetworkNumber()

    def __init__(self, element):
        self.element = element
        ports_element = element.find('Ports')
        self.ports = ElementDict(ports_element, 'Id', Port, key_type=int)


class Port(ElementAccess):
    """Accessor object for a module's port."""
    address = AttributeDescriptor('Address')
    type = AttributeDescriptor('Type', True)
