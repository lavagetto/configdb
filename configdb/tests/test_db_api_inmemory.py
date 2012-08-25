from configdb import exceptions
from configdb.db import db_api
from configdb.db import acl
from configdb.db.interface import inmemory_interface
from configdb.tests import *
from configdb.tests.db_api_test_base import DbApiTestBase


class DbApiTest(DbApiTestBase, TestBase):

    def setUp(self):
        TestBase.setUp(self)
        DbApiTestBase.setUp(self)

    def init_db(self):
        return inmemory_interface.InMemoryDbInterface(self.get_schema())
