"""
Module unit tests.
"""

from tests import fixture
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
    test_module = 'EN2T'

    def setUp(self):
        prj = fixture.setup()
        self.module = prj.modules[self.test_module]

    def test_port_names(self):
        """Ensure names returns a non-empty list of integers."""
        self.assertGreater(len(self.module.ports.names), 0)
        for port in self.module.ports.names:
            self.assertIsInstance(port, int)

    def test_invalid_port(self):
        """Ensure invalid port indices raise an exception."""
        with self.assertRaises(KeyError):
            self.module.ports[0]

    def test_port_type(self):
        """Port type should return a non-empty string."""
        for port in self.module.ports.names:
            type = self.module.ports[port].type
            self.assertIsInstance(type, str)
            self.assertGreater(len(type), 0)

    def test_port_type_access(self):
        """Attempting to modify port type should raise an exception."""
        for port in self.module.ports.names:
            with self.assertRaises(AttributeError):
                self.module.ports[port].type = 'foo'

    def test_address_type(self):
        """Address attribute should return a non-empty string."""
        address = self.module.ports[2].address
        self.assertIsInstance(address, str)
        self.assertGreater(len(address), 0)

    @classmethod
    def tearDownClass(cls):
        """Changes the module's IP address in the output project."""
        prj = fixture.setup()
        module = prj.modules[cls.test_module]
        module.ports[2].address = '1.2.3.4'
        fixture.teardown(prj)
