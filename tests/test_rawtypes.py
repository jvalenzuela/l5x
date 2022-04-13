"""
Unit tests for the low-level, raw data translation of atomic data types.
"""


from l5x import rawtypes
import unittest


class Base(unittest.TestCase):
    """Base class to handle common setup operations."""

    def setUp(self):
        """Create a buffer large enough to handle all data types."""
        self.buf = bytearray(8)


class ByteOrder(Base):
    """Tests to verify correct endianness.

    These are implemented by setting the value to something that yields
    an asymmetric byte pattern, e.g., only one byte non-zero.
    """

    def test_INT(self):
        """Confirm correct byte order for INT type."""
        x = rawtypes.INT.from_buffer(self.buf)
        x.value = 1
        self.assertEqual(self.buf[0], 1)

    def test_DINT(self):
        """Confirm correct byte order for DINT type."""
        x = rawtypes.DINT.from_buffer(self.buf)
        x.value = 1
        self.assertEqual(self.buf[0], 1)

    def test_LINT(self):
        """Confirm correct byte order for LINT type."""
        x = rawtypes.LINT.from_buffer(self.buf)
        x.value = 1
        self.assertEqual(self.buf[0], 1)

    def test_REAL(self):
        """Confirm correct byte order for REAL types."""
        x = rawtypes.REAL.from_buffer(self.buf)
        x.value = 2.0
        self.assertEqual(self.buf[3], 0x40)


class Size(Base):
    """Tests to verify number of bytes for raw data storage.

    These write a value that should set every byte to a non-zero value,
    then confirm the correct number of bytes have been altered.
    """

    def test_SINT(self):
        """Confirm correct number of bytes to store SINT type."""
        x = rawtypes.SINT.from_buffer(self.buf)
        x.value = -1
        self.assert_nonzero_bytes(1)

    def test_INT(self):
        """Confirm correct number of bytes to store INT type."""
        x = rawtypes.INT.from_buffer(self.buf)
        x.value = -1
        self.assert_nonzero_bytes(2)

    def test_DINT(self):
        """Confirm correct number of bytes to store DINT type."""
        x = rawtypes.DINT.from_buffer(self.buf)
        x.value = -1
        self.assert_nonzero_bytes(4)

    def test_LINT(self):
        """Confirm correct number of bytes to store LINT type."""
        x = rawtypes.LINT.from_buffer(self.buf)
        x.value = -1
        self.assert_nonzero_bytes(8)

    def test_REAL(self):
        """Confirm correct number of bytes to store REAL type."""
        x = rawtypes.REAL.from_buffer(self.buf)
        x.value = 1.1
        self.assert_nonzero_bytes(4)

    def assert_nonzero_bytes(self, expected):
        """Asserts the correct number of non-zero bytes in the buffer."""
        nz = list(filter(lambda x: x != 0, self.buf))
        self.assertEqual(expected, len(nz))


class Signed(Base):
    """Tests to verify integer types are signed.

    These set the sign bit(MSB) and confirm the resulting value is equal
    to the minimum possible.
    """

    def test_SINT(self):
        """Confirm SINT is signed."""
        self.buf[0] = 0x80
        x = rawtypes.SINT.from_buffer(self.buf)
        self.assert_min(x, 8)

    def test_INT(self):
        """Confirm INT is signed."""
        self.buf[1] = 0x80
        x = rawtypes.INT.from_buffer(self.buf)
        self.assert_min(x, 16)

    def test_DINT(self):
        """Confirm DINT is signed."""
        self.buf[3] = 0x80
        x = rawtypes.DINT.from_buffer(self.buf)
        self.assert_min(x, 32)

    def test_LINT(self):
        """Confirm LINT is signed."""
        self.buf[7] = 0x80
        x = rawtypes.LINT.from_buffer(self.buf)
        self.assert_min(x, 64)

    def assert_min(self, i, bitwidth):
        """Asserts an integer is equal to it's smallest possible value."""
        expected = -2**(bitwidth - 1)
        self.assertEqual(expected, i.value)
