import crypt
import mox
import os
import sys
from configdb import exceptions
from configdb.db import acl
from configdb.tests import *
from configdb.server import auth


class UserObj(object):

    def __init__(self, user, password=None):
        self.user = user
        if password:
            self.password = crypt.crypt(password, 'az')


class ApiObj(object):

    def __init__(self, db):
        self.db = db


class UserAuthTest(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        TestBase.tearDown(self)

    def test_auth_user_fn_ok(self):
        db = self.mox.CreateMockAnything()
        db.get_by_name('user', 'admin').AndReturn(UserObj('admin', 'pw'))
        self.mox.ReplayAll()

        fn = auth.user_auth_fn()
        self.assertEquals(
            'admin',
            fn(ApiObj(db), {'username': 'admin',
                            'password': 'pw'}))

    def test_auth_user_fn_wrong_password(self):
        db = self.mox.CreateMockAnything()
        db.get_by_name('user', 'admin').AndReturn(UserObj('admin', 'pw'))
        self.mox.ReplayAll()

        fn = auth.user_auth_fn()
        self.assertEquals(
            None,
            fn(ApiObj(db), {'username': 'admin',
                            'password': 'badpass'}))

    def test_auth_user_fn_missing_data(self):
        db = self.mox.CreateMockAnything()
        self.mox.ReplayAll()

        fn = auth.user_auth_fn()
        self.assertEquals(
            None,
            fn(ApiObj(db), {'username': 'admin'}))

    def test_auth_user_fn_nonexisting_user(self):
        db = self.mox.CreateMockAnything()
        db.get_by_name('user', 'admin').AndReturn(None)
        self.mox.ReplayAll()

        fn = auth.user_auth_fn()
        self.assertEquals(
            None,
            fn(ApiObj(db), {'username': 'admin',
                            'password': 'pw'}))


    def test_auth_user_context_ok(self):
        db = self.mox.CreateMockAnything()
        user_obj = UserObj('admin', 'pw')
        db.get_by_name('user', 'admin').AndReturn(user_obj)
        self.mox.ReplayAll()

        fn = auth.user_auth_context_fn()
        ctx = fn(ApiObj(db), 'admin')
        self.assertTrue(isinstance(ctx, acl.AuthContext))
        self.assertEquals(user_obj, ctx.get_self())

