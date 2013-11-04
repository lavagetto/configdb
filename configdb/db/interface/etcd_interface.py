# You need the etcd python client library you can find here:
# https://github.com/lavagetto/python-etcd
import etcd
import cPickle as pickle
import os
from urlparse import urlparse
from configdb.db.interface import inmemory_interface

class EtcdSession(object):
    """A EtcdInterface session."""
    def __init__(self,db):
        self.db = db
        raise NotImplementedError

    def _mkpath(self, entity_name, object_name):
        return os.path.join(self.db.root, entity_name, object_name)

    def add(self, obj):
        path = self._mkpath(obj._entity_name, obj.name)
        #TODO: test for presence of an old object and do test_and_set
        self.db.conn.set(path, self.db._serialize(obj))


    def delete(self, obj):
        raise NotImplementedError

    def _delete_by_name(self, entity_name, obj_name):
        raise NotImplementedError

    def _deserialize_if_not_none(self, data):
        raise NotImplementedError

    def _get(self, entity_name, obj_name):
        raise NotImplementedError

    def _find(self, entity_name):
        raise NotImplementedError

    def commit(self):
        pass

    def rollback(self):
        pass


class EtcdInterface(base.DbInterface):
    """Database interface for an Etcd backend.

    This needs the 'python-etcd' library, available at:

    https://github.com/lavagetto/python-etcd

    """

    def __init__(self, url, schema, root='/configdb', timeout=30):
        self.root = root
        try:
            p = urlparse(url)
            host, port = p.netloc.split(':')
        except ValueError:
            raise ValueError('Url {} is not in the host:port format'.format(p.netloc))

        self.conn = etcd.Client(host=host, port=port, protocol = p.schema, allow_reconnect = True)


    def _serialize(self, obj):
        return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

    def _deserialize(self, data):
        return pickle.loads(data)

    def session(self):
        return base.session_context_manager(EtcdSession(self))

    def get_by_name(self, entity_name, object_name, session):
        return session._get(entity_name, object_name)

    def find(self, entity_name, query, session):
        raise NotImplementedError

    def create(self, entity_name, attrs, session):
        entity = self.schema.get_entity(entity_name)
        object =
        raise NotImplementedError

    def delete(self, entity_name, object_name, session):
        raise NotImplementedError

    def close(self):
        pass
