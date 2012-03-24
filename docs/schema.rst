
Schema Reference
----------------

A schema contains a number of *entities*, which you can consider as
SQL tables. Each entity contains some *fields*, which contain the
actual data. The schema definition is an array encoded in JSON format:
a top-level array whose elements are entities, and in turn entities
are arrays containing fields. Finally, fields themselves are
represented as arrays.



Entity
++++++

An entity definition is just an array containing field definitions.

Each entity definition must include a field called *name*, which is
used as the primary key. In other words: every object in your database
must have a name, and the entity / name combination must be globally
unique.

There are two special attributes that can be specified on an entity
along the field definitions:

*_acl*
  `ACL Definition`_ for the entity itself

*_help*
  Description of the entity, shown in the command-line client help.



Field
+++++

Field names must consist of alphanumeric ASCII characters only.
A field definition can contain the following attributes:

*type* (mandatory)
  The field type. One of *string*, *int*, *number* (floating-point
  value), *bool*, *datetime*, *text*, *binary*, or the special type
  *relation* (see Relation_).

*size*
  Some field types support a maximum value size, which can be set
  with this attribute.

*validator*
  An optional validator for the field value. The validator must be one
  of: *int*, *bool*, *number*, *string*, *email*, *url*, *ip*, *cidr*,
  any other string will be interpreted as a regular expression. Of
  course, not all validators are appropriate for all field types:
  where types have only one possible meaningful validator, it is
  selected by default.

*acl*
  An `ACL Definition`_, an array describing the access policies for
  this field.

The following attributes are specific to the database backend:

*index*
  If True, create an index on this field.

*nullable*
  If False, prevent this field from being set to NULL.



Relation
++++++++

A relation is a field that references another entity. All relations
in admdb are many-to-many: as a consequence, relation fields are
always represented as lists of instance names (strings). There are no
cascading deletes, so you'll have to maintain each entity separately.

A relation field definition can contain the following attributes:

*type* (mandatory)
  Must be `relation`.

*rel* (mandatory)
  The name of the referenced entity.

*acl*
  An `ACL Definition`_.

In the current implementation, relation fields can be empty.

You should define each relation only once, backreferences are not
implemented yet but are planned (there is preliminary support for them
at the database layer).



ACL Definition
++++++++++++++

An array controlling access to a resource (an entity, or a field).
There are only two possible operations, read (`r`) and write (`w`).
The ACL definition array can contain attributes for each or both
these operations, where the value is an ACL rule list.

An ACL rule list is simply a string containing a comma-separated list
of individual ACL rules. The possible ACL rules are:

user/*USER*
  Allow access to the specified user

group/*GROUP*
  Allow access to the specified group

@self
  Allow access to the object representing the authenticated user

\*
  Allow all access

!
  Deny all access

