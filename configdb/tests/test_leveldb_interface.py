import os
from configdb import exceptions
from configdb.tests import *
from configdb.db.interface import leveldb_interface


class TestSaInterface(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.dburi = os.path.join(self._tmpdir, 'db')
        self.schema = self.get_schema()

    def init_db(self):
        return leveldb_interface.LevelDbInterface(self.dburi, self.schema)

    def load_some_data(self, db):
        with db.session() as s:
            a = db.create('host', {'ip': '1.2.3.4', 'name': 'obz'}, s)
            r = db.create('role', {'name': 'role1'}, s)
            a.roles.append(r)
            s.add(a)
        
    def test_init_ok(self):
        db = self.init_db()
        self.assertTrue(db is not None)

    def test_simple_insert(self):
        db = self.init_db()
        self.load_some_data(db)

        # verify
        b = db.get_by_name('host', 'obz')
        self.assertEquals('obz', b.name)
        self.assertEquals('1.2.3.4', b.ip)
        self.assertEquals(None, b.ip6)

        r = db.get_by_name('role', 'role1')
        self.assertEquals('role1', r.name)
        self.assertTrue(r in b.roles)

    def test_find(self):
        db = self.init_db()
        self.load_some_data(db)

        r = list(db.find('host', {'name': 'obz'}))
        self.assertEquals(1, len(r))
        self.assertEquals('obz', r[0].name)

    def test_find_nonexisting_relation(self):
        db = self.init_db()
        self.load_some_data(db)

        r = list(db.find('host', {'roles': ['zzzz']}))
        self.assertEquals([], r)
        
