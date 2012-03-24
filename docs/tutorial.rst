
Quick Tutorial
==============

This short tutorial will walk through some example use cases of
`configdb`, covering full deployment of a test system.


A Basic Schema
--------------

Let's assume, for our fictional example, that you need to build a very
simple configuration database consisting of some basic host
information.

A minimal schema for this could be::

    {
      "host": {
        "name": {
          "type": "string"
        },
        "ip": {
          "type": "string",
          "size": 16,
          "nullable": false,
          "validator": "ip"
        }
      }
    }

Now let's say that we also want to define a set of *roles* that can be
assigned to hosts (maybe in order to control their configuration
somehow). We'll define a second entity, and a relation between it and
the `host` entity::

    {
      "host": {
        "name": {
          "type": "string"
        },
        "ip": {
          "type": "string",
          "size": 16,
          "nullable": false,
          "validator": "ip"
        },
        "roles": {
          "type": "relation",
          "rel": "role"
        }
      },
      "role": {
        "name": {
          "type": "string"
        }
      }
    }

Roles have simply a name, we don't need to associate other information
with them.


Starting a Test Database Server
-------------------------------

Now, having saved the schema above to a file somewhere, say
`schema.json` in the current directory, we can try to start a test
instance of the database API HTTP server. To do so, create the
application config file first::

    AUTH_BYPASS = True
    SECRET_KEY = 'secret'
    SCHEMA_FILE = 'schema.json'
    DB_URI = 'sqlite:///data.db'

Save this in `app.conf`.

You should now be able to start the HTTP server with::

    $ env APP_CONFIG=app.conf configdb-api-server

Visiting `http://localhost:3000/schema` should return you the JSON
schema definition, it's a good test that the HTTP server is working.


Running the Command-line Client
-------------------------------

Let's try running the command-line client against the test database::

    $ alias testdb='env SCHEMA_FILE=schema.json configdb-client \
         --url=http://localhost:3000'

We can then, for instance, create a new host object and verify that it
has indeed been saved to the database::

    $ testdb host create --name=host1 --ip=1.2.3.4
    $ testdb host get host1

Or create a new role and assign it to a host::

    $ testdb role create --name=role1
    $ testdb host mod host1 --add --role=role1

