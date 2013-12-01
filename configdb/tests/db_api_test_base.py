from configdb import exceptions
from configdb.db import db_api
from configdb.db import acl
import time


class DbApiTestBase(object):

    def setUp(self):
        self.db = self.init_db()

        with self.db.session() as s:
            a = self.db.create('host', {'ip': u'1.2.3.4', 'name': u'obz'}, s)
            r = self.db.create('role', {'name': u'role1'}, s)
            a.roles.append(r)
            r = self.db.create('role', {'name': u'role1b'}, s)
            a.roles.append(r)
            r = self.db.create('role', {'name': u'a/i'}, s)
            a.roles.append(r)
            s.add(a)

            r2 = self.db.create('role', {'name': u'role2'}, s)
            u = self.db.create('user', {'name': u'testuser'}, s)
            sk = self.db.create('ssh_key', {'name': u'testuser@host',
                                            'key': u'KEY_DATA'}, s)
            u.ssh_keys.append(sk)

        self.api = db_api.AdmDbApi(self.get_schema(), self.db)
        self.ctx = acl.AuthContext('admin', ['admins'])

    def tearDown(self):
        self.db.close()

    def init_db(self):
        raise NotImplementedError()

    def test_get(self):
        result = self.api.get('host', 'obz', self.ctx)
        self.assertTrue(result is not None)
        self.assertEquals('obz', result.name)

        result = self.api.get('role', 'role1', self.ctx)
        self.assertTrue(result is not None)
        self.assertEquals('role1', result.name)

    def test_get_nonexisting_obj_returns_none(self):
        self.assertRaises(exceptions.NotFound,
                          self.api.get,
                          'host', 'whrarggh', self.ctx)

    def test_get_nonexisting_entity_raises_notfound(self):
        self.assertRaises(exceptions.NotFound,
                          self.api.get,
                          'whrarggh', 'obz', self.ctx)

    def test_get_entity_with_slash(self):
        result = self.api.get('role', 'a/i', self.ctx)
        self.assertTrue(result is not None)
        self.assertEquals('a/i', result.name)

    def test_find(self):
        result = list(
            self.api.find('host',
                          {'name': {'type': 'eq', 'value': 'obz'}},
                          self.ctx))
        self.assertEquals(1, len(result))
        self.assertEquals('obz', result[0].name)

    def test_find_substring(self):
        result = list(
            self.api.find('host',
                          {'name': {'type': 'substring', 'value': 'bz'}},
                          self.ctx))
        self.assertEquals(1, len(result))
        self.assertEquals('obz', result[0].name)

    def test_find_regexp(self):
        result = list(
            self.api.find('host',
                          {'name': {'type': 'regexp', 'pattern': '^o.*$'}},
                          self.ctx))
        self.assertEquals(1, len(result))
        self.assertEquals('obz', result[0].name)

    def test_find_relation(self):
        result = list(
            self.api.find('host',
                          {'roles': {'type': 'eq', 'value': 'role1'}},
                          self.ctx))

        self.assertEquals(1, len(result))
        self.assertEquals('obz', result[0].name)

    def test_find_relation_substring(self):
        result = list(
            self.api.find('host',
                          {'roles': {'type': 'substring', 'value': 'ole1'}},
                          self.ctx))
        self.assertEquals(1, len(result))
        self.assertEquals('obz', result[0].name)

    def test_find_empty_query(self):
        result = list(
            self.api.find('role', {}, self.ctx))
        self.assertEquals(4, len(result))

    def test_find_multiple_criteria(self):
        result = list(
            self.api.find('host',
                          {'roles': {'type': 'substring', 'value': 'ole1'},
                           'name': {'type': 'eq', 'value': 'obz'}},
                          self.ctx))
        self.assertEquals(1, len(result))
        self.assertEquals('obz', result[0].name)

    def test_find_bad_query_spec_unknown_type(self):
        self.assertRaises(exceptions.QueryError,
                          self.api.find,
                          'host', {'roles': {'type': 'unknown'}},
                          self.ctx)

    def test_find_bad_query_spec_missing_value(self):
        self.assertRaises(exceptions.QueryError,
                          self.api.find,
                          'host', {'roles': {'type': 'eq'}},
                          self.ctx)

    def test_find_bad_query_spec_unknown_field(self):
        self.assertRaises(exceptions.ValidationError,
                          self.api.find,
                          'host', {'unknown': {'type': 'eq', 'value': 'yeah'}},
                          self.ctx)

    def test_find_nonexisting_entity_raises_notfound(self):
        self.assertRaises(exceptions.NotFound,
                          self.api.find,
                          'noent', {'name': {'type': 'eq', 'value': 'blah'}},
                          self.ctx)

    def test_find_nonexisting_substring_raises_notfound(self):
        self.assertRaises(exceptions.NotFound,
                          self.api.find,
                          'noent', {'name': '~lah'}, self.ctx)

    def test_create_simple(self):
        host_data = {'name': 'utz', 'ip': '2.3.4.5'}
        self.assertTrue(self.api.create('host', host_data, self.ctx))

    def test_create_adds_audit_log(self):
        if not self.api.db.AUDIT_SUPPORT:
            return
        host_data = {'name': 'utz', 'ip': '2.3.4.5'}
        self.assertTrue(self.api.create('host', host_data, self.ctx))

        result = list(self.api.get_audit({'entity': 'host',
                                          'object': 'utz'}, self.ctx))
        self.assertEquals(1, len(result))

    def test_create_with_relations(self):
        host_data = {'name': 'utz', 'ip': '2.3.4.5',
                     'roles': ['a/i']}
        self.assertTrue(self.api.create('host', host_data, self.ctx))

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

    def test_create_without_name(self):
        self.assertRaises(exceptions.ValidationError,
                          self.api.create,
                          'host', {'ip': '192.168.1.1'},
                          self.ctx)

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

    def test_update_adds_audit_log(self):
        if not self.api.db.AUDIT_SUPPORT:
            return
        old_result = list(self.api.get_audit({'entity': 'host',
                                              'object': 'obz',
                                              'op': 'update'}, self.ctx))

        result = self.api.update('host', 'obz', {'ip': '2.3.4.5'}, self.ctx)
        self.assertTrue(result)

        result = list(self.api.get_audit({'entity': 'host',
                                          'object': 'obz',
                                          'op': 'update'}, self.ctx))
        self.assertEquals(1, len(result) - len(old_result))

    # FIXME: should renaming even work?
    #
    # def test_update_rename(self):
    #     result = self.api.update('host', 'obz', {'name': 'utz'}, self.ctx)
    #     self.assertTrue(result)
    #
    #     self.assertEquals('utz',
    #                       self.api.get('host', 'utz', self.ctx).name)
    #     self.assertRaises(exceptions.NotFound,
    #                       self.api.get, 'host', 'obz', self.ctx)

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

    def test_delete_adds_audit_log(self):
        if not self.api.db.AUDIT_SUPPORT:
            return
        old_result = list(self.api.get_audit({'entity': 'host',
                                              'object': 'obz',
                                              'op': 'delete'}, self.ctx))

        self.assertTrue(
            self.api.delete('host', 'obz', self.ctx))

        result = list(self.api.get_audit({'entity': 'host',
                                          'object': 'obz',
                                          'op': 'delete'}, self.ctx))
        self.assertEquals(1, len(result) - len(old_result))

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
        with self.db.session() as s:
            testuser = self.db.get_by_name('user', 'testuser', s)
        auth_ctx = acl.AuthContext(testuser.name)
        auth_ctx.set_self(testuser)

        r = self.api.create('ssh_key', {'name': 'testuser@host2',
                                        'key': 'MORE KEY DATA'}, auth_ctx)

        user_data = {'ssh_keys': ['testuser@host2']}
        r = self.api.update('user', 'testuser', user_data, auth_ctx)
        self.assertTrue(r)

    def test_get_audit_fails_if_not_supported(self):
        if not self.db.AUDIT_SUPPORT:
            self.assertRaises(NotImplementedError,
                              self.api.get_audit,
                              {'entity': 'user'},
                              self.ctx)

    def test_get_audit_requires_entity_spec(self):
        self.assertRaises(exceptions.NotFound,
                          self.api.get_audit,
                          {'user': 'admin'},
                          self.ctx)

    def test_get_audit_requires_existing_entity(self):
        self.assertRaises(exceptions.NotFound,
                          self.api.get_audit,
                          {'entity': 'noent'},
                          self.ctx)

    def test_get_audit_enforces_acls(self):
        with self.db.session() as s:
            p = self.db.create('private', {'name': 'test'}, s)

        auth_ctx = acl.AuthContext('bad_user')
        self.assertRaises(exceptions.AclError,
                          self.api.get_audit,
                          {'entity': 'private', 'op': 'create'},
                          auth_ctx)

    def test_timestamp_is_updated(self):
        result = self.api.update('host', 'obz', {'ip': '2.3.4.5'}, self.ctx)
        self.assertTrue(result)
        ts1 = self.api.get_timestamp('host', self.ctx).ts
        self.assertTrue(ts1 != 0)
        time.sleep(0.01)
        result = self.api.update('host', 'obz', {'ip': '3.3.3.5'}, self.ctx)
        self.assertTrue(result)
        ts2 = self.api.get_timestamp('host', self.ctx).ts
        self.assertTrue(ts2 > ts1)

    def test_timestamp_for_non_updated_entity(self):
        self.assertRaises(ValueError, self.api.get_timestamp, 'role', self.ctx)
