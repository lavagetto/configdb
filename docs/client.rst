
Client
------

`admdb` provides a few ways to manipulate the underlying database,
which all expose the same create/read/update API, and enforce schema
correctness. It is important to note that usually the client will need
a copy of the schema (though it can be obtained from the API server,
the current client libraries do not implement this yet).


HTTP API
++++++++

The database API speaks a very simple JSON-based protocol. API
endpoints are exposed as verb-oriented URLs, with entity names and
(optionally) object names as path components. Requests that take
object data as input should use the POST method, with the JSON-encoded
data as the request body, and a `Content-Type` of `application/json`.

Upon receiving a 403 HTTP status code, clients should attempt to
authenticate themselves with the `login` endpoint and, if successful,
retry the request. Clients must support cookies for authentication to
work.


Python API
++++++++++

The low-level Python API closely models the database API, and it is
based around a stub API class.

See the API reference for `client.connection.Connection` for details.


Command-line Interface
++++++++++++++++++++++

The command-line client has the following syntax::

    $ admdb-client --url=API_URL <ENTITY> <VERB> [<NAME>|<OPTIONS>]

where ENTITY must be an entity defined in your schema, VERB can be one
of `create`, `mod`, `delete`, `get` or `find`, NAME is an object name,
OPTIONS is a set of `--attribute=value` long-style options
corresponding to entity fields.

Currently the client must have access to the JSON schema definition
file, so it is necessary to set the environment variable `SCHEMA_FILE`
to point to its location. In fact, for convenience it is often
advisable to set up a client wrapper script specific to your database
setup, such as the following example::

    #!/bin/sh
    export SCHEMA_FILE=/etc/mydb/schema.json
    exec admdb-client --url=http://my.db.server/ "$@"


Each entity will define a set of options corresponding to the
available fields. Option arguments are mapped to values depending on
the field type: for most fields this is just a no-op, but there are
some exceptions:

*datetime*
  Timestamps should be specified in ISO 8601 format, i.e.
  `yyyy-mm-ddThh:mm:ss` (that is a literal *T* as the separator).

*relation*
  Relation fields accept a comma-separated list of object names.

*binary*, *text*
  These fields take a file name as argument, the actual value will be
  the data read from the specified file.

*password*
  The argument value will be encrypted using the system `crypt`
  library. If set to the special value `ask`, the client will
  interactively ask the user for the new password.

The syntax for modifying relations with the command line client is as
follows::

    $ client <ENTITY> mod <NAME> {--add|--delete} \
        <ATTRIBUTE>=<OBJECT_NAME> [...]

note that ATTRIBUTE here is the singular noun version of the
relational attribute name. This, even if it might seem a bit
confusing, helps expressing the update syntax in a more natural
form. For example, with a schema containing *host* entities which in
turn have a *roles* relation attribute, one could write commands such
as::

    $ client host mod host19 --add --role=webserver



