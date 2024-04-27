"""
Top-level module defining the Project class through which all L5X access
is performed.

The general approach of this package is to provide access to L5X data
through descriptor objects organized under a Project instance in a structure
similar to RSLogix. These descriptor objects modify XML elements through
the __set__() method or return appropriately converted data from the
__get__() method. In this way the application can process L5X projects
without worrying about low-level XML handling.
"""

from .atomic import (SINT, INT, DINT, LINT, BOOL, REAL)
from .dom import (CDATA_TAG, ElementDict, AttributeDescriptor)
from .module import (Module, SafetyNetworkNumber)
from .tag import Scope
from l5x import array
import contextlib
import io
import re
import xml.etree.ElementTree as ElementTree
import xml.dom.minidom


class InvalidFile(Exception):
    """Raised if the given .L5X file was not a proper L5X export."""
    pass


class Project(object):
    """Top-level container for an entire Logix project."""
    def __init__(self, filename):
        # Dummy document used only for generating replacement CDATA sections.
        implementation = xml.dom.minidom.getDOMImplementation()
        self.cdata_converter = implementation.createDocument(None, None, None)

        self.parse(filename)

        # Confirm the root element indicates this is a Logix project.
        if self.doc.tag != 'RSLogix5000Content':
            raise InvalidFile('Not an L5X file.')

        try:
            lang = self.doc.attrib['CurrentLanguage']
        except KeyError:
            lang = None

        self._load_data_types()

        # Mapping of TagData objects keyed by XML tag element. This also
        # serves to record all tag data buffers that have been created so
        # they can be flushed when the project is written.
        self._tag_data = {}

        ctl_element = self.doc.find('Controller')
        self.controller = Controller(ctl_element, self, lang)

        progs = ctl_element.find('Programs')
        self.programs = ElementDict(progs, 'Name', Scope,
                                    value_args=[self, lang])

        mods = ctl_element.find('Modules')
        self.modules = ElementDict(mods, 'Name', Module)

    def parse(self, filename):
        """Parses the source project."""
        # Accept both filename strings for normal usage, and buffer objects
        # for unit tests.
        try:
            f = io.open(filename, encoding='UTF-8')
        except TypeError:
            f = filename

        with f:
            orig = f.read()

        # Swap out CDATA sections before parsing.
        cdata_replaced = self.convert_to_cdata_element(orig)

        # The (unicode) string needs to be converted back to a series
        # of bytes before ElementTree parses it.
        encoded = cdata_replaced.encode('UTF-8')

        try:
            self.doc = ElementTree.fromstring(encoded)
        except ElementTree.ParseError as e:
            raise InvalidFile("XML parsing error: {0}".format(e))

    def convert_to_cdata_element(self, doc):
        """Replaces the delimiters surrounding CDATA sections.

        This is used before parsing to convert CDATA sections into
        normal elements.
        """
        pattern = r"""
            <!\[CDATA\[   # Opening CDATA sequence.
            (?P<text>.*?) # Element content.
            \]\]>         # Closing CDATA sequence.
        """
        return re.sub(pattern, self.cdata_element, doc,
                      flags=re.VERBOSE | re.DOTALL)

    def cdata_element(self, match):
        """
        Generates a string representation of an XML element with a given
        text content. Used when replacing CDATA sections with elements.
        """
        element = ElementTree.Element(CDATA_TAG)
        element.text = match.group('text')
        return ElementTree.tostring(element).decode()

    def convert_to_cdata_section(self, doc):
        """Replaces CDATA elements with CDATA sections.

        This is used before writing a project to reinstall the CDATA sections
        required by RSLogix.
        """
        # Regular expression pattern to locate CDATA elements.
        pattern = r"""
            # Match elements with separate opening and closing tags.
            <{0}\s*>  # Opening tag.
            .*?       # Element content.
            </{0}\s*> # Closing tag

            |

            # Also match empty, self-closing tags.
            <{0}\s*/>
        """.format(CDATA_TAG)
        return re.sub(pattern, self.cdata_section, doc,
                      flags=re.VERBOSE | re.DOTALL)

    def cdata_section(self, match):
        """
        Generates a string representation of a CDATA section containing
        the content of an XML element. Used when replacing elements with
        CDATA sections.
        """
        # Parse the string to handle any escape sequences or character
        # references, after encoding to ensure ElementTree parses a
        # series of bytes.
        encoded = match.group().encode('UTF-8')
        root = ElementTree.fromstring(encoded)

        # Empty elements have None for text, which cannot be used when
        # creating a CDATA section.
        if root.text is not None:
            text = root.text
        else:
            text = ''

        cdata = self.cdata_converter.createCDATASection(text)
        return cdata.toxml()

    def write(self, filename):
        """Outputs the document to a new file."""
        with self._flush_data():
            no_cdata = self.doc_to_string()
        with_cdata = self.convert_to_cdata_section(no_cdata)

        encoded = with_cdata.encode('UTF-8')
        try:
            f = open(filename, 'wb')

        # Accept buffer targets for unit testing.
        except TypeError:
            filename.write(encoded)
            filename.seek(0)

        else:
            with f:
                f.write(encoded)

    @contextlib.contextmanager
    def _flush_data(self):
        """Serializes bytearrays stored in the XML document.

        Element text attributes holding a bytearray need to be converted back
        to a string before the XML document is serialized. This function
        performs that conversion as a context manager, serializing the
        bytearrays during setup, and restoring the bytearrays at teardown.
        The latter is required because further modifications to the bytearrays
        may occur after the document is serialized.
        """
        # Find elements that have bytearray text attributes.
        elements = [e for e in self.doc.iter() if isinstance(e.text, bytearray)]
        barrays = [e.text for e in elements]

        # Replace bytearrays with hex strings; upper-case isn't mandated by
        # the L5X format documentation, however, RSLogix exports upper-case,
        # so this will do the same.
        for e in elements:
            e.text = e.text.hex(' ').upper()

        yield

        # Restore bytearray references.
        for i in range(len(elements)):
            elements[i].text = barrays[i]

    def doc_to_string(self):
        """Serializes the document into a unicode string.

        This is used instead of ElementTree's tostring() method because
        an XML declaration is required, which can only be generated
        with write().
        """
        tree = ElementTree.ElementTree(self.doc)
        buf = io.BytesIO()
        tree.write(buf, encoding='UTF-8', xml_declaration=True)
        return buf.getvalue().decode('UTF-8')

    def _load_data_types(self):
        """Builds the set of all defined data types."""
        # Start with atomic data types.
        self._data_types = {
            'SINT':SINT,
            'INT':INT,
            'DINT':DINT,
            'LINT':LINT,
            'BOOL':BOOL,
            'REAL':REAL
            }

    def get_data_type(self, element):
        """Returns a mixin class to handle the data of a given XML element.

        The provided element may be a top-level tag or structure member.
        """
        name = element.attrib['DataType']

        try:
            data_type = self._data_types[name]
        except KeyError:
            raise NotImplementedError(
                "Data type not implemented: {0}".format(name))

        # Return an array class tailored for a given data type if the element
        # defines an array.
        if array.is_array(element):
            return array.define_new(element, data_type)

        return data_type


class Controller(Scope):
    """Accessor object for the controller device."""
    comm_path = AttributeDescriptor('CommPath')

    # The safety network number is stored in the first module element,
    # not the Controller element.
    snn = SafetyNetworkNumber('Modules/Module')
