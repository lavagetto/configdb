import json
from admdb.db import acl
from admdb import exceptions


class Field(acl.AclMixin):
    """A generic field of our schema."""

    def __init__(self, entity, name, attrs):
        self.set_acl(attrs.pop('acl', None))
        self.type = attrs.pop('type', 'string')
        self.name = name
        self.attrs = attrs


class Relation(Field):
    """A relation to another class.

    All relations are many-to-many.
    """

    def __init__(self, entity, name, attrs):
        self.local_name = entity.name
        self.remote_name = attrs.pop('rel')
        Field.__init__(self, entity, name, attrs)


class Entity(acl.AclMixin):
    """A schema entity ('table', or 'class', equivalently)."""

    def __init__(self, table_name, table_def):
        self.name = table_name
        self.fields = {}
        for name, attrs in table_def.iteritems():
            # 'acl' is a special entity attribute.
            if name == 'acl':
                self.set_acl(attrs)
                continue
            # Set some defaults for the special 'name' field.
            if name == 'name':
                attrs.update({'unique': True,
                              'index': True,
                              'nullable': False})
            if attrs['type'] == 'relation':
                field = Relation(self, name, attrs)
            else:
                field = Field(self, name, attrs)
            self.fields[name] = field
        if 'name' not in self.fields:
            raise exceptions.SchemaError('missing required "name" field')


class Schema(object):
    """A complete database schema.

    A schema consists of multiple Entities, each having multiple
    Fields. The definition is loaded from JSON-encoded data.
    """

    def __init__(self, json_data):
        self.tables = {}
        schema_data = json.loads(json_data)
        for tname, tdata in schema_data.iteritems():
            self.tables[tname] = Entity(tname, tdata)

    def get_entity(self, name):
        return self.tables.get(name)

    def get_tables(self):
        return self.tables
