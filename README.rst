
Overview
--------

`configdb` is a relational database for administrative databases (i.e.,
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
organization we're currently using one instance of `configdb` to store
data about hosts, users and groups, and another one for source code
projects.

When managing systems, there is often the necessity of this kind of
lightweight authoritative database. `configdb` is meant to remove the
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

* Transaction support is currently limited to what is provided by the
  underlying SQL storage backend (so, possibly, none).


