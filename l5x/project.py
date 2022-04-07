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

from .dom import (CDATA_TAG, ElementDict, AttributeDescriptor)
from .module import (Module, SafetyNetworkNumber)
from .tag import Scope
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

        ctl_element = self.doc.find('Controller')
        self.controller = Controller(ctl_element, lang)

        progs = ctl_element.find('Programs')
        self.programs = ElementDict(progs, 'Name', Scope, value_args=[lang])

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


class Controller(Scope):
    """Accessor object for the controller device."""
    comm_path = AttributeDescriptor('CommPath')

    # The safety network number is stored in the first module element,
    # not the Controller element.
    snn = SafetyNetworkNumber('Modules/Module')


class TagData(object):
    """
    This object manages access to a single tag's data, which always uses the
    raw, or unformatted, Data element. The raw data is chosen because it is
    the only type that is always exported; RSLogix does not export formatted
    data for some tags.

    When data is requested, this object will generate a bytearray from the
    XML content; all operations for reading and writing tag values are then
    based solely on this bytearray. This object does not interpret the
    data into any type; it only deals with raw XML data and resulting
    bytearray.

    This object will also write the bytearray back to the XML document
    before the project is written out to an L5X file to capture any
    modifications made to the tag's value.
    """

    def __init__(self, tag_element):
        self.tag_element = tag_element

    def get_data(self):
        """Generates a bytearray from the tag's raw data element.

        This will return the same bytearray object every time it is called
        to ensure only one bytearray exists for a given tag. This is
        important because it is possible for multiple objects to access
        the tag's data via the bytearray returned by this method.
        Maintaining a single bytearray ensures values remain consistent,
        regardless of how many objects access the data.
        """
        # See if the data has already been parsed.
        try:
            self.data

        # Read the data if it has not been previously parsed.
        except AttributeError:
            self.data = self._parse_data()

        return self.data

    def _parse_data(self):
        """Creates a bytearray from the tag's raw data element."""
        e = self._get_data_element()
        return bytearray.fromhex(e.text)

    def _get_data_element(self):
        """Locates the element containing the tag's data in raw format."""
        e = self.tag_element.find('Data')

        # The raw data must be the first Data element.
        if (e is None) or ('Format' in e.attrib):
            raise InvalidFile('Raw data element not found.')

        return e

    def flush(self):
        """Writes the bytearray back to the XML document.

        The XML content is only updated if the bytearray was modified.
        """
        # See if a bytearray has been created from the raw data element.
        try:
            self.data

        # Data does not need to be updated if it was never parsed into a
        # bytearray, which means it was never accessed by the L5X module.
        except AttributeError:
            pass

        else:
            if self._data_has_changed():
                self._write_data()

                # Remove formatted data so it does not conflict with the
                # new data.
                self._remove_formatted_data()

    def _data_has_changed(self):
        """Determines if the tag data has been modified.

        This is done by comparing the XML document's content with the
        bytearray created when the raw data was parsed. The L5X module
        only operates on the bytearray, while the XML content is not altered
        until the project is written, so a difference between the two means
        the bytearray has changed and the XML content is stale.
        """
        orig = self._parse_data()
        return orig != self.data

    def _write_data(self):
        """Writes the bytearray back to the XML document."""
        dst = self._get_data_element()

        # It is not clear if RSLogix is case-sensitive for hexadecimal data,
        # however, it exports upper-case, so this will do the same.
        dst.text = self.data.hex(' ').upper()

    def _remove_formatted_data(self):
        """Deletes elements containing formatted data."""
        formatted = self.tag_element.findall('Data[@Format]')
        [self.tag_element.remove(e) for e in formatted]
