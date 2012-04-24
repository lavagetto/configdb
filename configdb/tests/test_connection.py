import cookielib
import getpass
import json
import mox
import os
import sys
import urllib2
from configdb import exceptions
from configdb.tests import *
from configdb.client import connection
from datetime import datetime

TEST_URL = 'http://url'


class FakeResponse(object):

    def __init__(self, data):
        self.data = data

    def read(self):
        return json.dumps({'ok': True, 'result': self.data})


class ErrorResponse(object):

    def read(self):
        return json.dumps({'ok': False, 'error': 'errmsg'})


class RequestComparator(mox.Comparator):

    def __init__(self, url, data):
        self._url = url
        self._data = json.dumps(data) if data else None

    def equals(self, rhs):
        print 'REQUEST:', rhs.get_full_url(), rhs.get_data()
        return (isinstance(rhs, urllib2.Request)
                and (self._url == rhs.get_full_url())
                and (self._data == rhs.get_data()))


class ConnectionTest(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.mox = mox.Mox()
        self.opener = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(urllib2, 'build_opener')
        urllib2.build_opener(mox.IsA(urllib2.HTTPCookieProcessor),
                             mox.IsA(connection.GzipProcessor)
                             ).AndReturn(self.opener)

    def tearDown(self):
        self.mox.VerifyAll()
        self.mox.UnsetStubs()
        TestBase.tearDown(self)

    def _connect(self, **kw):
        return connection.Connection(TEST_URL, self.get_schema(), **kw)

    def _mock_request(self, url, req_data, resp_data):
        self.opener.open(
            RequestComparator(TEST_URL + url, req_data)
            ).AndReturn(FakeResponse(resp_data))

    def _mock_login(self):
        self.opener.open(
            RequestComparator(TEST_URL + '/get/host/obz', None)
            ).AndRaise(urllib2.HTTPError('/get/host/obz', 403,
                                         'Forbidden', {}, None))
        self.opener.open(
            RequestComparator(TEST_URL + '/login',
                              {'username': 'admin',
                               'password': 'pass'})
            ).AndReturn(FakeResponse(True))
        self.opener.open(
            RequestComparator(TEST_URL + '/get/host/obz', None)
            ).AndReturn(FakeResponse({'name': 'obz'}))

    def test_redirect_to_login(self):
        self._mock_login()
        self.mox.ReplayAll()

        conn = self._connect(username='admin', password='pass')
        self.assertEquals({'name': 'obz'}, conn.get('host', 'obz'))

    def test_login_opens_auth_file(self):
        auth_file = os.path.join(self._tmpdir, 'cookies')
        open(auth_file, 'w').close()

        jar = self.mox.CreateMock(cookielib.MozillaCookieJar)
        self.mox.StubOutWithMock(cookielib, 'MozillaCookieJar',
                                 use_mock_anything=True)
        cookielib.MozillaCookieJar().AndReturn(jar)
        jar.load(auth_file)

        self.mox.ReplayAll()

        conn = self._connect(username='admin', password='pass',
                             auth_file=auth_file)

    def test_login_creates_auth_file(self):
        self._mock_login()
        self.mox.ReplayAll()

        auth_file = os.path.join(self._tmpdir, 'cookies')
        conn = self._connect(username='admin', password='pass',
                             auth_file=auth_file)
        self.assertEquals({'name': 'obz'}, conn.get('host', 'obz'))
        self.assertTrue(os.path.exists(auth_file))

    def test_login_auth_file_write_failure_is_not_fatal(self):
        self._mock_login()
        self.mox.ReplayAll()

        auth_file = os.path.join(self._tmpdir, 'cookies')
        conn = self._connect(username='admin', password='pass',
                             auth_file=auth_file)

        def _error(self, x):
            raise Exception('error')
        conn._cj.save = _error

        self.assertEquals({'name': 'obz'}, conn.get('host', 'obz'))
        self.assertFalse(os.path.exists(auth_file))

    def test_login_guess_user_and_ask_password(self):
        self.mox.StubOutWithMock(getpass, 'getuser')
        getpass.getuser().InAnyOrder('login').AndReturn('admin')
        self.mox.StubOutWithMock(os, 'isatty')
        os.isatty(sys.stdin).InAnyOrder('login').AndReturn(True)
        self.mox.StubOutWithMock(getpass, 'getpass')
        getpass.getpass().InAnyOrder('login').AndReturn('pass')
        self._mock_login()
        self.mox.ReplayAll()

        conn = self._connect()
        self.assertEquals({'name': 'obz'}, conn.get('host', 'obz'))

    def test_login_fails_if_cant_ask_password(self):
        self.opener.open(
            RequestComparator(TEST_URL + '/get/host/obz', None)
            ).AndRaise(urllib2.HTTPError('/get/host/obz', 403,
                                         'Forbidden', {}, None))
        self.mox.StubOutWithMock(getpass, 'getuser')
        getpass.getuser().InAnyOrder('login').AndReturn('admin')
        self.mox.StubOutWithMock(os, 'isatty')
        os.isatty(sys.stdin).InAnyOrder('login').AndReturn(False)
        self.mox.ReplayAll()

        conn = self._connect()
        self.assertRaises(exceptions.AuthError,
                          conn.get, 'host', 'obz')

    def test_get(self):
        obj = {'name': 'obz',
               'ip': '1.2.3.4',
               'ip6': None,
               'roles': ['role1', 'role2']}
        self._mock_request('/get/host/obz', None, obj)

        self.mox.ReplayAll()

        conn = self._connect()
        self.assertEquals(obj, conn.get('host', 'obz'))

    def test_get_user(self):
        # test deserialization.
        obj = {'name': 'testuser',
               'enabled': True,
               'last_login': '2006-01-01T00:00:00'}
        self._mock_request('/get/user/testuser', None, obj)

        self.mox.ReplayAll()

        conn = self._connect()
        self.assertEquals(
            {'name': 'testuser',
             'enabled': True,
             'last_login': datetime(2006, 1, 1)},
            conn.get('user', 'testuser'))

    def test_get_unknown_entity_raises_notfound(self):
        self.mox.ReplayAll()
        conn = self._connect()
        self.assertRaises(exceptions.NotFound,
                          conn.get, 'noent', 'name')

    def test_find(self):
        obj = {'name': 'obz',
               'ip': '1.2.3.4',
               'ip6': None,
               'roles': ['role1', 'role2']}
        self._mock_request('/find/host', {'roles': ['role1']}, [obj])

        self.mox.ReplayAll()

        conn = self._connect()
        self.assertEquals([obj], conn.find('host', {'roles': ['role1']}))

    def test_create(self):
        # this implicitly tests serialization.
        self._mock_request('/create/user',
                           {'name': 'testuser',
                            'last_login': '2006-01-01T00:00:00',
                            'enabled': False},
                           42)
        self.mox.ReplayAll()

        conn = self._connect()
        data = {'name': 'testuser',
                'last_login': datetime(2006, 1, 1),
                'enabled': False}
        self.assertEquals(42, conn.create('user', data))

    def test_update(self):
        self._mock_request('/update/user/testuser',
                           {'last_login': '2006-01-01T00:00:00',
                            'enabled': False},
                           True)
        self.mox.ReplayAll()

        conn = self._connect()
        data = {'last_login': datetime(2006, 1, 1),
                'enabled': False}
        self.assertEquals(True, conn.update('user', 'testuser', data))

    def test_delete(self):
        self._mock_request('/delete/host/obz', None, True)

        self.mox.ReplayAll()

        conn = self._connect()
        self.assertEquals(True, conn.delete('host', 'obz'))

    def test_get_audit(self):
        self._mock_request('/audit', {'entity': 'host', 'object': 'obz'},
                           [{'entity': 'host', 'object': 'obz',
                             'user': 'admin', 'op': 'create',
                             'stamp': '2006-01-01T00:00:00'}])
        self.mox.ReplayAll()

        conn = self._connect()
        result = conn.get_audit({'entity': 'host', 'object': 'obz'})
        self.assertEquals(1, len(result))

    def test_app_error(self):
        self.opener.open(
            mox.IsA(urllib2.Request)).AndReturn(ErrorResponse())
        self.mox.ReplayAll()

        conn = self._connect()
        self.assertRaises(exceptions.RpcError,
                          conn.get, 'host', 'blah')

    def test_catch_urlerror(self):
        self.opener.open(
            mox.IsA(urllib2.Request)).AndRaise(urllib2.URLError('err'))
        self.mox.ReplayAll()

        conn = self._connect()
        self.assertRaises(exceptions.RpcError,
                          conn.get, 'host', 'blah')

    def test_catch_httperror(self):
        self.opener.open(
            mox.IsA(urllib2.Request)).AndRaise(
            urllib2.HTTPError('/get/host/obz', 500,
                              'Forbidden', {}, None))
        self.mox.ReplayAll()

        conn = self._connect()
        self.assertRaises(exceptions.RpcError,
                          conn.get, 'host', 'obz')
