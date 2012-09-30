import os
try:
    from configdb.db.interface import zookeeper_interface
except ImportError:
    from nose.exc import SkipTest
    raise SkipTest('Zookeeper not found')

from configdb.tests import *
from configdb.tests.db_interface_test_base import DbInterfaceTestBase


@attr('zookeeper')
class ZookeeperInterfaceTest(DbInterfaceTestBase, TestBase):

    TESTROOT = '/configdb-test-%d' % os.getpid()

    def init_db(self):
        return zookeeper_interface.ZookeeperInterface(
            '127.0.0.1:2181', self.get_schema(), self.TESTROOT)
