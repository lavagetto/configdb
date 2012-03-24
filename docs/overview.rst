
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
