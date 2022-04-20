"""
This module defines a set of classes for accessing the built-in,
non-structured data types, e.g., DINT or REAL. Unless otherwise notated,
these classes are intended to be used as mixin classes, to be combined with
Tag or Member depending on if the target data is a top-level tag or
a member of a composite type.
"""

from l5x import (rawtypes, tag)
import abc
import ctypes


class Base(object):
    """Base class for all atomic types."""

    def get_raw_value(self):
        """Acquires the instance of the raw type."""
        try:
            self._raw_value

        # Instantiate the raw type from the object's buffer if it does
        # not yet exist.
        except AttributeError:
            self._raw_value = self.raw_type.from_buffer(self.raw_data)

        return self._raw_value


class DirectValue(abc.ABC):
    """
    Base class for value descriptors which directly transfer the value
    to and from the raw type without any conversion.
    """

    def __get__(self, instance, owner=None):
        return instance.get_raw_value().value

    def __set__(self, instance, value):
        self._validate(instance, value)
        instance.get_raw_value().value = value

    @abc.abstractmethod
    def _validate(self, instance, value):
        """Verifies a given value is permissible when setting."""
        pass


def raw_storage(cls):
    """Decorator to define raw data properties when stored in a structure."""
    cls.raw_size = ctypes.sizeof(cls.raw_type)

    # Alignment in a structure's raw data is equal to the type's size up
    # to 4; types larger than 4 bytes are aligned to 4 bytes.
    cls.align = cls.raw_size if cls.raw_size <= 4 else 4

    return cls


class IntegerValue(DirectValue):
    """Descriptor class for accessing an integer's value."""

    def _validate(self, instance, value):
        if not isinstance(value, int):
            raise TypeError('Value must be an integer')
        if (value < instance.value_min) or (value > instance.value_max):
            raise ValueError('Value out of range')


class Integer(Base):
    """Base class for integer data types."""

    value = IntegerValue()

    def __getitem__(self, bit):
        """Implements integer indexing to access a single bit."""
        self._validate_bit_number(bit)
        buf = BOOL.get_bit_buffer(self.raw_data, bit)
        operand = self._get_bit_operand(bit)
        raw_bit = BOOL.get_bit_position(bit)
        return IntegerBit(self.tag, buf, operand, bit=raw_bit)

    def _validate_bit_number(self, bit):
        """Verifies a given bit index."""
        if not isinstance(bit, int):
            raise TypeError('Bit indices must be integers.')
        if (bit < 0) or (bit >= self.bits):
            raise IndexError('Bit index out of range')

    def _get_bit_operand(self, bit):
        """Builds a string to identify a given bit's comment.

        Member bits are identified by <int>.<bit> where <int> is the
        integer's operand.
        """
        return '.'.join((self.operand, str(bit)))


def integer_limits(cls):
    """Decorator for integer classes to compute limits from raw data type."""
    cls.bits = cls.raw_size * 8
    mbits = cls.bits - 1 # Number of bits allotted for the magnitude.
    cls.value_min = -2 ** mbits
    cls.value_max = (2 ** mbits) - 1
    return cls


@integer_limits
@raw_storage
class SINT(Integer):
    """Mixin class for handling SINT tags."""

    raw_type = rawtypes.SINT


@integer_limits
@raw_storage
class INT(Integer):
    """Mixin class for handling INT tags."""

    raw_type = rawtypes.INT


@integer_limits
@raw_storage
class DINT(Integer):
    """Mixin class for handling DINT tags."""

    raw_type = rawtypes.DINT


@integer_limits
@raw_storage
class LINT(Integer):
    """Mixin class for handling LINT tags."""

    raw_type = rawtypes.LINT


class RealValue(DirectValue):
    """Descriptor class for accessing REAL values."""

    def _validate(self, instance, value):
        if not isinstance(value, float):
            raise TypeError('Value must be a float')

        # Check for NaN and infinite values.
        try:
            value.as_integer_ratio()
        except (OverflowError, ValueError):
            raise ValueError('NaN and infinite values are not supported')


@raw_storage
class REAL(Base):
    """Mixin class for handling REAL tags."""

    raw_type = rawtypes.REAL
    value = RealValue()


class BoolValue(object):
    """Descriptor class accessing a BOOL value.

    This handles mapping 0/False and 1/True values to a specific bit
    within the BOOL's raw storage integer.
    """

    def __get__(self, instance, owner=None):
        mask = instance.get_mask()
        raw = instance.get_raw_value().value
        return 1 if (raw & mask) else 0

    def __set__(self, instance, value):
        self._validate(value)
        raw = instance.get_raw_value()
        before = raw.value
        mask = instance.get_mask()
        after = (before | mask) if value else (before & ~mask)
        raw.value = after

    def _validate(self, value):
        """Confirms a given value is the correct type and range."""
        if not isinstance(value, int):
            raise TypeError('Bit values must be integers or booleans')
        elif (value < 0) or (value > 1):
            raise ValueError('Bit values may only be 0 or 1')


class BOOL(Base):
    """Mixin class handling BOOL tags.

    This class does not utilize the @raw_storage decorator because BOOLs are
    not stored independently within structures or arrays.
    """

    value = BoolValue()

    # BOOLs are always packed into SINTs.
    raw_type = rawtypes.SINT

    # When stored in larger collections, i.e., arrays or structures, BOOL
    # elements are always packed into SINTs, so they do not directly
    # contribute to the enclosing data type's raw data size.
    raw_size = 0

    # Default for top-level tag instances where the bit is not provided;
    # in those cases the raw data byte always uses bit 0. Instances that
    # are part of a larger structure or array will mask this with an instance
    # attribute.
    bit = 0

    @staticmethod
    def get_bit_buffer(buffer, bit):
        """Creates a buffer targeting the byte containing a given bit."""
        index = bit // 8
        return memoryview(buffer)[index : index + 1]

    @staticmethod
    def get_bit_position(bit):
        """Calculates the target bit within a SINT."""
        return bit % 8

    def get_mask(self):
        """Generates a mask identifying the target bit."""
        try:
            self._mask
        except AttributeError:
            self._mask = 1 << self.bit
        return self._mask


class IntegerBit(BOOL, tag.Member):
    """Class for accessing individual bits within an integer.

    This is a specialization of BOOL because integer bits are an implicit
    type, e.g., they are not explicitly defined as part of a structure or
    array, but are automatically present for every integer type.

    It is also a concrete class, already including all necessary superclasses,
    as integer bits are only ever instantiated by indexing integer objects.
    """

    @property
    def data_type(self):
        """
        Override for the superclass's data_type descriptor because integer
        bits do not have a defining element, which is normally used to
        extract the data type.
        """
        return 'BOOL'
