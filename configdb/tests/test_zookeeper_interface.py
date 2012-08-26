import os
from configdb.db.interface import zookeeper_interface
from configdb.tests import *
from configdb.tests.db_interface_test_base import DbInterfaceTestBase


class ZookeeperInterfaceTest(DbInterfaceTestBase, TestBase):

    TESTROOT = '/configdb-test-%d' % os.getpid()

    def init_db(self):
        return zookeeper_interface.ZookeeperInterface(
            '127.0.0.1:2181', self.get_schema(), self.TESTROOT)