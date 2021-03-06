import os
from nose.exc import SkipTest
try:
    from configdb.db.interface import etcd_interface
    if os.getenv('SKIP_ETCD') is not None:
        raise SkipTest('Etcd tests disabled')
except ImportError:
    raise SkipTest('Etcd not found')

from configdb.tests import *
from configdb.tests.db_interface_test_base import DbInterfaceTestBase


@attr('etcd')
class EtcdInterfaceTest(DbInterfaceTestBase, TestBase):

    TESTROOT = '/configdb-test-%d' % os.getpid()

    def init_db(self):
        return etcd_interface.EtcdInterface(
            'http://127.0.0.1:4001', self.get_schema(), self.TESTROOT)


    def tearDown(self):
        db = self.init_db()
        try:
            db.conn.delete(self.TESTROOT, recursive = True)
        except KeyError:
            pass
