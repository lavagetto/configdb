import json
import mox
import urllib2
from admdb import exceptions
from admdb.tests import *
from admdb.client import connection
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
        self.mox = mox.Mox()
        self.opener = self.mox.CreateMockAnything()
        self.mox.StubOutWithMock(urllib2, 'build_opener')
        urllib2.build_opener().AndReturn(self.opener)

    def tearDown(self):
        self.mox.VerifyAll()
        self.mox.UnsetStubs()

    def _mock_request(self, url, req_data, resp_data):
        self.opener.open(
            RequestComparator(TEST_URL + url, req_data)
            ).AndReturn(FakeResponse(resp_data))

    def test_get(self):
        obj = {'name': 'obz',
               'ip': '1.2.3.4',
               'ip6': None,
               'roles': ['role1', 'role2']}
        self._mock_request('/get/host/obz', None, obj)

        self.mox.ReplayAll()

        conn = connection.Connection(TEST_URL, self.get_schema())
        self.assertEquals(obj, conn.get('host', 'obz'))

    def test_find(self):
        obj = {'name': 'obz',
               'ip': '1.2.3.4',
               'ip6': None,
               'roles': ['role1', 'role2']}
        self._mock_request('/find/host', {'roles': ['role1']}, [obj])

        self.mox.ReplayAll()

        conn = connection.Connection(TEST_URL, self.get_schema())
        self.assertEquals([obj], conn.find('host', {'roles': ['role1']}))

    def test_create(self):
        self._mock_request('/create/user',
                           {'name': 'testuser',
                            'last_login': '2006-01-01T00:00:00',
                            'enabled': False},
                           42)
        self.mox.ReplayAll()

        conn = connection.Connection(TEST_URL, self.get_schema())
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

        conn = connection.Connection(TEST_URL, self.get_schema())
        data = {'last_login': datetime(2006, 1, 1),
                'enabled': False}
        self.assertEquals(True, conn.update('user', 'testuser', data))

    def test_delete(self):
        self._mock_request('/delete/host/obz', None, True)

        self.mox.ReplayAll()

        conn = connection.Connection(TEST_URL, self.get_schema())
        self.assertEquals(True, conn.delete('host', 'obz'))

    def test_app_error(self):
        self.opener.open(
            mox.IsA(urllib2.Request)).AndReturn(ErrorResponse())
        self.mox.ReplayAll()

        conn = connection.Connection(TEST_URL, self.get_schema())
        self.assertRaises(exceptions.RpcError,
                          conn.get, 'host', 'blah')

    def test_transport_error(self):
        self.opener.open(
            mox.IsA(urllib2.Request)).AndRaise(urllib2.URLError('err'))
        self.mox.ReplayAll()

        conn = connection.Connection(TEST_URL, self.get_schema())
        self.assertRaises(exceptions.RpcError,
                          conn.get, 'host', 'blah')
