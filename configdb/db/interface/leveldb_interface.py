import json
import leveldb
import cPickle as pickle

from configdb import exceptions
from configdb.db import schema
from configdb.db.interface import base
from configdb.db.interface import inmemory_interface


class LevelDbSession(object):
    """This 'session' does not provide transaction support, only
    request batching."""

    def __init__(self, db):
        self._db = db
        self._batch = leveldb.WriteBatch()

    def _key_for_obj(self, obj):
        return self._db._key(obj._entity_name, obj.name)

    def add(self, obj):
        self._batch.Put(self._key_for_obj(obj),
                        self._db._serialize(obj))

    def delete(self, obj):
        self._batch.Delete(self._key_for_obj(obj))

    def commit(self):
        self._db.db.Write(self._batch, sync=True)

    def rollback(self):
        if hasattr(self, '_batch'):
            del self._batch


class LevelDbInterface(base.DbInterface):
    """Interface to a local LevelDB database.

    The interface is pretty simple at the moment, but it's a good
    example of how to implement a database backend for configdb.

    We store lightweight InMemoryObject instances in the database,
    representing relations with sets of names.  Object serialization
    is done using the 'pickle' module.
    """

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
        return base.session_context_manager(LevelDbSession(self))

    def get_by_name(self, entity_name, object_name, session):
        try:
            return self._deserialize(
                self.db.Get(self._key(entity_name, object_name)))
        except KeyError:
            return None

    def _find_all(self, entity_name):
        cursor = self.db.RangeIter('%s:' % entity_name,
                                   '%s:\xff' % entity_name)
        for key, serialized_data in cursor:
            yield self._deserialize(serialized_data)

    def find(self, entity_name, query, session):
        entity = self.schema.get_entity(entity_name)
        return self._run_query(entity, query,
                               self._find_all(entity_name))

    def create(self, entity_name, attrs, session):
        entity = self.schema.get_entity(entity_name)
        obj = inmemory_interface.InMemoryObject(entity, attrs)
        session.add(obj)
        return obj

    def delete(self, entity_name, object_name, session):
        session.delete(self.get_by_name(entity_name, object_name, session))
