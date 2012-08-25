import mox
import os
import tempfile
import shutil
from configdb.db import schema
from configdb.client import cli
from configdb.client import connection
from configdb.client import query
from configdb.tests import *



class CliMainTest(mox.MoxTestBase):

    def setUp(self):
        mox.MoxTestBase.setUp(self)
        self.mox.StubOutWithMock(os, 'getenv')
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._tmpdir)
        mox.MoxTestBase.tearDown(self)

    def test_schema_file_unset(self):
        os.getenv('SCHEMA_FILE').AndReturn(None)
        self.mox.ReplayAll()
        self.assertEquals(1, cli.main([]))

    def test_schema_file_non_existing(self):
        os.getenv('SCHEMA_FILE').AndReturn(
            os.path.join(self._tmpdir, 'missing.json'))
        self.mox.ReplayAll()
        self.assertEquals(1, cli.main([]))

    def test_schema_file_invalid_json(self):
        schemaf = os.path.join(self._tmpdir, 'schema.json')
        with open(schemaf, 'w') as fd:
            fd.write('{"invalid json":,}')

        os.getenv('SCHEMA_FILE').AndReturn(schemaf)
        self.mox.ReplayAll()
        self.assertEquals(1, cli.main([]))

    def test_schema_file_invalid_schema(self):
        schemaf = os.path.join(self._tmpdir, 'schema.json')
        with open(schemaf, 'w') as fd:
            fd.write('{"entity":{}}')

        os.getenv('SCHEMA_FILE').AndReturn(schemaf)
        self.mox.ReplayAll()
        self.assertEquals(1, cli.main([]))


