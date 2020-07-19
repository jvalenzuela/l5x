"""
Unit tests for a project's programs object.
"""

from tests import fixture
import unittest


class Programs(unittest.TestCase):
    """Tests for the top-level programs container object."""
    def setUp(self):
        prj = fixture.string_to_project(r"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="20.01" TargetName="test" TargetType="Controller" ContainsContext="false" Owner="admin" ExportDate="Mon Jul 20 01:45:55 2020" ExportOptions="DecoratedData ForceProtectedEncoding AllProjDocTrans">
<Controller Use="Target" Name="test" ProcessorType="1756-L61" MajorRev="20" MinorRev="11" TimeSlice="20" ShareUnusedTimeSlice="1" ProjectCreationDate="Sat Jul 18 23:53:16 2020" LastModifiedDate="Sat Jul 18 23:53:18 2020" SFCExecutionControl="CurrentActive" SFCRestartPosition="MostRecent"
 SFCLastScan="DontScan" ProjectSN="16#0000_0000" MatchProjectToController="false" CanUseRPIFromProducer="false" InhibitAutomaticFirmwareUpdate="0">
<Programs>
<Program Name="MainProgram" TestEdits="false" Disabled="false">
<Tags>
<Tag Name="main_tag_1" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>
<Tag Name="main_tag_2" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>
</Tags>
<Routines/>
</Program>
<Program Name="prog2" TestEdits="false" Disabled="false">
<Tags>
<Tag Name="prog2_tag_1" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>
<Tag Name="prog2_tag_2" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Data>00 00 00 00</Data>
<Data Format="Decorated">
<DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</Data>
</Tag>
</Tags>
<Routines/>
</Program>
</Programs>
</Controller>
</RSLogix5000Content>""")
        self.programs = prj.programs

    def test_names_read(self):
        """Test name attribute returns all program names."""
        self.assertEqual(set(self.programs.names),
                         set(('MainProgram', 'prog2')))

    def test_names_read_only(self):
        """Ensure names attribute is read-only."""
        with self.assertRaises(AttributeError):
            self.programs.names = 'foo'

    def test_index(self):
        """Test indexing by names."""
        for prg in self.programs.names:
            self.programs[prg]

    def test_tags_names(self):
        """Ensure tags names attribute is a iterable of non-empty strings."""
        self.assertEqual(set(self.programs['MainProgram'].tags.names),
                         set(('main_tag_1', 'main_tag_2')))
        self.assertEqual(set(self.programs['prog2'].tags.names),
                         set(('prog2_tag_1', 'prog2_tag_2')))
