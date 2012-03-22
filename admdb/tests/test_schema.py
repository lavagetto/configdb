from admdb import exceptions
from admdb.db import schema
from admdb.tests import *
from datetime import datetime


class SchemaTest(TestBase):

    def test_empty_schema_ok(self):
        s = schema.Schema('{}')
        self.assertEquals({}, s.entities)

    def test_entity_without_name(self):
        data = """
{ "ent": {
  "address": {
    "type": "string"
  } }
}
"""
        self.assertRaises(exceptions.SchemaError,
                          schema.Schema,
                          data)

    def test_entity_with_bad_name(self):
        data = """
{ "$$!*": {
  "name": {
    "type": "string"
  },
  "address": {
    "type": "string"
  }
 }
}
"""
        self.assertRaises(exceptions.SchemaError,
                          schema.Schema,
                          data)

    def test_field_with_wrong_type(self):
        data = """
{ "ent": {
  "name": {
    "type": "string"
  },
  "address": {
    "type": "foo"
  }
 }
}
"""
        self.assertRaises(exceptions.SchemaError,
                          schema.Schema,
                          data)

    def test_field_with_bad_name(self):
        data = """
{ "ent": {
  "name": {
    "type": "string"
  },
  "$address": {
    "type": "string"
  }
 }
}
"""
        self.assertRaises(exceptions.SchemaError,
                          schema.Schema,
                          data)

    def test_referential_integrity_violation(self):
        data = """
{ "ent": {
  "name": {
    "type": "string"
  },
  "address": {
    "type": "relation",
    "rel": "other_entity"
  }
 }
}
"""
        self.assertRaises(exceptions.SchemaError,
                          schema.Schema,
                          data)

    def test_single_entity_schema(self):
        data = """
{ "ent": {
  "name": {
    "type": "string"
  },
  "address": {
    "type": "string"
  },
  "_help": "an entity"
 }
}
"""
        s = schema.Schema(data)
        ent = s.get_entity('ent')
        self.assertTrue(ent)
        self.assertTrue('name' in ent.fields)
        self.assertTrue('address' in ent.fields)
        self.assertEquals('an entity', ent.description)


class FakeRole(object):

    def __init__(self, name):
        self.name = name


class FakeEnt(object):

    def __init__(self, name, stamp, roles):
        self.name = name
        self.stamp = stamp
        self.roles = roles


class SchemaSerializationTest(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        data = """
{
"ent": {
  "name": {
    "type": "string"
  },
  "stamp": {
    "type": "datetime"
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
"""
        self.schema = schema.Schema(data)
        self.ent = self.schema.get_entity('ent')

    def test_missing_data_serialized_as_none(self):
        data = {'name': 'a',
                'stamp': datetime(2006, 1, 1)}
        self.assertEquals(
            {'name': 'a',
             'roles': None,
             'stamp': '2006-01-01T00:00:00'},
            self.ent.to_net(data))

    def test_missing_data_ignored(self):
        data = {'name': 'a'}
        self.assertEquals(
            {'name': 'a'},
            self.ent.to_net(data, ignore_missing=True))

    def test_relation_data_serialization(self):
        data = {'name': 'a',
                'roles': ['role1', 'role2'],
                'stamp': datetime(2006, 1, 1)}
        self.assertEquals(
            {'name': 'a',
             'roles': ['role1', 'role2'],
             'stamp': '2006-01-01T00:00:00'},
            self.ent.to_net(data))

    def test_object_serialization(self):
        obj = FakeEnt('a', datetime(2006, 1, 1),
                      [FakeRole('role1'), FakeRole('role2')])
        self.assertEquals(
            {'name': 'a',
             'roles': ['role1', 'role2'],
             'stamp': '2006-01-01T00:00:00'},
            self.ent.to_net(obj))

    def test_deserialization(self):
        data = {'name': 'a',
                'roles': ['role1', 'role2'],
                'stamp': '2006-01-01T00:00:00'}
        self.assertEquals(
            {'name': 'a',
             'roles': ['role1', 'role2'],
             'stamp': datetime(2006, 1, 1)},
            self.ent.from_net(data))

    def test_deserialization_none(self):
        data = {'name': None,
                'roles': [],
                'stamp': None}
        self.assertEquals(
            {'name': None,
             'roles': [],
             'stamp': None},
            self.ent.from_net(data))

    def test_deserialization_error(self):
        data = {'stamp': 'not-a-timestamp'}
        self.assertRaises(
            ValueError,
            self.ent.from_net, data)
