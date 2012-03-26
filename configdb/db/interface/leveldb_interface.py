import contextlib
import json
import leveldb
import cPickle as pickle

from configdb import exceptions
from configdb.db import schema
from configdb.db.interface import base


class LevelDbRelationProxy(object):

    def __init__(self, objs):
        if objs is None:
            objs = []
        self._objs = set(x.name for x in objs)

    def append(self, obj):
        self._objs.add(obj.name)

    def __contains__(self, obj):
        if isinstance(obj, LevelDbObject):
            obj = obj.name
        return obj in self._objs


class LevelDbObject(object):

    def __init__(self, entity, data):
        self._entity = entity.name
        for field in entity.fields.itervalues():
            value = data.get(field.name)
            if value is None and not field.attrs.get('nullable', True):
                raise ValueError(
                    'NULL value for non-nullable field "%s"' % field.name)
            if field.is_relation():
                value = LevelDbRelationProxy(value)
            setattr(self, field.name, value)


class LevelDbSession(object):
    """This 'session' does not provide transaction support, only
    request batching."""

    def __init__(self, db):
        self._db = db
        self._batch = leveldb.WriteBatch()

    def _key_for_obj(self, obj):
        return self._db._key(obj._entity, obj.name)

    def add(self, obj):
        self._batch.Put(self._key_for_obj(obj),
                        self._db._serialize(obj))

    def delete(self, obj):
        self._batch.Delete(self._key_for_obj(obj))

    def commit(self):
        self._db.db.Write(self._batch, sync=True)

    def rollback(self):
        del self._batch


@contextlib.contextmanager
def session_manager(db):
    s = LevelDbSession(db)
    try:
        yield s
    except:
        s.rollback()
        raise
    else:
        s.commit()


class LevelDbInterface(base.DbInterface):
    """Interface to a local LevelDB database."""

    def __init__(self, path, schema, **kwargs):
        self.db = leveldb.LevelDB(path, **kwargs)
        self.schema = schema

    def _key(self, entity_name, object_name):
        return '%s:%s' % (entity_name, object_name)

    def _serialize(self, obj):
        return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

    def _deserialize(self, data):
        return pickle.loads(data)

    def session(self):
        return session_manager(self)

    def add_audit(self, entity_name, object_name, operation,
                  data, auth_ctx, session):
        pass

    def get_audit(self, query, session):
        return []

    def get_by_name(self, entity_name, object_name, session=None):
        try:
            return self._deserialize(
                self.db.Get(self._key(entity_name, object_name)))
        except KeyError:
            return None

    def find(self, entity_name, attrs, session=None):
        entity = self.schema.get_entity(entity_name)

        def _match(x):
            for key, value in attrs.iteritems():
                xvalue = getattr(x, key, None)
                field = entity.fields[key]
                if field.is_relation():
                    if xvalue is not None:
                        any_matches = any([x in xvalue for x in value])
                        if not any_matches:
                            return False
                if xvalue != value:
                    return False
            return True

        cursor = self.db.RangeIter('%s:' % entity_name,
                                   '%s:\xff' % entity_name)
        for key, serialized_data in cursor:
            data = self._deserialize(serialized_data)
            if _match(data):
                yield data

    def create(self, entity_name, attrs, session):
        entity = self.schema.get_entity(entity_name)
        obj = LevelDbObject(entity, attrs)
        session.add(obj)
        return obj

    def delete(self, entity_name, object_name, session):
        session.delete(self.get_by_name(entity_name, object_name, session))

