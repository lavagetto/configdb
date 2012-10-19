import os
try:
    import doozer
    from doozer.client import IsDirectory, NoEntity
except ImportError:
    from nose.exc import SkipTest
    raise SkipTest('doozer not found')

from configdb.db.interface import doozer_interface
from configdb.tests import *
from configdb.tests.db_interface_test_base import DbInterfaceTestBase


def delete_all(client, path):
    for file in client.getdir(path):
        fullp = os.path.join(path, file.path)
        try:
            item = client.get(fullp)
            client.delete(fullp, item.rev)
        except IsDirectory:
            delete_all(client, fullp)


class TestDoozerInterface(DbInterfaceTestBase, TestBase):

    TESTROOT = '/configdb-test-%d' % os.getpid()

    def init_db(self):
        return doozer_interface.DoozerInterface(
            None, self.get_schema(), self.TESTROOT)

    def tearDown(self):
        client = doozer.connect()
        try:
            delete_all(client, self.TESTROOT)
        except NoEntity:
            pass
        client.disconnect()
        TestBase.tearDown(self)
