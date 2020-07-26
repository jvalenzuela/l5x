"""
Module unit tests.
"""

from l5x import module
from tests import fixture
import unittest


class Modules(unittest.TestCase):
    """Tests for the project's top-level modules container."""
    def setUp(self):
        self.prj = fixture.string_to_project("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="20.01" TargetName="test" TargetType="Controller" ContainsContext="false" Owner="admin" ExportDate="Mon Jul 20 02:35:01 2020" ExportOptions="DecoratedData ForceProtectedEncoding AllProjDocTrans">
<Controller Use="Target" Name="test" ProcessorType="1756-L61" MajorRev="20" MinorRev="11" TimeSlice="20" ShareUnusedTimeSlice="1" ProjectCreationDate="Sat Jul 18 23:53:16 2020" LastModifiedDate="Sat Jul 18 23:53:18 2020" SFCExecutionControl="CurrentActive" SFCRestartPosition="MostRecent"
 SFCLastScan="DontScan" ProjectSN="16#0000_0000" MatchProjectToController="false" CanUseRPIFromProducer="false" InhibitAutomaticFirmwareUpdate="0">
<Modules>
<Module Name="Local" CatalogNumber="1756-L61" Vendor="1" ProductType="14" ProductCode="54" Major="20" Minor="11" ParentModule="Local" ParentModPortId="1" Inhibited="false" MajorFault="true"
>
<EKey State="ExactMatch"/>
<Ports>
<Port Id="1" Address="0" Type="ICP" Upstream="false">
<Bus Size="10"/>
</Port>
</Ports>
</Module>
<Module Name="mod1" CatalogNumber="1756-ENBT/A" Vendor="1" ProductType="12" ProductCode="58" Major="5" Minor="1" ParentModule="Local" ParentModPortId="1" Inhibited="false" MajorFault="false"
>
<EKey State="CompatibleModule"/>
<Ports>
<Port Id="1" Address="1" Type="ICP" Upstream="true"/>
<Port Id="2" Type="Ethernet" Upstream="false">
<Bus/>
</Port>
</Ports>
<Communications CommMethod="536870914">
<Connections/>
</Communications>
<ExtendedProperties>
<public><ConfigID>4325481</ConfigID></public></ExtendedProperties>
</Module>
<Module Name="mod2" CatalogNumber="1756-ENBT/A" Vendor="1" ProductType="12" ProductCode="58" Major="5" Minor="1" ParentModule="Local" ParentModPortId="1" Inhibited="false" MajorFault="false"
>
<EKey State="CompatibleModule"/>
<Ports>
<Port Id="1" Address="2" Type="ICP" Upstream="true"/>
<Port Id="2" Type="Ethernet" Upstream="false">
<Bus/>
</Port>
</Ports>
<Communications CommMethod="536870914">
<Connections/>
</Communications>
<ExtendedProperties>
<public><ConfigID>4325481</ConfigID></public></ExtendedProperties>
</Module>
</Modules>
<Tags/>
<Programs/>
</Controller>
</RSLogix5000Content>
""")

    def test_names_read(self):
        """Ensure names attribute returns a non-empty set of strings."""
        self.assertEqual(set(self.prj.modules.names),
                         set(('Local', 'mod1', 'mod2')))

    def test_names_readonly(self):
        """Ensure an exception is raised when attempting to write to the names attribute."""
        with self.assertRaises(AttributeError):
            self.prj.modules.names = 'foo'


class ModuleStandard(unittest.TestCase):
    """Tests for a single, non-safety module instance."""
    def setUp(self):
        element = fixture.parse_xml("""<Module Name="mod1" CatalogNumber="1756-ENBT/A" Vendor="1" ProductType="12" ProductCode="58" Major="5" Minor="1" ParentModule="Local" ParentModPortId="1" Inhibited="false" MajorFault="false"
>
<EKey State="CompatibleModule"/>
<Ports>
<Port Id="1" Address="1" Type="ICP" Upstream="true"/>
<Port Id="2" Type="Ethernet" Upstream="false">
<Bus/>
</Port>
</Ports>
<Communications CommMethod="536870914">
<Connections/>
</Communications>
<ExtendedProperties>
<public><ConfigID>4325481</ConfigID></public></ExtendedProperties>
</Module>""")
        self.module = module.Module(element)

    def test_port_names_read(self):
        """Ensure names returns a list of port IDs."""
        self.assertEqual(set(self.module.ports.names), set((1, 2)))

    def test_port_names_readonly(self):
        """Ensure an exception is raised when attempting to write to the port names attribute."""
        with self.assertRaises(AttributeError):
            self.module.ports.names = 'foo'

    def test_invalid_port_index(self):
        """Ensure invalid port indices raise an exception."""
        with self.assertRaises(KeyError):
            self.module.ports[0]

    def test_port_type(self):
        """Confirm accessing a port returns a Port instance."""
        self.assertIsInstance(self.module.ports[1], module.Port)

    def test_snn_read(self):
        """Confirm reading the SNN raises an exception."""
        with self.assertRaises(TypeError):
            self.module.snn

    def test_snn_write(self):
        """Confirm writing the SNN raises an exception."""
        with self.assertRaises(TypeError):
            self.module.snn = 'foo'


class ModuleSafetySingleSNN(unittest.TestCase):
    """Tests for safety modules with a single SNN for the entire module."""
    def setUp(self):
        self.element = fixture.parse_xml("""<Module Name="Local" CatalogNumber="1756-L61S" Vendor="1" ProductType="14" ProductCode="67" Major="20" Minor="11" ParentModule="Local" ParentModPortId="1" Inhibited="false" MajorFault="true"
 SafetyNetwork="16#0000_4544_03d1_e91a">
<EKey State="ExactMatch"/>
<Ports>
<Port Id="1" Address="0" Type="ICP" Upstream="false" Width="2">
<Bus Size="10"/>
</Port>
</Ports>
</Module>""")
        self.module = module.Module(self.element)

    def test_snn_read(self):
        """Confirm reading the SNN yields the module's SNN."""
        self.assertEqual(self.module.snn, '454403d1e91a')

    def test_snn_write(self):
        """Confirm writing the SNN correctly updates the XML attribute."""
        self.module.snn = '0'
        self.assertEqual(self.element.attrib['SafetyNetwork'],
                         '16#0000_0000_0000_0000')


class ModuleSafetyPortSNN(unittest.TestCase):
    """
    Tests for safety modules with per-port SNNs. These just confirm the
    module itself has no SNN as the SNNs must be accessed via the port
    instances, which are covered in separate unit tests.
    """
    def setUp(self):
        element = fixture.parse_xml("""<Module Name="Local" CatalogNumber="1756-L83ES" Vendor="1" ProductType="14" ProductCode="213" Major="31" Minor="11" ParentModule="Local" ParentModPortId="1" Inhibited="false" MajorFault="true"
>
<EKey State="Disabled"/>
<Ports>
<Port Id="1" Address="0" Type="ICP" Upstream="false" Width="2" SafetyNetwork="16#0000_1337_d00d_0100">
<Bus Size="4"/>
</Port>
<Port Id="2" Type="Ethernet" Upstream="false" SafetyNetwork="16#0000_1337_d00d_0101">
<Bus/>
</Port>
</Ports>
</Module>""")
        self.module = module.Module(element)

    def test_snn_read(self):
        """Confirm reading the SNN raises an exception."""
        with self.assertRaises(TypeError):
            self.module.snn

    def test_snn_write(self):
        """Confirm writing the SNN raises an exception."""
        with self.assertRaises(TypeError):
            self.module.snn = 'foo'


class Port(object):
    """Base class with common test cases for all port types."""
    def setUp(self):
        element = fixture.parse_xml(self.xml)
        self.port = module.Port(element)

    def test_type_read(self):
        """Type attribute return a the current attribute value."""
        self.assertEqual(self.port.type, self.port.element.attrib['Type'])

    def test_type_write(self):
        """Attempting to modify port type should raise an exception."""
        with self.assertRaises(AttributeError):
            self.ports.type = 'foo'

    def test_address_read(self):
        """Confirm the current address is returned via the address attribute."""
        self.assertEqual(self.port.address, self.port.element.attrib['Address'])

    def test_address_write(self):
        """Confirm correct attribute is updated when setting a new address."""
        self.port.address = '42'
        self.assertEqual(self.port.element.attrib['Address'], '42')


class PortStandard(Port, unittest.TestCase):
    """Tests for a non-safety module communication port."""
    xml = r"""<Port Id="2" Address="192.168.0.1" Type="Ethernet" Upstream="false">
<Bus/>
</Port>"""

    def test_snn_read(self):
        """Confirm reading the SNN raises an exception."""
        with self.assertRaises(TypeError):
            self.port.snn

    def test_snn_write(self):
        """Confirm writing the SNN raises an exception."""
        with self.assertRaises(TypeError):
            self.port.snn = 'foo'


class PortNoNAT(Port, unittest.TestCase):
    """Tests for ports that do not use network address translation."""
    xml = r"""<Port Id="2" Address="192.168.0.1" Type="Ethernet" Upstream="false">
<Bus/>
</Port>"""

    def test_nat_address_read(self):
        """Confirm reading the NAT address returns None."""
        self.assertIsNone(self.port.nat_address)

    def test_nat_address_write(self):
        """Confirm an exception is raised when writing the NAT address."""
        with self.assertRaises(TypeError):
            self.port.nat_address = 'foo'


class PortNAT(Port, unittest.TestCase):
    """Test for ports configured with network address translation."""
    xml = r"""<Port Id="2" Address="192.168.0.1" Type="Ethernet" Upstream="true" NATActualAddress="10.0.0.1"/>"""

    def test_nat_address_read(self):
        """Confirm reading the NAT address returns the attribute value."""
        self.assertEqual(self.port.nat_address,
                         self.port.element.attrib['NATActualAddress'])

    def test_nat_address_write(self):
        """Confirm writing the NAT address updates the XML attribute."""
        self.port.nat_address = 'foo'
        self.assertEqual(self.port.element.attrib['NATActualAddress'], 'foo')

    def test_nat_address_write_non_string(self):
        """Confirm writing a non-string raises an exception."""
        with self.assertRaises(TypeError):
            self.port.nat_address = None


class PortSafety(Port, unittest.TestCase):
    """Tests for a safety module communication port."""
    xml = r"""<Port Id="1" Address="0" Type="ICP" Upstream="false" Width="2" SafetyNetwork="16#0000_1337_d00d_0100">
<Bus Size="4"/>
</Port>"""

    def test_snn_read(self):
        """Confirm reading the SNN."""
        self.assertEqual(self.port.snn, '1337d00d0100')

    def test_snn_write(self):
        """Confirm writing the SNN correctly updates the XML attribute."""
        self.port.snn = '0'
        self.assertEqual(self.port.element.attrib['SafetyNetwork'],
                         '16#0000_0000_0000_0000')


class SafetyNetworkNumber(unittest.TestCase):
    """Tests for safety network numbers."""
    def setUp(self):
        element = fixture.parse_xml(r"""<Module Name="Local" CatalogNumber="1756-L61S" Vendor="1" ProductType="14" ProductCode="67" Major="20" Minor="11" ParentModule="Local" ParentModPortId="1" Inhibited="false" MajorFault="true"
 SafetyNetwork="16#0000_4544_03d1_e91a">
<EKey State="ExactMatch"/>
<Ports>
<Port Id="1" Address="0" Type="ICP" Upstream="false" Width="2">
<Bus Size="10"/>
</Port>
</Ports>
</Module>""")
        self.module = module.Module(element)

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

    def test_set_snn_underscore(self):
        """Test setting SNN to a value including underscores."""
        self.module.snn = '0000_1111_2222'
        self.assertEqual(self.module.element.attrib['SafetyNetwork'],
                         '16#0000_0000_1111_2222')
