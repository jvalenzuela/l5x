"""
This module defines a set of classes for translating atomic data types
to and from raw data. These are the only objects that directly read or write
raw data as all other types are simply collections of these. Translation
is implemented with Python ctype structures containing a single member of
the equivalent ctype. Although each structure contains only one member,
they are used instead of simple values because structures are the
only way to define a specific byte order.

In addition to the value member, each class includes an alignment attribute
defining byte alignment when the type is part of a UDT or built-in
structure, e.g., TIMER.
"""

import ctypes


class SINT(ctypes.LittleEndianStructure):
    align = 1
    _fields_ = [('value', ctypes.c_int8)]


class INT(ctypes.LittleEndianStructure):
    align = 2
    _fields_ = [('value', ctypes.c_int16)]


class DINT(ctypes.LittleEndianStructure):
    align = 4
    _fields_ = [('value', ctypes.c_int32)]


class LINT(ctypes.LittleEndianStructure):
    align = 4 # Types exceeding 32-bit are aligned to 32-bit.
    _fields_ = [('value', ctypes.c_int64)]


class REAL(ctypes.LittleEndianStructure):
    align = 4
    _fields_ = [('value', ctypes.c_float)]
