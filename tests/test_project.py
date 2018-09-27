"""
Unit tests for the top-level project module.
"""

import l5x
import io
import unittest
from tests import fixture
import xml.etree.ElementTree as ElementTree
import xml.dom.minidom


class Parse(unittest.TestCase):
    """Input file parsing tests."""
    def test_invalid_xml(self):
        """Ensure an exception is raised if the XML could not be parsed."""
        buf = io.BytesIO(b"foo bar")
        with self.assertRaises(l5x.InvalidFile):
            l5x.Project(buf)

    def test_invalid_root(self):
        """Ensure an exception is raised without the correct root element."""
        imp = xml.dom.minidom.getDOMImplementation()
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
        doc = self.project.convert_to_cdata_element(src)
        return ElementTree.fromstring(doc)

    def generate_cdata(self, text):
        """Creates a CDATA section."""
        return "<![CDATA[{0}]]>".format(text)


class CDATAInsertion(unittest.TestCase):
    """Tests for replacing CDATA elements with CDATA sections."""
    def setUp(self):
        """
        Creates a dummy project. This is only needed to get a Project
        instance to test the CDATA conversion method.
        """
        self.project = fixture.create_project()

    def test_element_to_CDATA(self):
        """Confirm CDATA elements are converted to CDATA sections."""
        src = '<root>' + self.generate_cdata('foo') + '</root>'
        root = self.convert_parse(src)
        self.assert_cdata_content(root, 'foo')

    def test_multiple_elements(self):
        """Confirm multiple CDATA elements are converted to CDATA sections."""
        src = '<root>' + \
              '<first>' + self.generate_cdata('foo') + '</first>' + \
              '<second>' + self.generate_cdata('bar') + '</second>' + \
              '</root>'
        root = self.convert_parse(src)

        for tag, text in [('first', 'foo'), ('second', 'bar')]:
            element = root.getElementsByTagName(tag)[0]
            self.assert_cdata_content(element, text)

    def test_escape_sequences(self):
        """Confirm escape sequences are converted to unescaped characters."""
        src = '<root>' + \
              self.generate_cdata('&amp;&lt;&gt;&quot;&apos;') + \
              '</root>'
        root = self.convert_parse(src)
        self.assert_cdata_content(root, '&<>"\'')

    def test_empty_element(self):
        """Confirm an empty element is converted to an empty CDATA section."""
        src = '<root>' + self.generate_cdata('') + '</root>'
        self.assert_empty_cdata(src)

    def test_self_closing_empty(self):
        """Confirm a self-closing element yields to an empty CDATA section."""
        src = '<root><CDATAContent/></root>'
        self.assert_empty_cdata(src)

    def test_tag_whitespace(self):
        """Confirm whitespace in opening and closing tags is accepted."""
        src = '<root><CDATAContent   ></CDATAContent   ></root>'
        self.assert_empty_cdata(src)

    def test_self_closing_tag_whitespace(self):
        """Confirm whitespace in a self-closing tag is accepted."""
        src = '<root><CDATAContent   /></root>'
        self.assert_empty_cdata(src)

    def convert_parse(self, src):
        """
        Converts string containing the source document, parses the
        result, and returns the root element.
        """
        cdata = self.project.convert_to_cdata_section(src)
        doc = xml.dom.minidom.parseString(cdata)
        return doc.documentElement

    def generate_cdata(src, text):
        """Creates a CDATAContent element containing text."""
        return "<CDATAContent>{0}</CDATAContent>".format(text)
        
    def assert_cdata_content(self, element, text):
        """
        Confirms an element contains a single CDATA section with a
        given text content.
        """
        cdata_nodes = [n for n in element.childNodes
                       if n.nodeType == n.CDATA_SECTION_NODE]
        self.assertEqual(len(cdata_nodes), 1)
        self.assertEqual(cdata_nodes[0].data, text)

    def assert_empty_cdata(self, src):
        """Validates CDATA conversion results in an empty CDATA section.

        This uses basic string equality instead of parsing the converted
        XML because empty CDATA sections are not preserved when parsed.
        """
        doc = self.project.convert_to_cdata_section(src)
        self.assertEqual(doc, '<root><![CDATA[]]></root>')
