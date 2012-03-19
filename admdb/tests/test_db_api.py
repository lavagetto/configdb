from admdb import exceptions
from admdb.tests import *
from admdb.db import db_api
from admdb.db import acl
from admdb.db.interface import sa_interface


class DbApiTest(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.schema = self.get_schema()
        self.db = sa_interface.SqlAlchemyDb('sqlite:///:memory:',
                                            self.schema)

        with self.db.session() as s:
            a = self.db.create('host', {'ip': '1.2.3.4', 'name': 'obz'}, s)
            r = self.db.create('role', {'name': 'role1'}, s)
            a.roles.append(r)
            r2 = self.db.create('role', {'name': 'role2'}, s)
            u = self.db.create('user', {'name': 'testuser'}, s)
            sk = self.db.create('ssh_key', {'name': 'testuser@host',
                                            'key': 'KEY_DATA'}, s)
            u.ssh_keys.append(sk)

        self.api = db_api.AdmDbApi(self.schema, self.db)

    def test_get(self):
        auth_ctx = acl.AuthContext('admin', ['admins'])
        result = self.api.get('host', 'obz', auth_ctx)
        self.assertTrue(result is not None)
        self.assertEquals('obz', result.name)

    def test_get_nonexisting_obj_returns_none(self):
        auth_ctx = acl.AuthContext('admin', ['admins'])
        self.assertRaises(exceptions.NotFound,
                          self.api.get,
                          'host', 'whrarggh', auth_ctx)

    def test_get_nonexisting_entity_raises_notfound(self):
        auth_ctx = acl.AuthContext('admin', ['admins'])
        self.assertRaises(exceptions.NotFound,
                          self.api.get,
                          'whrarggh', 'obz', auth_ctx)

    def test_find(self):
        auth_ctx = acl.AuthContext('admin', ['admins'])
        result = self.api.find('host', {'name': 'obz'}, auth_ctx)
        self.assertTrue(result is not None)
        self.assertEquals(1, len(result))
        self.assertEquals('obz', result[0].name)

    def test_create_simple(self):
        auth_ctx = acl.AuthContext('admin', ['admins'])
        host_data = {'name': 'utz', 'ip': '2.3.4.5'}
        result = self.api.create('host', host_data, auth_ctx)
        self.assertTrue(result > 0)

    def test_create_with_relations(self):
        auth_ctx = acl.AuthContext('admin', ['admins'])
        host_data = {'name': 'utz', 'ip': '2.3.4.5',
                     'roles': ['role1']}
        result = self.api.create('host', host_data, auth_ctx)
        self.assertTrue(result > 0)

    def test_update_ok(self):
        auth_ctx = acl.AuthContext('admin', ['admins'])
        result = self.api.update('host', 'obz', {'ip': '2.3.4.5'}, auth_ctx)
        self.assertTrue(result)

        self.assertEquals('2.3.4.5',
                          self.api.get('host', 'obz', auth_ctx).ip)

    def test_update_modify_relation(self):
        auth_ctx = acl.AuthContext('admin', ['admins'])
        result = self.api.update('host', 'obz', {'roles': ['role2']}, auth_ctx)
        self.assertTrue(result)

        new_roles = set(x.name
                        for x in self.api.get('host', 'obz', auth_ctx).roles)
        self.assertEquals(set(['role2']), new_roles)

    def test_update_clear_relation(self):
        auth_ctx = acl.AuthContext('admin', ['admins'])
        result = self.api.update('host', 'obz', {'roles': []}, auth_ctx)
        self.assertTrue(result)
        self.assertEquals(0, len(self.api.get('host', 'obz', auth_ctx).roles))

        auth_ctx = acl.AuthContext('admin', ['admins'])
        result = self.api.update('host', 'obz', {'roles': None}, auth_ctx)
        self.assertTrue(result)
        self.assertEquals(0, len(self.api.get('host', 'obz', auth_ctx).roles))

    def test_update_modify_relation_error(self):
        auth_ctx = acl.AuthContext('admin', ['admins'])
        self.assertRaises(exceptions.RelationError,
                          self.api.update,
                          'host', 'obz', {'roles': ['blah']}, auth_ctx)

    def test_delete(self):
        auth_ctx = acl.AuthContext('admin', ['admins'])
        result = self.api.delete('host', 'obz', auth_ctx)
        self.assertTrue(result)

        # double-check
        self.assertRaises(exceptions.NotFound,
                          self.api.get,
                          'host', 'obz',  auth_ctx)

        # a second time should still return true
        result = self.api.delete('host', 'obz', auth_ctx)
        self.assertTrue(result)

    def test_update_bad_acl(self):
        auth_ctx = acl.AuthContext('bad_user')
        self.assertRaises(exceptions.AclError,
                          self.api.update,
                          'host', 'obz', {'ip': ['1.2.3.4']}, auth_ctx)

    def test_create_bad_acl(self):
        auth_ctx = acl.AuthContext('bad_user')
        host_data = {'name': 'utz', 'ip': '2.3.4.5'}
        self.assertRaises(exceptions.AclError,
                          self.api.create,
                          'host', host_data, auth_ctx)

    def test_delete_bad_acl(self):
        auth_ctx = acl.AuthContext('bad_user')
        self.assertRaises(exceptions.AclError,
                          self.api.delete,
                          'host', 'obz', auth_ctx)

    def test_self_acl(self):
        testuser = self.db.get_by_name('user', 'testuser')
        auth_ctx = acl.AuthContext(testuser.name)
        auth_ctx.set_self(testuser)

        r = self.api.create('ssh_key', {'name': 'testuser@host2',
                                        'key': 'MORE KEY DATA'}, auth_ctx)

        user_data = {'ssh_keys': ['testuser@host2']}
        r = self.api.update('user', 'testuser', user_data, auth_ctx)
        self.assertTrue(r)
