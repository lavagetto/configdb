import unittest
import shutil
import tempfile
from configdb.db import schema


TEST_SCHEMA = '''
{
"host": {
  "name": {
    "type": "string"
  },
  "ip": {
    "type": "string",
    "validator": "ip"
  },
  "ip6": {
    "type": "string"
  },
  "roles": {
    "type": "relation",
    "rel": "role"
  },
  "_acl": {
    "r": "*", "w": "user/admin"
  }
},
"role": {
  "name": {
    "type": "string"
  }
},
"user": {
  "name": {
    "type": "string"
  },
  "last_login": {
    "type": "datetime"
  },
  "password": {
    "type": "password",
    "size": 64
  },
  "enabled": {
    "type": "bool",
    "default": "True"
  },
  "ssh_keys": {
    "type": "relation",
    "rel": "ssh_key",
    "acl": {
      "w": "user/admin,@self"
    }
  },
  "_acl": {
    "r": "*", "w": "user/admin"
  }
},
"ssh_key": {
  "name": {
    "type": "string"
  },
  "key": {
    "type": "text"
  },
  "_acl": {
    "w": "@users"
  }
}
}
'''


class TestBase(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._tmpdir)

    def get_schema(self):
        self._schema = schema.Schema(TEST_SCHEMA)
        return self._schema

