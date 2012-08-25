import os
from configdb.db.interface import leveldb_interface
from configdb.tests import *
from configdb.tests.db_api_test_base import DbApiTestBase


class DbApiLevelDbTest(DbApiTestBase, TestBase):

    def setUp(self):
        TestBase.setUp(self)
        DbApiTestBase.setUp(self)

    def init_db(self):
        dburi = os.path.join(self._tmpdir, 'db')
        return leveldb_interface.LevelDbInterface(dburi, self.get_schema())

