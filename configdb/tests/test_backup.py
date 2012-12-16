import mox
import struct
import StringIO
from configdb.client import backup
from configdb.client import connection
from configdb.tests import *


class Entity(object):

    def __init__(self, name):
        self.name = name


class BackupTest(mox.MoxTestBase):

    def setUp(self):
        mox.MoxTestBase.setUp(self)
        self.conn = self.mox.CreateMock(connection.Connection)
        self.conn._schema = self.mox.CreateMockAnything()

    def test_dump_and_restore(self):
        self.conn._schema.get_dependency_sequence().AndReturn(['user', 'group'])
        self.conn.find('user',{'name': {'pattern': '^.*$', 'type': 'regexp'} }).AndReturn([
                {'id': 1, 'name': 'user1'},
                {'id': 2, 'name': 'user2'}])
        self.conn.find('group', {'name': {'pattern': '^.*$', 'type': 'regexp'}}).AndReturn([])

        self.conn.create('user', {'id': 1, 'name': 'user1'})
        self.conn.create('user', {'id': 2, 'name': 'user2'})

        self.mox.ReplayAll()

        buf = StringIO.StringIO()
        b = backup.Dumper(self.conn)
        b.dump(buf)

        self.assertTrue(buf.tell() > 0)

        buf.seek(0)
        b.restore(buf)

    def _create_record(self, entity_name, obj):
        buf = StringIO.StringIO()
        backup.record_write(buf, entity_name, obj)
        return buf.getvalue()

    def test_restore_short_read(self):
        data = ''.join([struct.pack('I', 1024), 'short record'])
        buf = StringIO.StringIO(data)

        self.mox.ReplayAll()

        b = backup.Dumper(self.conn)
        b.restore(buf)

    def test_restore_bad_crc(self):
        data = ''.join([struct.pack('I', 4), 'abcd', struct.pack('I', 42)])
        data += self._create_record('user', {'id': 1, 'name': 'user1'})
        buf = StringIO.StringIO(data)

        self.conn.create('user', {'id': 1, 'name': 'user1'})        

        self.mox.ReplayAll()

        b = backup.Dumper(self.conn)
        b.restore(buf)
        
