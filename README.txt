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


Controller
-------------------------

The controller attribute of a project has the following attributes:

tags:
	A tag scope containing controller tags; see _`Tags`.


comm_path:
	Permits reading and modifying the controller's communication path.
	Setting to None will delete the communication path.

::

	>>> prj.controller.tags['tag_name'].description = 'A controller tag'
	>>> prj.controller.comm_path
	'AB_ETHIP-1\\192.168.1.10\\Backplane\\0'

snn:
	Safety network number; see Modules_ for details.


Programs
-------------------------

A project's programs attribute contains a names attribute that evaluates
to an iterable of program names, members of which can be used as indices to
access program-scoped tags.

::

	>>> prj.programs.names
	['MainProgram', 'AnotherProgram']
	>>> prj.programs['MainProgram'].tags['a_program_tag'].value = 50


Tags
-------------------------

The top-level project contains tag scope objects, such as controller or
programs, which provide access to their respective tags. Indexing a scope
object with a tag's name will return a tag object providing access to the
various properties of the tag. An iterable of tag names can also be acquired
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

Consumed tags include these additional read/write attributes:

producer
	Name of the producing controller.

remote_tag
	Remote tag name.


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

An iterable set of member identifiers is available with the names attribute:

::

	>>> prj.controller.tags['timer'].names
	['PRE', 'ACC', 'TT', 'EN', 'DN']

Accessing the value of the structure as a whole is also possible using
dictionaries keyed by member name.

::

	d = {'PRE':0, 'ACC':0, 'EN':0, 'TT':0, 'DN':0}
	prj.controller.tags['timer'].value = d


Arrays
~~~~~~~~~~~~~~~~~~~~~~~~~

Array elements are accessed with standard index notation using integer
indices. Multidimensional arrays use a series of indices, each within their
own bracket as opposed to the comma-separated style of RSLogix.

::

	>>> prj.controller.tags['single_dim_array'][3].value = 16
	>>> prj.controller.tags['multi_dim_array'][2][5].description
	'This is multi_dim_array[2,5]'

The value of entire array is available through the value attribute using
lists. Multidimensional arrays use lists of lists and arrays of complex data
types are supported, for example an array of UDTs is a list of dicts.

::

	>>> l = [0, 1, 2, 3, 4]
	>>> prj.controller.tags['single_dim_array'].value = l
	>>> prj.controller.tags['multi_dim_array'].value
	[[0, 1], [2, 3], [4, 5]]
	

An array's dimensions may be read with the shape attribute, which returns
a tuple containing the size of each dimension. The following example shows
output for a tag of type DINT[4,3,2]. Note the tuple's reversed display order
as the number of elements in DimX is placed in shape[X].

::

	>>> prj.controller.tags['array'].shape
	(2, 3, 4)


Modules
-------------------------

The project's modules attribute provides access to modules defined in the
I/O Configuration tree. A list of modules can be obtained with the names
attribute.

::

	>> prj.modules.names
	['Controller', 'DOUT1', 'ENBT']

Each module is comprised of a set of communication ports identified by
a unique integer. Ports feature a read-only type attribute to query the
interface type and a read-write address attribute to get or set the
type-specific address. A typical example for manipulating the IP
address of an Ethernet port, which is usually port 2:

::

	>> prj.modules['ENBT'].ports[2].type
	'Ethernet'
	>> prj.modules['ENBT'].ports[2].address = '192.168.0.1'

Safety modules, including the controller, contain a read/write snn
attribute for manipulating the module's safety network number.
It evaluates to a 12-character string representing the hexadecimal
safety network number; intervening underscores as seen with RSLogix
are stripped away. Acceptable values to set a new number need not be
zero padded and may contain intervening underscores, however, it must
be a string yielding a hexadecimal number not exceeding 48 bits.

::

	>>> prj.controller.snn
	'000011112222'
	>>> prj.modules['safe_in'].snn
	'AAAABBBBCCCC'
	>>> prj.controller.snn = '42'
	>>> prj.modules['safe_out'].snn = '0001_0002_0003'
