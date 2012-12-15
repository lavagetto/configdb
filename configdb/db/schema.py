import json
import re
from dateutil import parser as dateutil_parser
from configdb import exceptions
from configdb.db import acl
from configdb.db import validation

ENTITY_NAME_PATTERN = re.compile(r'^[-_a-z0-9]+$')
FIELD_NAME_PATTERN = re.compile(r'^[a-z][_a-z0-9]*$')
DEFAULT_ACL = {'r': '*', 'w': '*'}


class Field(acl.AclMixin, validation.ValidatorMixin):
    """A generic field of our schema.

    Complex fields that aren't directly supported by the network
    transport encoding (JSON) can inherit from this class and
    implement serialization using the to_net() / from_net() methods.

    When implementing serialization, take care of passing through the
    None value unchanged, as it has a special meaning (missing value).
    Also, if serialization fails, try to raise ValueError.
    """

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

    from_net = to_net


class BoolField(Field):

    def __init__(self, entity, name, attrs):
        # Force a specific validator.
        attrs['validator'] = 'bool'
        Field.__init__(self, entity, name, attrs)


class DateTimeField(Field):

    def to_net(self, value):
        if value:
            return value.isoformat()

    def from_net(self, value):
        if value:
            return dateutil_parser.parse(value)


class Relation(Field):
    """A relation to another class.

    All relations are many-to-many.
    """

    def __init__(self, entity, name, attrs):
        self.local_name = entity.name
        self.remote_name = attrs.pop('rel')
        attrs['validator'] = 'relation'
        if 'identifier' in attrs:
            self.relation_id = attrs['identifier']
        else:
            self.relation_id = '1'
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
    'number': Field,
    'bool': BoolField,
    'datetime': DateTimeField,
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
            elif name == 'id':
                raise exceptions.SchemaError(
                    'the "id" field is reserved')
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

    def from_net(self, data):
        return dict(
            (field.name, field.from_net(data[field.name]))
            for field in self.fields.itervalues()
            if field.name in data)


class Schema(object):
    """A database schema definition.

    A schema consists of multiple Entities, each having multiple
    Fields. The definition is loaded from JSON-encoded data.
    """

    def __init__(self, json_data):
        self.entities = {}
        schema_data = json.loads(json_data)
        for tname, tdata in schema_data.iteritems():
            if not ENTITY_NAME_PATTERN.match(tname):
                raise exceptions.SchemaError(
                    'invalid entity name "%s"' % tname)
            self.entities[tname] = Entity(tname, tdata)
        self._relation_check()
        self.default_acl = acl.AclMixin()
        self.default_acl.set_acl(DEFAULT_ACL)

    def _relation_check(self):
        """Verify that all relations reference existing entities."""
        seen = set()
        for entity in self.get_entities():
            for field in entity.fields.itervalues():
                if field.is_relation():
                    seen.add(field.remote_name)
        missing = seen - set(self.entities.keys())
        if missing:
            raise exceptions.SchemaError(
                'undefined entities referenced in relations: %s' % (
                    ', '.join(missing)))

    def get_entity(self, name):
        return self.entities.get(name)

    def get_entities(self):
        return self.entities.itervalues()

    def acl_check_fields(self, entity, fields, auth_context, op, obj):
        """Authorize an operation on the fields of an instance."""
        base_acl_check = (
            entity.acl_check(auth_context, op, obj)
            if entity.has_acl()
            else self.default_acl.acl_check(auth_context, op, obj))
        for field_name in fields:
            field = entity.fields[field_name]
            acl_check = (
                field.acl_check(auth_context, op, obj)
                if field.has_acl()
                else base_acl_check)
            if not acl_check:
                raise exceptions.AclError(
                    'unauthorized change to %s.%s' % (
                        entity.name, field_name))

    def acl_check_entity(self, entity, auth_context, op, obj):
        """Authorize an operation on an entity."""
        acl_check = (
            entity.acl_check(auth_context, op, obj)
            if entity.has_acl()
            else self.default_acl.acl_check(auth_context, op, obj))
        if not acl_check:
            raise exceptions.AclError(
                'unauthorized change to %s' % (
                    entity.name,))


    def get_dependency_sequence(self):
        sequence = []
        #create a copy of the entities dict.
        entities = self.entities.copy()
        while entities:
            additions = []
            for entity in entities.itervalues():
                valid = True
                for (name, field) in entity.fields.iteritems():
                    if field.is_relation() and field.remote_name not in sequence:
                        # We have a relation which is still not rolled out.
                        valid = False
                        break
                if valid:
                    sequence.append(entity.name)
                    additions.append(entity.name)
            for name in additions:
                del entities[name]
        return sequence
                    
    
