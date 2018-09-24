"""
Unit tests for the top-level project module.
"""

import l5x
import io
import unittest
from tests import fixture
import xml.etree.ElementTree as ElementTree
from xml.dom.minidom import getDOMImplementation


class Parse(unittest.TestCase):
    """Input file parsing tests."""
    def test_invalid_xml(self):
        """Ensure an exception is raised if the XML could not be parsed."""
        buf = io.BytesIO(b"foo bar")
        with self.assertRaises(l5x.InvalidFile):
            l5x.Project(buf)

    def test_invalid_root(self):
        """Ensure an exception is raised without the correct root element."""
        imp = getDOMImplementation()
        doc = imp.createDocument(None, "foo", None)
        buf = io.BytesIO(doc.toxml('UTF-8'))
        with self.assertRaises(l5x.InvalidFile):
            l5x.Project(buf)


class CDATARemoval(unittest.TestCase):
    """Tests for replacing CDATA sections with elements."""
    def setUp(self):
        """
        Creates a dummy project. This is only needed to get a Project
        instance to test the replace_cdata method.
        """
        self.project = fixture.create_project()

    def test_CDATA_to_element(self):
        """Confirm CDATA sections are converted to elements."""
        src = '<root>' + self.generate_cdata('foo') + '</root>'
        root = self.convert_parse(src)
        cdata = root.find('CDATAContent')
        self.assertEqual(cdata.text, 'foo')

    def test_multiple_CDATA(self):
        """Confirm multiple CDATA sections are all converted to elements."""
        src = '<root>' + \
              '<first>' + self.generate_cdata('foo') + '</first>' + \
              '<second>' + self.generate_cdata('bar') + '</second>' + \
              '</root>'
        root = self.convert_parse(src)

        first = root.find('first/CDATAContent')
        self.assertEqual(first.text, 'foo')

        second = root.find('second/CDATAContent')
        self.assertEqual(second.text, 'bar')

    def test_escape_characters(self):
        """Confirm special characters are converted to escape sequences."""
        text = '&<>"\''
        src = '<root>' + self.generate_cdata(text) + '</root>'
        root = self.convert_parse(src)
        cdata = root.find('CDATAContent')
        self.assertEqual(cdata.text, text)

    def test_empty_section(self):
        """Confirm an empty CDATA section is converted to an empty element."""
        src = '<root>' + self.generate_cdata('') + '</root>'
        root = self.convert_parse(src)
        cdata = root.find('CDATAContent')
        self.assertIsNone(cdata.text)

    def convert_parse(self, src):
        """
        Passes the test string through CDATA removal and parses the
        result into an XML document.
        """
        doc = self.project.replace_cdata(src, False)
        return ElementTree.fromstring(doc)

    def generate_cdata(self, text):
        """Creates a CDATA section."""
        return "<![CDATA[{0}]]>".format(text)
