
=======
 admdb
=======

`admdb` is a relational database for administrative databases (i.e.,
stuff that gets read more often than written to) with a focus on
stability and usability rather than performance.

When provided with a simple JSON schema of your data, it will offer:

* An HTTP API to a database implementing your schema;

* ACL and validation support for every field, and a pluggable
  authentication system (which can use objects in the database
  itself);

* a Python client library to manipulate such database;

* a client tool to manipulate the database from the command line.

This framework is meant for those small databases where the ability to
make quick manual changes is critical: for instance, databases used to
store configuration and management information. As an example, in our
organization we're currently using one instance of `admdb` to store
data about hosts, users and groups, and another one for source code
projects.

When managing systems, there is often the necessity of this kind of
lightweight authoritative database. `admdb` is meant to remove the
tedium of writing your own solution: just craft an appropriate schema,
and the management functionality is already taken care of.



Caveats and Limitations
-----------------------

Plenty, of course:

* The relational capabilities of the schema are (purposedly) limited,
  as it will only model many-to-many relations.

* The performance characteristics are sub-optimal: serialization and
  validation have their cost. Furthermore, the network transport is
  HTTP, which adds overhead, etc.

* Transaction support is limited to what is provided by the underlying
  SQL storage backend (so, possibly, none).



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
always represented as lists of instance names (strings).

A relation field definition can contain the following attributes:

*type* (mandatory)
  Must be `relation`.

*rel* (mandatory)
  The name of the referenced entity.

*acl*
  An `ACL Definition`_.

In the current implementation, relation fields can be empty.



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



Performance
-----------

Performance will be typical of most simple web applications: if you
need a significant number of updates per second this is probably not
the right technology to use.

On the other hand, read performance can easily be scaled upwards
by running more app servers (they are completely stateless).



Database Storage
----------------

The actual database backend is structured as a plugin, but at the
moment only a SQL-based backend is available. It will support any SQL
database known to `SQLAlchemy`_.


For testing purposes, you can run a standalone instance of the
database HTTP API server with::

    $ env APP_CONFIG=path/to/my.config admdb-api-server

which will start a very simple HTTP server on port 3000.



Deployment
----------

The database HTTP API component is a plain WSGI application. Have a
look at the `Flask deployment documentation`_ to check some of the
available options for deployment.

It is advisable to pick an external HTTP server such as Apache or
NGINX to act as a front-end for the database HTTP API, as this will
provide for two features that are extremely desirable in a production
setting, namely request compression using gzip/deflate, and SSL.

These are the configuration options known to the application:

`SCHEMA_FILE`
  Location of your JSON schema definition. This option is required.

`DB_URI`
  Database connection string (it will be passed to SQLAlchemy).

`AUTH_FN`
`AUTH_CONTEXT_FN`
  See the Authentication_ chapter for details.

You will also need to set the Flask `SECRET_KEY` configuration option
to something sufficiently random.  If you're running more than one app
server, ensure that the value of `SECRET_KEY` is consistent, otherwise
you'll introduce arbitrary authentication errors.



Authentication
--------------

HTTP connections to the database API server are authenticated: admdb
has the concept of *authorized user*, and it will take advantage of
it, if possible, in ACLs and audit logs.

Authentication is token-based (set via an HTTP cookie), so the client
only has to login once per session, using an explicit authentication
endpoint (`/login`).

Since authentication is a delicate topic in every organization, the
admdb authentication support tries to be as flexible as possible. It
works by providing an authentication layer abstraction that you can 
extend to adapt it to your schema, or to integrate it with external
systems. The API consists of two functions, configurable via the Flask
application config:

`AUTH_FN`
  The authentication function. This will be called by the /login API
  endpoint, and it should use the request data to authenticate the
  caller. The function signature should be::

      def auth_fn(db_api, request_data):

  and it should return `None` if the authentication failed, or an
  authentication token if successful, which will be associated with
  the client session and passed to the `AUTH_CONTEXT_FN`.

`AUTH_CONTEXT_FN`
  Every request to the database API has an associated *authentication
  context*, which is used by the ACL rules. An authentication context
  can optionally provide a username and a set of groups that the user
  belongs to (for user- and group-matching ACL rules), and a reference
  to a "self" object. See the API documentation for the
  `acl.AuthContext` class for details.

  This method will be called with the session authentication token as
  its only argument, and it should return an `acl.AuthContext`
  instance.

Naturally, more complex implementations of these functions might
require changes in the authentication request data provided by the
client, which by default passes `username` and `password` attributes.

Some standard implementations of these functions are provided in the
`admdb.server.auth` module, for instance:

* if your schema includes an entity representing a user, you can have
  admdb authenticate against itself::

    from admdb.server.auth import *
    AUTH_FN = user_auth_fn('user')
    AUTH_CONTEXT_FN = user_auth_context_fn('user')

  here `user` is the name of your user entity. This `user_auth_fn`
  assumes that your user entity has a `password` field encrypted using
  the system crypt() library.

* if you are handling authentication directly at the HTTP server level,
  you can use the following functions instead::

    from admdb.server.auth import *
    AUTH_FN = external_auth_fn
    AUTH_CONTEXT_FN = external_auth_context_fn

  These functions will work with any external authentication method
  that sets the `REMOTE_USER` variable in the WSGI environment. The
  ACL context created will not attempt to look up the user in the
  admdb database though, so the `@self` ACL rule will not be
  available.

* if you are not interested in authentication at all, perhaps because
  you're running on a trusted network and your schema uses no ACLs, it
  is possible to bypass authentication entirely by adding this to the
  app configuration file::

    AUTH_BYPASS = True




.. _Flask deployment documentation: http://flask.pocoo.org/docs/
.. _SQLAlchemy: http://sqlalchemy.org/
