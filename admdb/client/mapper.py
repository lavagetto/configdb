from admdb import schema


class ItemStub(object):

    def __init__(self, conn, entity, data=None):
        self._conn = conn
        self._entity = entity
        self._data = data or {}

    def __getattr__(self, attr):
        return self._data[attr]
    __getitem__ = __getattr__

    def __setattr__(self, attr, value):
        self._data[attr] = value
    __setitem__ = __setattr__

    def commit(self):
        self._conn.update(self._entity.name,
                          self._data['name'],
                          self._data)

    def delete(self):
        self._conn.delete(self._entity.name,
                          self._data['name'])


class EntityStub(object):

    def __init__(self, conn, name):
        self._conn = conn
        self.name = name

    def find(self, **query):
        return [ItemStub(self._conn, self, x)
                for x in self._conn.find(self.name, query)]

    def get(self, name):
        return ItemStub(self._conn, self,
                        self._conn.get(self.name, name))

    def create(self, **attrs):
        self._conn.create(self.name, attrs)
        return ItemStub(self._conn, self,
                        self._conn.get(self.name, attrs['name']))


class Session(object):

    def __init__(self, conn):
        self._conn = conn

    def __getattr__(self, class_name):
        return EntityStub(self._conn, class_name)


