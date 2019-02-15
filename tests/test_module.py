"""
Module unit tests.
"""

from l5x import module
from tests import fixture
import xml.etree.ElementTree as ElementTree
import unittest


class Modules(unittest.TestCase):
    """Tests for the project's top-level modules container."""
    def setUp(self):
        self.prj = fixture.setup()

    def test_names(self):
        """Ensure names attribute returns a non-empty set of strings."""
        self.assertGreater(len(self.prj.modules.names), 0)
        for mod in self.prj.modules.names:
            self.assertIsInstance(mod, str)
            self.assertGreater(len(mod), 0)


class Module(unittest.TestCase):
    """Tests for a single module instance."""
    def setUp(self):
        attrib = {'SafetyNetwork':'16#0000_1337_d00d_0100'}
        element = ElementTree.Element('Module', attrib)
        ports = ElementTree.SubElement(element, 'Ports')
        ElementTree.SubElement(ports, 'Port', {'Id':'1'})
        self.module = module.Module(element)

    def test_port_names(self):
        """Ensure names returns a non-empty list of integers."""
        self.assertGreater(len(self.module.ports.names), 0)
        for port in self.module.ports.names:
            self.assertIsInstance(port, int)

    def test_invalid_port(self):
        """Ensure invalid port indices raise an exception."""
        with self.assertRaises(KeyError):
            self.module.ports[0]

    def test_snn(self):
        """Confirm the snn attribute yields a safety network number."""
        self.assertEqual(self.module.snn, '1337d00d0100')


class Port(unittest.TestCase):
    """Tests for a module communication port."""
    def setUp(self):
        attrib = {'Type':'ICP',
                  'Address':'1',
                  'SafetyNetwork':'16#0000_1337_d00d_0100'}
        element = ElementTree.Element('Port', attrib)
        self.port = module.Port(element)

    def test_type(self):
        """Type attribute return a the current attribute value."""
        self.assertEqual(self.port.type, 'ICP')

    def test_type_access(self):
        """Attempting to modify port type should raise an exception."""
        with self.assertRaises(AttributeError):
            self.ports.type = 'foo'

    def test_address_read(self):
        """Confirm the current address is returned via the address attribute."""
        self.assertEqual(self.port.address, '1')

    def test_address_write(self):
        """Confirm correct attribute is updated when setting a new address."""
        self.port.address = '42'
        self.assertEqual(self.port.element.attrib['Address'], '42')

    def test_snn(self):
        """Confirm the snn attribute yields the safety network number."""
        self.assertEqual(self.port.snn, '1337d00d0100')


class SafetyNetworkNumber(unittest.TestCase):
    """Tests for safety network numbers."""
    class DummyModule(object):
        """Test fixture object."""
        snn = module.SafetyNetworkNumber()

        def __init__(self, element):
            self.element = element

    def setUp(self):
        attrs = {'SafetyNetwork':"16#0000_0000_0000_0000",
                 'Name':'dummy'}
        element = ElementTree.Element('Module', attrs)
        self.module = self.DummyModule(element)

    def test_snn_type(self):
        """Confirm SNN is a 12 character string."""
        snn = self.module.snn
        self.assertIsInstance(snn, str)
        self.assertEqual(len(snn), 12)

    def test_snn_value(self):
        """Confirm SNN number is a valid hex value."""
        x = int(self.module.snn, 16)

    def test_invalid_snn_type(self):
        """Confirm setting SNN to a non-string raises an exception."""
        with self.assertRaises(TypeError):
            self.module.snn = 0

    def test_invalid_snn_value(self):
        """Confirm setting SSN to an out-of-range value raises an exception."""
        with self.assertRaises(ValueError):
            self.module.snn = '1000000000000'

    def test_invalid_snn_str(self):
        """Confirm setting SNN to a non-hex value raises an exception."""
        with self.assertRaises(ValueError):
            self.module.snn = 'not hex'

    def test_set_snn(self):
        """Test setting SNN to a legal value."""
        self.module.snn = '0000deadbeef'
        self.assertEqual(self.module.element.attrib['SafetyNetwork'],
                         '16#0000_0000_DEAD_BEEF')

    def test_set_snn_underscore(self):
        """Test setting SNN to a value including underscores."""
        self.module.snn = '0000_1111_2222'
        self.assertEqual(self.module.element.attrib['SafetyNetwork'],
                         '16#0000_0000_1111_2222')

    def test_delete(self):
        """Confirm SNN can not be removed by setting to None."""
        with self.assertRaises(TypeError):
            self.module.snn = None

    def test_nonsafety_read(self):
        """Confirm reading from a non-safety object raises an exception."""
        del self.module.element.attrib['SafetyNetwork']
        with self.assertRaises(TypeError):
            self.module.snn

    def test_nonsafety_write(self):
        """Confirm writing a SNN to a non-safety object raises an exception."""
        del self.module.element.attrib['SafetyNetwork']
        with self.assertRaises(TypeError):
            self.module.snn = '0000deadbeef'
