from configdb.db.interface import sa_interface
from configdb.tests import *
from configdb.tests.db_interface_test_base import DbInterfaceTestBase


class TestSaInterface(DbInterfaceTestBase, TestBase):

    def init_db(self):
        dburi = 'sqlite:///:memory:'
        return sa_interface.SqlAlchemyDbInterface(dburi, self.get_schema())

