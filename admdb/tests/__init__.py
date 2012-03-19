import unittest
import shutil
import tempfile
from admdb.db import schema


TEST_SCHEMA = '''
{
"host": {
  "name": {
    "type": "String"
  },
  "ip": {
    "type": "String(16)"
  },
  "ip6": {
    "type": "String(128)"
  },
  "roles": {
    "type": "relation",
    "rel": "role"
  },
  "acl": {
    "r": "*", "w": "user/admin"
  }
},
"role": {
  "name": {
    "type": "String"
  }
},
"user": {
  "name": {
    "type": "string"
  },
  "ssh_keys": {
    "type": "relation",
    "rel": "ssh_key",
    "acl": {
      "w": "user/admin,@self"
    }
  },
  "acl": {
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
  "acl": {
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

