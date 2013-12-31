# You need the etcd python client library you can find here:
# https://github.com/lavagetto/python-etcd
import os
import time
import base64
import urllib
from urlparse import urlparse
import cPickle as pickle
import json

import etcd

from configdb import exceptions
from configdb.db.interface import base
from configdb.db.interface import inmemory_interface

import logging
log = logging.getLogger(__name__)

class EtcdSession(inmemory_interface.InMemorySession):
    """A EtcdInterface session."""

    def __init__(self,db):
        self.db = db
        self.revisions = {}

    def _escape(self,s):
        return s.encode('hex')

    def _unescape(self, s):
        return s.decode('hex')

    def _mkpath(self, entity_name, obj_name=None):
        path = os.path.join(self.db.root, self._escape(entity_name))
        if obj_name:
            path = os.path.join(path, self._escape(obj_name))
        return path


    def add(self, obj, create=False):
        path = self._mkpath(obj._entity_name, obj.name)
        # If we don't have a revision,
        rev = self.revisions.get(path, None)
        log.debug("Path %s, rev %s", path, rev)
        if rev is None:
            opts = {'prevExist': False}
        else:
            opts = {'prevIndex': rev}

        if create:
            opts['prevExist'] = False

        # Will raise ValueError if the test fails.
        try:
            r = self.db.conn.write(path, self.db._serialize(obj), **opts)
            self.revisions[path] = r.modifiedIndex
        except (ValueError, KeyError):
            raise exceptions.IntegrityError('Bad revision')


    def delete(self, obj):
        self._delte_by_name(obj._entity_name, obj.name)


    def _delete_by_name(self, entity_name, obj_name):
        path = self._mkpath(entity_name, obj_name)
        try:
            rev = self.revisions.pop(path, 0)
            # etcd has no way to atomically delete objects depending on their index. Meh!
            # we simulate (coarsely) the correct behaviour
            self.db.conn.write(path, '__to_delete',prevIndex = rev)
            self.db.conn.delete(path)
        except KeyError:
            pass
        except ValueError:
            # CAS has failed
            raise exceptions.IntegrityError('Bad revision')

    def _deserialize_if_not_none(self, data):
        if data:
            return self.db._deserialize(data)
        else:
            return None

    def _get(self, entity_name, obj_name):
        path = self._mkpath(entity_name, obj_name)
        try:
            # Again, reads are not atomic in etcd and watchIndex is not useful.
            data = self.db.conn.read(path)
            self.revisions[path] = data.modifiedIndex
            return self._deserialize_if_not_none(data.value)
        except KeyError:
            pass

    def _find(self, entity_name):
        path = self._mkpath(entity_name)
        for r in self.db.conn.read(path, recursive = True).children:
            if not r.dir:
                curpath = r.key.replace(self.db.conn.key_endpoint,'')
                self.revisions[curpath] = r.modifiedIndex
                yield self._deserialize_if_not_none(r.value)

    def commit(self):
        pass

    def rollback(self):
        pass


class EtcdInterface(base.DbInterface):
    """Database interface for an Etcd backend.

    This needs the 'python-etcd' library, available at:

    https://github.com/lavagetto/python-etcd

    """

    AUDIT_SUPPORT = True
    AUDIT_LOG_LENGTH = 100

    def __init__(self, url, schema, root='/configdb', timeout=30):
        self.root = root
        self.schema = schema
        try:
            p = urlparse(url)
            host, port = p.netloc.split(':')
        except ValueError:
            raise ValueError(
                'Url {} is not in the host:port format'.format(p.netloc))

        #TODO: find a way to allow use of SSL client certificates.
        self.conn = etcd.Client(
            host=host, port=int(port), protocol = p.scheme, allow_reconnect = True)


    def _serialize(self, obj):
        return base64.b64encode(
            pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL))


    def _deserialize(self, data):
        return pickle.loads(base64.b64decode(data))

    def session(self):
        return base.session_context_manager(EtcdSession(self))

    def get_by_name(self, entity_name, object_name, session):
        return session._get(entity_name, object_name)

    def find(self, entity_name, query, session):
        entity = self.schema.get_entity(entity_name)
        return self._run_query(entity, query,
                               session._find(entity_name))


    def create(self, entity_name, attrs, session):
        entity = self.schema.get_entity(entity_name)
        obj = inmemory_interface.InMemoryObject(entity, attrs)
        session.add(obj, create=True)
        return obj

    def delete(self, entity_name, obj_name, session):
        session._delete_by_name(entity_name, obj_name)

    def close(self):
        self.conn.http.clear()


    def _get_audit_slot(self):
        path = os.path.join(self.root, '_audit', '_slots')
        retries = 10
        while retries > 0:
            try:
                res = self.conn.read(path)
            except:
                # we do not check for existence, on purpose
                self.conn.write(path, 0)
                return "0"
            slot = (int(res.value) + 1) % self.AUDIT_LOG_LENGTH
            try:
                self.conn.write(path, slot, prevIndex = res.modifiedIndex)
                return str(slot)
            except:
                retries -= 1
        #we could not apply for a slot, it seems; just give up writing
        return None

    def add_audit(self, entity_name, obj_name, operation,
                  data, auth_ctx, session):
        """Add an entry in the audit log."""
        if data is not None:
            data = self.schema.get_entity(entity_name).to_net(data)
        slot = self._get_audit_slot()
        if slot is None:
            return
        path = os.path.join(self.root, '_audit', slot)

        audit = {
            'entity': entity_name,
            'object': obj_name,
            'op': operation,
            'user': auth_ctx.get_username(),
            'data': base64.b64encode(json.dumps(data)) if data else None,
            'ts': time.time()
        }
        self.conn.write(path, json.dumps(audit))
        try:
            self.conn.write(path, json.dumps(audit))
        except ValueError:
            pass

    def get_audit(self, query, session):
        """Query the audit log."""
        # This is actually very expensive and this is why we have a limited number of slots
        path = os.path.join(self.root, '_audit')
        try:
            data = self.conn.read(path, recursive=True)
        except KeyError:
            # special case: no audit log present!
            return []
        log = []

        for result in data.children:
            obj = json.loads(result.value)
            if obj['data']:
                obj['data'] = base64.b64decode(obj['data'])
            matches = True

            for (k,v) in query.iteritems():
                if k not in obj:
                    matches = False
                    break
                if obj[k] != v:
                    matches = False
                    break

            if matches:
                log.append(obj)
        return sorted(log, key=lambda k: k['ts'])
