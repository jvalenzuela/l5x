=========================
RSLogix .L5X Interface
=========================

This package aims to implement an interface for manipulating content of
RSLogix .L5X export files using a native Pythonic approach as opposed to
dealing with raw XML.


Getting Started
-------------------------

All access to .L5X data is through a top-level Project object, instantiated
by passing a filename to the constructor. If the project is to be modified
the write method writes the updated data back to a file for importing into
RSLogix. Typical execution flow is as follows:

::

	import l5x
	prj = l5x.Project('project.L5X')

	# Read or modify data as needed.

	prj.write('modified.L5X')


Tags
-------------------------

The top-level project contains tag scope objects, such as controller or
programs, which provide access to their respective tags. Indexing a scope
object with a tag's name will return a tag object providing access to the
various properties of the tag. A list of tag names can also be acquired
from a scope's names attribute.

::

	ctl_tags = prj.controller.tags
	tag_names = ctl_tags.names
	some_tag = ctl_tags[tag_names[0]]

All tag objects have at least the following attributes:

data_type
	A string describing the tag's data type, such as DINT or TIMER.

value
	The tag's complete value, the type of which varies based on the
        tag's type. For base data types this will be a single value, such
        as an integer, however, container objects are utilized for compound
	data types such as arrays and UDTs. See documentation below for
	details. This attribute can be read to acquire the current value
	or written to set a new value.

description
	The tag's top-level comment. See data type specific
        documentation for data types which support commenting subelements
	such as individual array members or integer bits. In addition to
        normal read/write activities, setting this attribute to None will
        delete any existing comment.


Integers
~~~~~~~~~~~~~~~~~~~~~~~~~

DINT, INT, and SINT data types accept integer values.

::

	prj.controller.tags['dint_tag'].value = 42

Accessing individual bits is available via index notation with a zero-based
integer index:

::

	prj.controller.tags['dint_tag'][3].value = 1
	prj.controller.tags['dint_tag'][2].description = 'this is bit 2'


Booleans
~~~~~~~~~~~~~~~~~~~~~~~~~

Like integers, BOOL data types accept integer values, albeit only
0 or 1.


Floats
~~~~~~~~~~~~~~~~~~~~~~~~~

REAL data types use floating point values. If an integer value is desired,
it must first be converted to a float before assignment or a TypeError will
be raised. Infinite and not-a-number values may not be used.


Structures
~~~~~~~~~~~~~~~~~~~~~~~~~

Structured data types include UDTs and built-ins such as TIMER. Individual
members are accessed using the member's name as an index as follows:

::

	prj.controller.tags['timer']['PRE'].value = 100
	prj.controller.tags['timer']['DN'].description = 'done bit'

Accessing the value of the structure as a whole is also possible using
dictionaries keyed by member name.

::

	d = {'PRE':0, 'ACC':0, 'EN':0, 'TT':0, 'DN':0}
	prj.controller.tags['timer'].value = d


Arrays
~~~~~~~~~~~~~~~~~~~~~~~~~
