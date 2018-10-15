"""
Unit tests for low-level XML interface objects.
"""

from l5x import dom
import unittest
import xml.etree.ElementTree as ElementTree


class ElementDict(unittest.TestCase):
    """Unit tests for the ElementDict class."""
    def test_key_attribute_value(self):
        """Confirm values from the key attribute are used for lookup."""
        pass

    def test_depth_lookup(self):
        """Confirm only direct children are queried for lookup."""
        pass

    def test_key_not_found(self):
        """Confirm a KeyError is raised if a matching key doesn't exist."""
        pass

    def test_key_not_found_empty(self):
        """Confirm a KeyError is raised if the parent has no child elements."""
        pass

    def test_string_lookup(self):
        """Confirm correct lookup with string keys."""
        pass

    def test_integer_lookup(self):
        """Confirm correct lookup with integer keys."""
        pass

    def test_value_read_only(self):
        """
        Confirm attempting to assign a different value raises an exception.
        """
        pass

    def test_create_new(self):
        """
        Confirm attempting to create a new key raises an exception.
        """
        pass

    def test_names(self):
        """Confirm the names attribute returns a list of keys."""
        pass

    def test_names_empty(self):
        """
        Confirm the names attribute returns an empty list when the parent has
        no child elements.
        """
        pass

    def test_names_attribute(self):
        """Confirm the key attribute is used to generate the names list."""
        pass

    def test_names_type(self):
        """Confirm names are converted to the correct key type."""
        pass

    def test_names_read_only(self):
        """
        Confirm attempting to assign the names attributes raises an exception.
        """
        pass

    def test_single_value_type(self):
        """
        Confirm an instance of the value type is returned when the value
        type is specified as a class.
        """
        pass

    def test_single_value_type_args(self):
        """
        Confirm the target element and extra arguments are passed to
        the value class for single-type values.
        """
        pass

    def test_value_type_by_attribute(self):
        """
        Confirm the type of value returned is selected by the type attribute
        when the value type is specified as a dictionary.
        """
        pass

    def test_value_type_by_attribute_args(self):
        """
        Confirm the target element and extra arguments are passed to
        the value class for value types selected by attribute.
        """
        pass
