"""
Project object unit tests.
"""

from lxml import etree
from string import Template
import io
import unittest
import l5x


class ContentCheck(unittest.TestCase):
    """Tests for initial content verifications."""
    def test_root_element(self):
        """
        Confirms an exception is raised when given an XML document
        without the correct root element.
        """
        root = etree.Element("notRSLogixContent")
        s = etree.tostring(root)
        buf = io.BytesIO(s)
        with self.assertRaises(l5x.project.InvalidFile):
            l5x.Project(buf)


class CDATA_Fixture(l5x.Project):
    """Dummy object for CDATA newline tests."""
    def __init__(self):
        pass


class CDATA_newlines(unittest.TestCase):
    """Tests for CDATA newline correction."""
    def setUp(self):
        self.prj = CDATA_Fixture()

    def test_no_newlines(self):
        """Ensure CDATA without any newlines remains unmodified."""
        s = self.make_cdata('spam')
        self.check_result(s, s)

    def test_noncdata(self):
        """Ensure content outside CDATA sections is not modified."""
        s = 'not\nCDATA'
        self.check_result(s, s)

    def test_newline_expansion(self):
        """Confirm newlines are expanded with a leading carriage return."""
        lf = self.make_cdata('foo\nbar')
        crlf = self.make_cdata('foo\r\nbar')
        self.check_result(lf, crlf)

    def test_multiple_newlines(self):
        """Confirm consecutive newlines are properly expanded."""
        lr = self.make_cdata('\n' * 3)
        crlf = self.make_cdata('\r\n' * 3)
        self.check_result(lr, crlf)

    def make_cdata(self, content):
        """Constructs a CDATA element with some given content."""
        return "<![CDATA[{0}]]>".format(content)

    def check_result(self, test, expected):
        """Wrapper to process a test string and verify the result."""
        result = self.prj._fixup_cdata_newlines(test)
        self.assertEqual(result, expected)
