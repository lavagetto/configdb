import json
from admdb.db import acl
from admdb.db import validation
from admdb import exceptions


class Field(acl.AclMixin, validation.ValidatorMixin):
    """A generic field of our schema."""

    def __init__(self, entity, name, attrs):
        self.set_acl(attrs.pop('acl', None))
        self.set_validator(attrs.pop('validator', None))
        self.type = attrs.pop('type', 'string')
        self.name = name
        self.attrs = attrs

    def is_relation(self):
        return False


class Relation(Field):
    """A relation to another class.

    All relations are many-to-many.
    """

    def __init__(self, entity, name, attrs):
        self.local_name = entity.name
        self.remote_name = attrs.pop('rel')
        Field.__init__(self, entity, name, attrs)

    def is_relation(self):
        return True


# Table of known field types.
type_map = {
    'string': Field,
    'password': Field,
    'text': Field,
    'binary': Field,
    'int': Field,
    #'date': DateField,
    'relation': Relation,
    }


class Entity(acl.AclMixin):
    """A schema entity ('table', or 'class', equivalently)."""

    def __init__(self, table_name, table_def):
        self.name = table_name
        self.description = None
        self.fields = {}
        for name, attrs in table_def.iteritems():
            # Check some special entity attributes.
            if name == '_acl':
                self.set_acl(attrs)
            elif name == '_help':
                self.description = attrs
            else:
                # Set some defaults for the special 'name' field.
                if name == 'name':
                    attrs.update({'unique': True,
                                  'index': True,
                                  'nullable': False})
                ftype = attrs.get('type', 'string').lower()
                if ftype not in type_map:
                    raise exceptions.SchemaError(
                        'field "%s" has unknown type "%s"' % (name, ftype))
                self.fields[name] = type_map[ftype](self, name, attrs)
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

    def get_entities(self):
        return self.tables.itervalues()
