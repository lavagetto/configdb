import os
from nose.exc import SkipTest
try:
    from configdb.db.interface import zookeeper_interface
    if os.getenv('SKIP_ZOOKEEPER') is not None:
        raise SkipTest('Zookeeper tests disabled')
except ImportError:
    raise SkipTest('Zookeeper not found')

from configdb.tests import *
from configdb.tests.db_interface_test_base import DbInterfaceTestBase


@attr('zookeeper')
class ZookeeperInterfaceTest(DbInterfaceTestBase, TestBase):

    TESTROOT = '/configdb-test-%d' % os.getpid()

    def init_db(self):
        return zookeeper_interface.ZookeeperInterface(
            '127.0.0.1:2181', self.get_schema(), self.TESTROOT)
