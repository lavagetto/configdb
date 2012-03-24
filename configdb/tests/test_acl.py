from configdb.tests import *
from configdb.db import acl
from configdb import exceptions


class AclParseRulesTest(TestBase):

    def test_parse_self(self):
        r = acl._parse_acl_rules('@self')
        self.assertEquals(1, len(r))
        self.assertTrue(isinstance(r[0], acl.RuleMatchSelf))

    def test_parse_any(self):
        r = acl._parse_acl_rules('*')
        self.assertEquals(1, len(r))
        self.assertTrue(isinstance(r[0], acl.RuleAny))

    def test_parse_none(self):
        r = acl._parse_acl_rules('!')
        self.assertEquals(1, len(r))
        self.assertTrue(isinstance(r[0], acl.RuleNone))

    def test_parse_user(self):
        r = acl._parse_acl_rules('user/admin')
        self.assertEquals(1, len(r))
        self.assertTrue(isinstance(r[0], acl.RuleMatchUser))
        self.assertEquals('admin', r[0].ok_user)

    def test_parse_group(self):
        r = acl._parse_acl_rules('group/admins')
        self.assertEquals(1, len(r))
        self.assertTrue(isinstance(r[0], acl.RuleMatchGroup))
        self.assertEquals('admins', r[0].ok_group)

    def test_parse_user_by_relation(self):
        r = acl._parse_acl_rules('@owners')
        self.assertEquals(1, len(r))
        self.assertTrue(isinstance(r[0], acl.RuleMatchUserByRelation))
        self.assertEquals('owners', r[0].rel_attr)

    def test_parse_error(self):
        self.assertRaises(exceptions.SchemaError,
                          acl._parse_acl_rules,
                          'blah')

    def test_parse_multiple_rules(self):
        r = acl._parse_acl_rules('user/admin, *,group/blah')
        self.assertEquals(3, len(r))


class AclParseTest(TestBase):

    def test_parse_acl(self):
        spec = {'r': 'user/admin, group/admins',
                'w': '@self'}
        r = acl.parse_acl(spec)
        self.assertEquals(set(['r', 'w']), set(r.keys()))

    def test_error_extra_attrs(self):
        spec = {'r': '@self',
                'blah': '42'}
        self.assertRaises(exceptions.SchemaError,
                          acl.parse_acl,
                          spec)


class StubObj(acl.AclMixin):

    def __init__(self, acl_spec):
        self.set_acl(acl_spec)


class StubDbObj(object):

    def __init__(self, objid, parents=None):
        self.id = objid
        self.parents = parents


class AclCheckTest(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.ctx = acl.AuthContext('admin', ['admins'])
        self.bad_ctx = acl.AuthContext('bad_user')
        self.dbobj = StubDbObj(42)

    def test_check_default(self):
        obj = StubObj({})
        self.assertFalse(
            obj.acl_check(self.ctx, 'r', self.dbobj))

    def test_check_any_ok(self):
        obj = StubObj({'r': '*'})
        self.assertTrue(
            obj.acl_check(self.ctx, 'r', self.dbobj))

    def test_check_user_ok(self):
        obj = StubObj({'r': '*', 'w': 'user/admin'})
        self.assertTrue(
            obj.acl_check(self.ctx, 'w', self.dbobj))

    def test_check_user_not_ok(self):
        obj = StubObj({'r': '*', 'w': 'user/admin'})
        self.assertFalse(
            obj.acl_check(self.bad_ctx, 'w', self.dbobj))

    def test_check_none_not_ok(self):
        obj = StubObj({'r': '!'})
        self.assertFalse(
            obj.acl_check(self.ctx, 'r', self.dbobj))

    def test_check_group_ok(self):
        obj = StubObj({'r': '*', 'w': 'group/admins'})
        self.assertTrue(
            obj.acl_check(self.ctx, 'w', self.dbobj))

    def test_check_group_not_ok(self):
        obj = StubObj({'r': '*', 'w': 'group/admins'})
        self.assertFalse(
            obj.acl_check(self.bad_ctx, 'w', self.dbobj))

    def test_check_self(self):
        obj = StubObj({'w': '@self'})
        self.ctx.set_self(self.dbobj)
        self.assertTrue(
            obj.acl_check(self.ctx, 'w', self.dbobj))

        self.ctx.set_self(StubDbObj('z'))
        self.assertFalse(
            obj.acl_check(self.ctx, 'w', self.dbobj))

    def test_check_multiple_rules(self):
        obj = StubObj({'w': 'user/admin,@self'})
        self.assertTrue(
            obj.acl_check(self.ctx, 'w', self.dbobj))

        self.bad_ctx.set_self(self.dbobj)
        self.assertTrue(
            obj.acl_check(self.bad_ctx, 'w', self.dbobj))
        self.assertFalse(
            obj.acl_check(self.bad_ctx, 'w', StubDbObj('z')))

    def test_check_user_by_relation(self):
        obj = StubObj({'w': '@parents'})
        self_dbobj = StubDbObj('self')
        dbobj = StubDbObj('cur', [self_dbobj])
        self.ctx.set_self(self_dbobj)

        self.assertTrue(
            obj.acl_check(self.ctx, 'w', dbobj))

        self.assertFalse(
            obj.acl_check(self.ctx, 'w', StubDbObj('other')))
            