class CliTest(mox.MoxTestBase):

    def setUp(self):
        mox.MoxTestBase.setUp(self)
        self.mox.StubOutWithMock(connection, 'Connection', 
                                 use_mock_anything=True)
        self.mox.StubOutWithMock(os, 'getenv')
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._tmpdir)
        mox.MoxTestBase.tearDown(self)

    def _connect(self):
        schema_file = os.path.join(self._tmpdir, 'schema.json')
        with open(schema_file, 'w') as fd:
            fd.write(TEST_SCHEMA)
        os.getenv('SCHEMA_FILE').AndReturn(schema_file)

        self.conn = self.mox.CreateMockAnything()
        connection.Connection(mox.IsA(str), mox.IsA(schema.Schema),
                              username=None, auth_file=mox.IsA(str)
                              ).AndReturn(self.conn)

    def test_get_object(self):
        self._connect()
        self.conn.get('host', 'obz').AndReturn('ok')
        self.mox.ReplayAll()

        self.assertEquals(
            0, cli.main(['host', 'get', 'obz']))

    def test_find_object(self):
        self._connect()
        self.conn.find('host', query.Query(name=query.Equals('obz'))
                       ).AndReturn(['ok'])
        self.mox.ReplayAll()

        self.assertEquals(
            0, cli.main(['host', 'find', '--name=obz']))

    def test_find_object_by_relation(self):
        self._connect()
        self.conn.find('host', query.Query(roles=query.Equals('role1'))
                       ).AndReturn(['ok'])
        self.mox.ReplayAll()

        self.assertEquals(
            0, cli.main(['host', 'find', '--roles=role1']))

    def test_find_object_by_regexp(self):
        self._connect()
        self.conn.find('host', query.Query(name=query.RegexpMatch('^o'))
                       ).AndReturn(['ok'])
        self.mox.ReplayAll()

        self.assertEquals(
            0, cli.main(['host', 'find', '--name=~^o']))

    def test_find_object_by_substring(self):
        self._connect()
        self.conn.find('host', query.Query(name=query.SubstringMatch('bz'))
                       ).AndReturn(['ok'])
        self.mox.ReplayAll()

        self.assertEquals(
            0, cli.main(['host', 'find', '--name=%bz']))

    def test_create_object(self):
        self._connect()
        self.conn.create('host', {'name': 'utz', 'ip': '2.3.4.5'})
        self.mox.ReplayAll()

        self.assertEquals(
            0, cli.main(
                ['host', 'create', '--name=utz', '--ip=2.3.4.5']))

    def test_create_object_with_relation(self):
        self._connect()
        self.conn.create('host', {'name': 'utz', 'ip': '2.3.4.5',
                                  'roles': ['role1', 'role2']})
        self.mox.ReplayAll()

        self.assertEquals(
            0, cli.main(
                ['host', 'create', '--name=utz', '--ip=2.3.4.5',
                 '--roles=role1,role2']))

    def test_delete_object(self):
        self._connect()
        self.conn.delete('host', 'utz')
        self.mox.ReplayAll()

        self.assertEquals(
            0, cli.main(
                ['host', 'del', 'utz']))

    def test_update_object(self):
        self._connect()
        self.conn.get('host', 'utz').AndReturn(
            {'name': 'utz', 'ip': '1.2.3.4', 'ip6': None, 'roles': []})
        self.conn.update('host', 'utz', {'ip': '2.3.4.5'})
        self.mox.ReplayAll()

        self.assertEquals(
            0, cli.main(
                ['host', 'mod', 'utz', '--ip=2.3.4.5']))

    def test_update_object_clear_attr(self):
        self._connect()
        self.conn.get('host', 'utz').AndReturn(
            {'name': 'utz', 'ip': '1.2.3.4', 'ip6': None, 'roles': []})
        self.conn.update('host', 'utz', {'ip': None})
        self.mox.ReplayAll()

        self.assertEquals(
            0, cli.main(
                ['host', 'mod', 'utz', '--ip=']))

    def test_update_object_add_relation(self):
        self._connect()
        self.conn.get('host', 'utz').AndReturn(
            {'name': 'utz', 'ip': '1.2.3.4', 'ip6': None, 'roles': ['role1']})
        self.conn.update('host', 'utz', {'ip': '2.3.4.5',
                                         'roles': ['role1', 'role2']})
        self.mox.ReplayAll()

        self.assertEquals(
            0, cli.main(
                ['host', 'mod', 'utz',
                 '--ip=2.3.4.5',
                 '--add', '--role=role2']))

    def test_update_object_delete_relation(self):
        self._connect()
        self.conn.get('host', 'utz').AndReturn(
            {'name': 'utz', 'ip': '1.2.3.4', 'ip6': None, 'roles': ['role1']})
        self.conn.update('host', 'utz', {'ip': '2.3.4.5',
                                         'roles': []})
        self.mox.ReplayAll()

        self.assertEquals(
            0, cli.main(
                ['host', 'mod', 'utz',
                 '--ip=2.3.4.5',
                 '--delete', '--role=role1']))

    def test_update_object_conflicting_relation_flags(self):
        self._connect()
        self.mox.ReplayAll()

        self.assertEquals(
            1, cli.main(
                ['host', 'mod', 'utz',
                 '--add', '--delete', '--role=role2']))

    def test_update_object_bad_relation_flags(self):
        self._connect()
        self.mox.ReplayAll()

        self.assertEquals(
            1, cli.main(
                ['host', 'mod', 'utz',
                 '--add', '--role=']))

    def test_update_object_relation_flag_without_add_or_delete(self):
        self._connect()
        self.mox.ReplayAll()

        self.assertEquals(
            1, cli.main(
                ['host', 'mod', 'utz',
                 '--role=role1']))

    def test_audit(self):
        self._connect()
        self.conn.get_audit({'entity': 'host', 'object': 'obz'}).AndReturn(
            [{'entity': 'host', 'object': 'obz',
              'user': 'admin', 'op': 'create',
              'stamp': '2006-01-01T00:00:00'}])
        self.mox.ReplayAll()

        self.assertEquals(
            0, cli.main(
                ['audit', '--entity=host', '--object=obz']))
            
