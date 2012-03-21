import json
import re
from admdb.db import acl
from admdb.db import validation
from admdb import exceptions

ENTITY_NAME_PATTERN = re.compile(r'^[-_a-z0-9]+$')
FIELD_NAME_PATTERN = re.compile(r'^[a-z][-_a-z0-9]*$')


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

    def to_net(self, value):
        """Convert value for this field to net format."""
        return value


class BoolField(Field):

    def __init__(self, entity, name, attrs):
        # Force a specific validator.
        attrs['validator'] = 'bool'
        Field.__init__(self, entity, name, attrs)


class DateField(Field):

    def __init__(self, entity, name, attrs):
        # Force a specific validator.
        attrs['validator'] = 'iso_timestamp'
        Field.__init__(self, entity, name, attrs)

    def to_net(self, value):
        if value:
            return value.isoformat()


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

    def to_net(self, value):
        # Return list-of-strings as they are, but assume list of
        # database objects otherwise.
        if (isinstance(value, list)
            and (not len(value) or not isinstance(value[0], basestring))):
            return [x.name for x in value]
        else:
            return value


# Table of known field types.
TYPE_MAP = {
    'string': Field,
    'password': Field,
    'text': Field,
    'binary': Field,
    'int': Field,
    'bool': BoolField,
    'datetime': DateField,
    'relation': Relation,
    }

KNOWN_TYPES = TYPE_MAP.keys()


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
            elif FIELD_NAME_PATTERN.match(name):
                # Set some defaults for the special 'name' field.
                if name == 'name':
                    attrs.update({'unique': True,
                                  'index': True,
                                  'nullable': False})
                ftype = attrs.get('type', 'string').lower()
                if ftype not in TYPE_MAP:
                    raise exceptions.SchemaError(
                        'field "%s" has unknown type "%s"' % (name, ftype))
                self.fields[name] = TYPE_MAP[ftype](self, name, attrs)
            else:
                raise exceptions.SchemaError(
                    'invalid field name "%s"' % name)
        if 'name' not in self.fields:
            raise exceptions.SchemaError('missing required "name" field')

    def to_net(self, item, ignore_missing=False):
        if isinstance(item, dict):
            attr_getter = lambda x, y: x.get(y)
        else:
            attr_getter = getattr
        return dict(
            (field.name, field.to_net(
                    attr_getter(item, field.name)))
            for field in self.fields.itervalues()
            if not (ignore_missing and attr_getter(item, field.name) is None))


class Schema(object):
    """A complete database schema.

    A schema consists of multiple Entities, each having multiple
    Fields. The definition is loaded from JSON-encoded data.
    """

    def __init__(self, json_data):
        self.tables = {}
        schema_data = json.loads(json_data)
        for tname, tdata in schema_data.iteritems():
            if not ENTITY_NAME_PATTERN.match(tname):
                raise exceptions.SchemaError(
                    'invalid entity name "%s"' % tname)
            self.tables[tname] = Entity(tname, tdata)
        self._relation_check()

    def _relation_check(self):
        """Verify that all relations reference existing entities."""
        seen = set()
        for entity in self.get_entities():
            for field in entity.fields.itervalues():
                if field.is_relation():
                    seen.add(field.remote_name)
        missing = seen - set(self.tables.keys())
        if missing:
            raise exceptions.SchemaError(
                'undefined entities referenced in relations: %s' % (
                    ', '.join(missing)))

    def get_entity(self, name):
        return self.tables.get(name)

    def get_entities(self):
        return self.tables.itervalues()
