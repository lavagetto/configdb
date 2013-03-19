import os
from nose.exc import SkipTest
try:
    import doozer
    from doozer.client import IsDirectory, NoEntity
    if os.getenv('SKIP_DOOZER') is not None:
        raise SkipTest('doozer tests disabled')
except ImportError:
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


@attr('doozer')
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
