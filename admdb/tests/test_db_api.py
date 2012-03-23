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
        self.ctx = acl.AuthContext('admin', ['admins'])

    def test_get(self):
        result = self.api.get('host', 'obz', self.ctx)
        self.assertTrue(result is not None)
        self.assertEquals('obz', result.name)

    def test_get_nonexisting_obj_returns_none(self):
        self.assertRaises(exceptions.NotFound,
                          self.api.get,
                          'host', 'whrarggh', self.ctx)

    def test_get_nonexisting_entity_raises_notfound(self):
        self.assertRaises(exceptions.NotFound,
                          self.api.get,
                          'whrarggh', 'obz', self.ctx)

    def test_find(self):
        result = self.api.find('host', {'name': 'obz'}, self.ctx)
        self.assertTrue(result is not None)
        self.assertEquals(1, len(result))
        self.assertEquals('obz', result[0].name)

    def test_find_relation(self):
        result = self.api.find('host', {'roles': 'role1'}, self.ctx)
        self.assertTrue(result is not None)
        self.assertEquals(1, len(result))
        self.assertEquals('obz', result[0].name)

    def test_find_relation_as_list(self):
        result = self.api.find('host', {'roles': ['role1']}, self.ctx)
        self.assertTrue(result is not None)
        self.assertEquals(1, len(result))
        self.assertEquals('obz', result[0].name)

    def test_find_nonexisting_entity_raises_notfound(self):
        self.assertRaises(exceptions.NotFound,
                          self.api.find,
                          'noent', {'name': 'blah'}, self.ctx)

    def test_find_validation_error(self):
        self.assertRaises(exceptions.ValidationError,
                          self.api.find,
                          'host', {'ip': '299.0.0.1'},
                          self.ctx)

    def test_create_simple(self):
        host_data = {'name': 'utz', 'ip': '2.3.4.5'}
        result = self.api.create('host', host_data, self.ctx)
        self.assertTrue(result > 0)

    def test_create_with_relations(self):
        host_data = {'name': 'utz', 'ip': '2.3.4.5',
                     'roles': ['role1']}
        result = self.api.create('host', host_data, self.ctx)
        self.assertTrue(result > 0)

    def test_create_unknown_entity(self):
        self.assertRaises(exceptions.NotFound,
                          self.api.create,
                          'noent', {'something': 'else'}, self.ctx)

    def test_create_bad_acl(self):
        auth_ctx = acl.AuthContext('bad_user')
        host_data = {'name': 'utz', 'ip': '2.3.4.5'}
        self.assertRaises(exceptions.AclError,
                          self.api.create,
                          'host', host_data, auth_ctx)

    def test_create_validation_error(self):
        self.assertRaises(exceptions.ValidationError,
                          self.api.create,
                          'host', {'name': 'host2', 'ip': '299.0.0.1'},
                          self.ctx)

    def test_update_ok(self):
        result = self.api.update('host', 'obz', {'ip': '2.3.4.5'}, self.ctx)
        self.assertTrue(result)

        self.assertEquals('2.3.4.5',
                          self.api.get('host', 'obz', self.ctx).ip)

    def test_update_modify_relation(self):
        self.assertTrue(
            self.api.update('host', 'obz', {'roles': ['role2']}, self.ctx))
        new_roles = set(x.name
                        for x in self.api.get('host', 'obz', self.ctx).roles)
        self.assertEquals(set(['role2']), new_roles)

    def test_update_clear_relation(self):
        self.assertTrue(
            self.api.update('host', 'obz', {'roles': []}, self.ctx))
        self.assertEquals(0, len(self.api.get('host', 'obz', self.ctx).roles))

        self.assertTrue(
            self.api.update('host', 'obz', {'roles': None}, self.ctx))
        self.assertEquals(0, len(self.api.get('host', 'obz', self.ctx).roles))

    def test_update_modify_relation_error(self):
        self.assertRaises(exceptions.RelationError,
                          self.api.update,
                          'host', 'obz', {'roles': ['blah']}, self.ctx)

    def test_update_validation_error(self):
        self.assertRaises(exceptions.ValidationError,
                          self.api.update,
                          'host', 'obz', {'ip': '299.0.0.1'}, self.ctx)

    def test_update_validation_error_on_relation(self):
        self.assertRaises(exceptions.ValidationError,
                          self.api.update,
                          'host', 'obz', {'roles': 42}, self.ctx)

    def test_update_validation_error_in_deserialization(self):
        self.assertRaises(exceptions.ValidationError,
                          self.api.update,
                          'user', 'testuser',
                          {'last_login': 'not_a_valid_iso_timestamp'}, 
                          self.ctx)

    def test_update_unknown_entity_error(self):
        self.assertRaises(exceptions.NotFound,
                          self.api.update,
                          'noent', 'obz', {'ip': '299.0.0.1'}, self.ctx)

    def test_update_unknown_object_error(self):
        self.assertRaises(exceptions.NotFound,
                          self.api.update,
                          'host', 'notfound', {'ip': '299.0.0.1'}, self.ctx)

    def test_update_bad_acl(self):
        auth_ctx = acl.AuthContext('bad_user')
        self.assertRaises(exceptions.AclError,
                          self.api.update,
                          'host', 'obz', {'ip': '2.3.4.5'}, auth_ctx)

    def test_update_extra_fields(self):
        self.assertRaises(exceptions.ValidationError,
                          self.api.update,
                          'host', 'obz',
                          {'ip': '1.2.3.4', 'extra': 'read all about it'},
                          self.ctx)

    def test_delete(self):
        self.assertTrue(
            self.api.delete('host', 'obz', self.ctx))

        self.assertRaises(exceptions.NotFound,
                          self.api.get,
                          'host', 'obz',  self.ctx)

    def test_delete_twice(self):
        self.assertTrue(
            self.api.delete('host', 'obz', self.ctx))
        self.assertTrue(
            self.api.delete('host', 'obz', self.ctx))

    def test_delete_unknown_entity(self):
        self.assertRaises(exceptions.NotFound,
                          self.api.delete,
                          'noent', 'obz', self.ctx)

    def test_delete_unknown_object(self):
        self.assertTrue(
            self.api.delete('host', 'notfound',  self.ctx))

    def test_delete_bad_acl(self):
        auth_ctx = acl.AuthContext('bad_user')
        self.assertRaises(exceptions.AclError,
                          self.api.delete,
                          'host', 'obz', auth_ctx)

    def test_self_acl(self):
        testuser = self.db.get_by_name('user', 'testuser')
        print 'ID:', testuser.id
        auth_ctx = acl.AuthContext(testuser.name)
        auth_ctx.set_self(testuser)

        r = self.api.create('ssh_key', {'name': 'testuser@host2',
                                        'key': 'MORE KEY DATA'}, auth_ctx)

        user_data = {'ssh_keys': ['testuser@host2']}
        r = self.api.update('user', 'testuser', user_data, auth_ctx)
        self.assertTrue(r)
