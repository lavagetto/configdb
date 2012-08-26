import os
import urllib
import cPickle as pickle

import kazoo.client
import kazoo.exceptions

from configdb import exceptions
from configdb.db.interface import base
from configdb.db.interface import inmemory_interface


class ZookeeperSession(object):
    """A ZookeeperInterface session."""

    def __init__(self, db):
        self.db = db
        self.revisions = {}

    def _escape(self, s):
        return urllib.quote(s, safe='')

    def _unescape(self, s):
        return urllib.unquote(s)

    def _mkpath(self, entity_name, obj_name=None):
        path = os.path.join(self.db.root, self._escape(entity_name))
        if obj_name:
            path = os.path.join(path, self._escape(obj_name))
        return path

    def add(self, obj):
        path = self._mkpath(obj._entity_name, obj.name)
        rev = self.revisions.get(path, -1)
        try:
            if rev < 0:
                self.db.conn.ensure_path(path)
            stat = self.db.conn.set(
                path,
                self.db._serialize(obj),
                rev)
            self.revisions[path] = stat.version
        except kazoo.exceptions.BadVersionException:
            raise exceptions.IntegrityError('Bad revision')

    def delete(self, obj):
        self._delete_by_name(obj._entity_name, obj.name)

    def _delete_by_name(self, entity_name, obj_name):
        path = self._mkpath(entity_name, obj_name)
        if path in self.revisions:
            try:
                rev = self.revisions.pop(path)
                self.db.conn.delete(path, rev)
            except kazoo.exceptions.BadVersionException:
                raise exceptions.IntegrityError('Bad revision')

    def _deserialize_if_not_none(self, data):
        if data:
            return self.db._deserialize(data)
        else:
            return None

    def _get(self, entity_name, obj_name):
        path = self._mkpath(entity_name, obj_name)
        rev = self.revisions.get(path, -1)
        try:
            data, stat = self.db.conn.get(path, rev)
            if rev < 0:
                self.revisions[path] = stat.version
        except kazoo.exceptions.BadVersionException:
            data, stat = self.db.conn.get(path)
            self.revisions[path] = stat.version
        except kazoo.exceptions.NoNodeException:
            return None
        return self._deserialize_if_not_none(data)

    def _find(self, entity_name):
        path = self._mkpath(entity_name)
        for name in self.db.conn.get_children(path):
            yield self._get(entity_name, self._unescape(name))

    def commit(self):
        pass

    def rollback(self):
        pass


class ZookeeperInterface(base.DbInterface):
    """Database interface for a Zookeeper-based backend.

    This needs the 'kazoo' library, available at:

        http://github.com/python-zk/kazoo

    """

    def __init__(self, hosts, schema, root, timeout=30):
        self.conn = kazoo.client.KazooClient(hosts, timeout=timeout)
        self.conn.start()
        self.schema = schema
        self.root = root

    def _serialize(self, obj):
        return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

    def _deserialize(self, data):
        return pickle.loads(data)

    def session(self):
        return base.session_context_manager(ZookeeperSession(self))

    def add_audit(self, entity_name, object_name, operation,
                  data, auth_ctx, session):
        pass

    def get_audit(self, query, session):
        return []

    def get_by_name(self, entity_name, object_name, session):
        return session._get(entity_name, object_name)

    def find(self, entity_name, query, session):
        entity = self.schema.get_entity(entity_name)
        return self._run_query(entity, query,
                               session._find(entity_name))

    def create(self, entity_name, attrs, session):
        entity = self.schema.get_entity(entity_name)
        obj = inmemory_interface.InMemoryObject(entity, attrs)
        session.add(obj)
        return obj

    def delete(self, entity_name, object_name, session):
        session._delete_by_name(entity_name, object_name)

    def close(self):
        self.conn.stop()
