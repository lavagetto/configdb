from collections import defaultdict
from configdb import exceptions
from configdb.db import schema
from configdb.db.interface import base


class InMemoryObjectProxy(object):

    def __init__(self, name):
        self.name = name


class InMemoryRelationProxy(object):
    """Proxy for a database relation attribute.

    Supports the list method append() and the 'in' operator, used both
    with a InMemoryObject instance or a string.
    """

    def __init__(self, objs):
        if objs is None:
            objs = []
        self._objs = set(objs)

    def append(self, obj):
        self._objs.add(obj.name)

    def remove(self, obj):
        self._objs.discard(obj.name)

    def __contains__(self, obj):
        if isinstance(obj, InMemoryObject):
            obj = obj.name
        return obj in self._objs

    def __len__(self):
        return len(self._objs)

    def __iter__(self):
        return (InMemoryObjectProxy(name) for name in self._objs)

    def __repr__(self):
        return '<InMemoryRelationProxy: [%s]>' % ', '.join(self._objs)

    def to_net(self):
        return list(self._objs)



class InMemoryObject(object):

    def __init__(self, entity, data):
        self._entity_name = entity.name
        for field in entity.fields.itervalues():
            value = data.get(field.name)
            if field.is_relation():
                value = InMemoryRelationProxy(value)
            setattr(self, field.name, value)

    def __repr__(self):
        return '<InMemoryObject: %s>' % str(self.__dict__)


class InMemorySession(object):

    def add(self, obj):
        # Does not handle renames.
        pass

    def commit(self):
        pass

    def rollback(self):
        pass


class InMemoryDbInterface(base.DbInterface):
    """Reference in-memory db implementation.

    Only useful for testing purposes.
    """

    AUDIT_SUPPORT = True

    def __init__(self, schema):
        self.schema = schema
        self._entities = defaultdict(dict)
        self._audit = []

    def session(self):
        return base.session_context_manager(InMemorySession())

    def add_audit(self, entity_name, object_name, operation,
                  data, auth_ctx, session):
        self._audit.append((entity_name, object_name, operation, data))

    def get_audit(self, query, session):
        # FIXME: apply the query.
        return self._audit

    def get_by_name(self, entity_name, object_name, session):
        return self._entities[entity_name].get(object_name, None)

    def create(self, entity_name, attrs, session):
        entity = self.schema.get_entity(entity_name)
        obj = InMemoryObject(entity, attrs)
        self._entities[entity_name][obj.name] = obj
        return obj

    def delete(self, entity_name, object_name, session):
        self._entities[entity_name].pop(object_name)

    def find(self, entity_name, query, session):
        entity = self.schema.get_entity(entity_name)
        return self._run_query(entity, query,
                               self._entities[entity_name].itervalues())
