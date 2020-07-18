"""
Utilities used by all test modules to ensure test output is accumulated into
a single output file for final validation by RSLogix.
"""

import io
import l5x
import xml.dom.minidom
import xml.etree.ElementTree as ElementTree


INPUT_FILE = 'tests/test.L5X'
OUTPUT_FILE = 'tests/output.L5X'


def parse_xml(xml_str):
    """Parses XML from a string."""
    class Parser(l5x.Project):
        """Use the Project class to handle CDATA conversion."""
        def __init__(self, s):
            # Swap out CDATA sections before parsing.
            cdata_replaced = self.convert_to_cdata_element(s)

            # The (unicode) string needs to be converted back to a series
            # of bytes before ElementTree parses it.
            encoded = cdata_replaced.encode('UTF-8')

            self.doc = ElementTree.fromstring(encoded)

    parser = Parser(xml_str)
    return parser.doc


def setup():
    """Called by setUpModule to acquire the project for testing."""
    try:
        prj = l5x.Project(OUTPUT_FILE)
    except IOError:
        prj = l5x.Project(INPUT_FILE)
    return prj


def teardown(prj):
    """Called by tearDownModule to write the tests final output data."""
    prj.write(OUTPUT_FILE)


def create_project(*populate):
    """
    Generates a mock L5X project. The created document contains only an
    empty set of elements required by the L5X Project class; the populate
    callbacks are used to add whatever additional content needed by particular
    test cases.
    """
    imp = xml.dom.minidom.getDOMImplementation()
    doc = imp.createDocument(None, 'RSLogix5000Content', None)
    root = doc.documentElement

    controller = doc.createElement('Controller')
    root.appendChild(controller)

    # Create the top-level elements under the Controller.
    for tag in ['Tags', 'Programs', 'Modules']:
        element = doc.createElement(tag)
        controller.appendChild(element)

    # Dispatch the document to the populate callbacks to allow additional
    # content to be added before serialization.
    [f(doc) for f in populate]

    # Serialize the document so it can be parsed as a simulated XML file.
    xml_str = root.toxml('UTF-8').decode('UTF-8')
    buf = io.StringIO(xml_str)
    return l5x.Project(buf)
