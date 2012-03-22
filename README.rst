
admdb
=====

`admdb` is a relational database for administrative databases
(i.e., stuff that gets read more often than written to) with a
focus on stability and usability rather than performance.

When provided with a simple JSON schema of your data, it will
offer:

 * An HTTP API to a database implementing your schema;

 * ACL and validation support for every field, and a pluggable
   authentication system (which can use objects in the database
   itself);

 * A Python client library to manipulate such database;

 * A client tool to manipulate the database from the command line.

This framework is meant for those small databases where the ability to
make quick manual changes is critical: for instance, databases used to
store configuration and management information. As an example, in our
organization we're currently using one instance of `admdb` to store
data about hosts, users and groups, and another one for source code
projects.


Database Storage
----------------

The actual database backend is structured as a plugin, but at the
moment only a SQL-based backend is available. It will support any
SQL database known to SQLAlchemy.
