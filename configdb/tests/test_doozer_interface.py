import os
import doozer
from doozer.client import IsDirectory, NoEntity
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
        try:
            delete_all(doozer.connect(), self.TESTROOT)
        except NoEntity:
            pass
        TestBase.tearDown(self)
