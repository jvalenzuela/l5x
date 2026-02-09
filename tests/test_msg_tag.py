"""Message tag unit tests."""

from . import fixture
from .test_tags import LanguageBase
import l5x

import unittest


class Parameters(unittest.TestCase):
    """Tests for the parameters attribute."""

    XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <RSLogix5000Content>
    <Controller>
    <Tags>
    <Tag Name="tag" TagType="Base" DataType="MESSAGE">
    <Data Format="Message">
    <MessageParameters foo="bar" spam="eggs"/>
    </Data>
    </Tag>
    </Tags>
    </Controller>
    </RSLogix5000Content>
    """

    def setUp(self):
        prj = fixture.string_to_project(self.XML)
        self.tag = prj.controller.tags["tag"]

    def test_read(self):
        """Confirm reading yields the set of element attributes."""
        self.assertEqual({"foo": "bar", "spam": "eggs"}, self.tag.parameters)

    def test_change_value(self):
        """Confirm changing dict values updates the element attributes."""
        self.tag.parameters["spam"] = "new eggs"
        param_element = self.tag.element.find("Data/MessageParameters")
        self.assertEqual(
            {"foo": "bar", "spam": "new eggs"},
            param_element.attrib,
        )

    def test_assign(self):
        """Confirm exception when assigning a value to the attribute."""
        with self.assertRaises(RuntimeError):
            self.tag.parameters = "foo"


class Description(LanguageBase):
    """Tests for the description attribute."""

    XML = """
    <Tag Name="tag" TagType="Base" DataType="MESSAGE">
    <Description>
    <![CDATA[foo]]>
    </Description>
    <Data Format="Message">
    <MessageParameters foo="bar" spam="eggs"/>
    </Data>
    </Tag>
    """

    def setUp(self):
        self.create_tag(self.XML)

    def test_read(self):
        """Confirm reading an existing description."""
        self.assertEqual("foo", self.tag.description)

    def test_write(self):
        """Confirm updating an existing description."""
        self.tag.description = "bar"
        desc = self.tag.element.findall("Description")
        self.assertEqual(len(desc), 1)
        self.assert_cdata_content(desc[0], "bar")
