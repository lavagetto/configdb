
Database API
============

The most important component of `configdb` is the database API HTTP
server, which exports the database API to clients, providing ACL
enforcement and validation.


Performance
-----------

Performance will be typical of most simple web applications: if you
need a significant number of updates per second this is probably not
the right technology to use.

On the other hand, read performance can easily be scaled upwards
by running more app servers (they are completely stateless).




Deployment
----------

The database HTTP API component is a plain WSGI application. Have a
look at the `Flask documentation`_ to check some of the
available options for deployment.

It is advisable to pick an external HTTP server such as Apache or
NGINX to act as a front-end for the database HTTP API, as this will
provide for two features that are extremely desirable in a production
setting, namely request compression using gzip/deflate, and SSL.

These are the configuration options known to the application:

`SCHEMA_FILE`
  Location of your JSON schema definition. This option is required.

`DB_DRIVER`, `DB_URI`
  Storage backend configuration, see `Database Storage`_ for details.

`AUTH_FN`, `AUTH_CONTEXT_FN`
  See the Authentication_ chapter for details.

You will also need to set the Flask `SECRET_KEY` configuration option
to something sufficiently random.  If you're running more than one app
server, ensure that the value of `SECRET_KEY` is consistent, otherwise
you'll introduce arbitrary authentication errors.



Database Storage
----------------

The database storage can be configured using two configuration
variables:

`DB_DRIVER`
  Select the storage driver (which is `sqlalchemy` by default)

`DB_URI`
  Connection string, syntax depends on the specific storage
  driver selected.

The actual database backend is structured as a plugin, there are 
currently two database backends available:

`sqlalchemy` (default)
  This is the default SQL-based backend. It will support any SQL
  database known to `SQLAlchemy`_. The `DB_URI` should be a 
  SQLAlchemy connection string.

`leveldb`
  An experimental backend using Google's `LevelDB`_. Mostly
  written to demonstrate how to write a storage backend for a
  pure key-value store. You'll need the `py-leveldb`_ Python
  package for this to work. Here `DB_URI` must point to a path
  on the local filesystem, where the database will be created.
  Note that, since LevelDB provides no process-level locking, you
  can only have one database HTTP API process accessing the
  database at once, so make sure to pick a suitable deployment
  model.

For testing purposes, you can run a standalone instance of the
database HTTP API server with::

    $ env APP_CONFIG=path/to/my.config configdb-api-server

which will start a very simple HTTP server on port 3000.



Authentication
--------------

HTTP connections to the database API server are authenticated: configdb
has the concept of *authorized user*, and it will take advantage of
it, if possible, in ACLs and audit logs.

Authentication is token-based (set via an HTTP cookie), so the client
only has to login once per session, using an explicit authentication
endpoint (`/login`).

Since authentication is a delicate topic in every organization, the
configdb authentication support tries to be as flexible as possible. It
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
`configdb.server.auth` module, for instance:

* if your schema includes an entity representing a user, you can have
  configdb authenticate against itself::

    from configdb.server.auth import *
    AUTH_FN = user_auth_fn('user')
    AUTH_CONTEXT_FN = user_auth_context_fn('user')

  here `user` is the name of your user entity. This `user_auth_fn`
  assumes that your user entity has a `password` field encrypted using
  the system crypt() library.

* if you are handling authentication directly at the HTTP server level,
  you can use the following functions instead::

    from configdb.server.auth import *
    AUTH_FN = external_auth_fn
    AUTH_CONTEXT_FN = external_auth_context_fn

  These functions will work with any external authentication method
  that sets the `REMOTE_USER` variable in the WSGI environment. The
  ACL context created will not attempt to look up the user in the
  configdb database though, so the `@self` ACL rule will not be
  available.

* if you are not interested in authentication at all, perhaps because
  you're running on a trusted network and your schema uses no ACLs, it
  is possible to bypass authentication entirely by adding this to the
  app configuration file::

    AUTH_BYPASS = True





.. _Flask documentation: http://flask.pocoo.org/docs/
.. _SQLAlchemy: http://sqlalchemy.org/
.. _LevelDB: http://code.google.com/p/leveldb/
.. _py-leveldb: http://code.google.com/p/py-leveldb/
