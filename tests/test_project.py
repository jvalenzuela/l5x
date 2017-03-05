"""
Unit tests for the top-level project module.
"""

import l5x
import io
import unittest
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
