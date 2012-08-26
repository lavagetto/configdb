import logging
import os
import cPickle as pickle

import doozer
from doozer.client import RevMismatch, NoEntity, BadPath

from configdb import exceptions
from configdb.db.interface import base
from configdb.db.interface import inmemory_interface

log = logging.getLogger(__name__)


class DoozerSession(object):
    """A DoozerInterface session.

    This object ensures that the client maintains a consistent view of
    the data, but it won't batch changes, so both commit() and
    rollback() have no effect.
    """

    def __init__(self, db):
        self.db = db
        self.revisions = {}

    def _mkpath(self, entity_name, obj_name=None):
        # Return the Doozer path to the specified object.
        # Play it safe with valid characters in doozer paths,
        # at the expense of creating a quite obscure hierarchy.
        path = os.path.join(self.db.root,
                            entity_name.encode('hex'))
        if obj_name:
            path = os.path.join(path, obj_name.encode('hex')) 
        return path

    def add(self, obj):
        path = self._mkpath(obj._entity_name, obj.name)
        rev = self.revisions.get(path, 0)
        try:
            new_rev = self.db.conn.set(
                path,
                self.db._serialize(obj),
                rev)
            self.revisions[path] = new_rev.rev
            log.debug('set %s,rev %s oldrev %s', path, new_rev.rev, rev)
        except RevMismatch:
            raise exceptions.IntegrityError('Bad revision')

    def delete(self, obj):
        self._delete_by_name(obj._entity_name, obj.name)

    def _delete_by_name(self, entity_name, obj_name):
        path = self._mkpath(entity_name, obj_name)
        try:
            rev = self.revisions.pop(path, 0)
            log.debug('delete %s, rev %s', path, rev)
            item = self.db.conn.delete(
                path,
                rev)
        except RevMismatch:
            raise exceptions.IntegrityError('Bad revision')
        except BadPath:
            pass

    def _deserialize_if_not_none(self, data):
        if data:
            return self.db._deserialize(data)
        else:
            return None

    def _get(self, entity_name, obj_name):
        path = self._mkpath(entity_name, obj_name)
        rev = self.revisions.get(path, 0)
        try:
            item = self.db.conn.get(path, rev)
            if not rev:
                self.revisions[path] = item.rev
        except RevMismatch:
            item = self.db.conn.get(path)
            self.revisions[path] = item.rev
        except BadPath:
            return None
        return self._deserialize_if_not_none(item.value)

    def _find(self, entity_name):
        path = self._mkpath(entity_name)
        try:
            folder = self.db.conn.getdir(path)
        except NoEntity:
            return
        for entry in folder:
            obj_name = entry.path.decode('hex')
            yield self._get(entity_name, obj_name)

    def commit(self):
        pass

    def rollback(self):
        pass


class DoozerInterface(base.DbInterface):
    """Database interface for a Doozer backend.

    This needs the 'pydoozer' library, available at:

        https://github.com/progrium/pydoozer

    """

    def __init__(self, doozer_uri, schema, root='/configdb', timeout=30):
        self.conn = doozer.connect(doozer_uri, timeout)
        self.schema = schema
        self.root = root

    def _serialize(self, obj):
        return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

    def _deserialize(self, data):
        return pickle.loads(data)

    def session(self):
        return base.session_context_manager(DoozerSession(self))

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
        self.conn.disconnect()
