
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



Performance
-----------

Performance will be typical of most simple web applications: if you
need a significant number of updates per second this is probably not
the right technology to use.

On the other hand, read performance can easily be scaled upwards
either by running more app servers (they are completely stateless),
or by taking advantage of the aggressive caching layer (that uses
`Memcached`_).



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
  See the `Authentication`_ chapter for details.



.. _Flask deployment documentation: http://flask.pocoo.org/docs/
.. _SQLAlchemy: http://sqlalchemy.org/