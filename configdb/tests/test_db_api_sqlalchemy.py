from configdb.db.interface import sa_interface
from configdb.tests import *
from configdb.tests.db_api_test_base import DbApiTestBase


class DbApiSqlAlchemyTest(DbApiTestBase, TestBase):

    def setUp(self):
        TestBase.setUp(self)
        DbApiTestBase.setUp(self)

    def init_db(self):
        dburi = 'sqlite:///:memory:'
        return sa_interface.SqlAlchemyDbInterface(dburi, self.get_schema())
