import json
import os
from werkzeug.exceptions import Forbidden
from datetime import datetime
from configdb.db import acl
from configdb.tests import *


@wsgiapp.api_app.route('/raise_exception')
@wsgiapp.authenticate
@wsgiapp.json_request
@wsgiapp.json_response
def raise_exception():
    raise Exception('test exception')        


class WsgiTest(WsgiTestBase):

    def setUp(self):
        WsgiTestBase.setUp(self)

        app = self.create_app_with_schema('schema-simple.json')
        self.wsgiapp = app
        self.app = app.test_client()

        db = app.api.db
        with db.session() as s:
            a = db.create('host', {'ip': '1.2.3.4', 'name': 'obz', 'ghz': 4.5}, s)
            r = db.create('role', {'name': 'role1'}, s)
            u = db.create('user', {'name': 'user1',
                                   'last_login': datetime(2006, 1, 1)}, s)
            a.roles.append(r)

            r2 = db.create('role', {'name': u'a/i black ops'}, s)
            db.add_audit('host', 'obz', 'create', {'ip': '1.2.3.4',
                                                   'name': 'obz'},
                         acl.AuthContext('admin'), s)

    def test_config_without_schema_file_raises_exception(self):
        self.assertRaises(Exception,
                          wsgiapp.make_app, {})

    def test_unauthenticated_request(self):
        rv = self.app.get('/get/host/obz')
        self.assertEquals(403, rv.status_code)

    def test_auth_bypass(self):
        self.wsgiapp.config['AUTH_BYPASS'] = True
        rv = self.app.get('/get/host/obz')
        self.assertEquals(200, rv.status_code)

    def test_wrap_exceptions(self):
        self._login()
        rv = self.app.get('/raise_exception')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertEquals(
            {'ok': False, 'error': 'test exception'},
            data)

    def test_get_host(self):
        self._login()
        result = self._parse(self.app.get('/get/host/obz'))
        self.assertEquals({'name': 'obz',
                           'ip': '1.2.3.4',
                           'ip6': None,
                           'ghz': 4.5,
                           'roles': ['role1']},
                          result)

    def test_get_user(self):
        # same as above, with more data types
        self._login()
        result = self._parse(self.app.get('/get/user/user1'))
        self.assertEquals({'name': 'user1',
                           'enabled': True,
                           'password': None,
                           'last_login': '2006-01-01T00:00:00',
                           'ssh_keys': []},
                          result)

    def test_get_entity_with_slashes(self):
        self._login()
        rv = self.app.get('/get/role/a%2Fi%20black%20ops')
        self.assertEquals(200, rv.status_code)

    def test_create(self):
        self._login()
        rv = self.app.post('/create/user',
                           data=json.dumps({'name': 'testuser'}),
                           content_type='application/json')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertEquals({'ok': True, 'result': True}, data)

    def test_create_integrity_failure(self):
        self._login()
        rv = self.app.post('/create/user',
                           data=json.dumps({'name': 'user1'}),
                           content_type='application/json')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertFalse(data['ok'])

    def test_session_is_reusable_after_integrity_failure(self):
        # If a database call fails, the SQLAlchemy session needs
        # to be cleared up. Ensure that this is the case.
        self._login()
        rv = self.app.post('/create/user',
                           data=json.dumps({'name': 'user1'}),
                           content_type='application/json')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertFalse(data['ok'])

        rv = self.app.get('/get/user/user1')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertTrue(data['ok'])

    def test_require_json_content_type_on_post(self):
        self._login()
        rv = self.app.post('/create/user',
                           data=json.dumps({'name': 'testuser'}))
        self.assertEquals(400, rv.status_code)

    def test_json_decoding_error(self):
        self._login()
        rv = self.app.post('/create/user',
                           data='definitely { not json;',
                           content_type='application/json')
        self.assertEquals(400, rv.status_code)

    def test_update(self):
        self._login()
        rv = self.app.post('/update/host/obz',
                           data=json.dumps({'name': 'obz',
                                            'ip': '2.3.4.5'}),
                           content_type='application/json')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertEquals({'ok': True, 'result': True}, data)

    def test_update_entity_with_slashes(self):
        self._login()
        rv = self.app.post('/update/role/a%2Fi%20black%20ops',
                           data=json.dumps({'name': 'a/i'}),
                           content_type='application/json')
        self.assertEquals(200, rv.status_code)

    def test_find(self):
        self._login()
        query = {'name': {'type': 'eq', 'value': 'obz'},
                 'roles': {'type': 'eq', 'value': 'role1'}}
        rv = self.app.post('/find/host',
                           data=json.dumps(query),
                           content_type='application/json')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertTrue(data.get('ok'))
        result = data['result']
        self.assertEquals(1, len(result))
        self.assertEquals('obz', result[0]['name'])


    def test_delete(self):
        self._login()
        rv = self.app.get('/delete/host/obz')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertEquals({'ok': True, 'result': True}, data)

    def test_delete_entity_with_slashes(self):
        self._login()
        rv = self.app.get('/delete/role/a%2Fi')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertEquals({'ok': True, 'result': True}, data)

    def test_get_audit(self):
        self._login()
        result = self._parse(
            self.app.post('/audit',
                          data=json.dumps({'entity': 'host',
                                           'object': 'obz'}),
                          content_type='application/json'))
        self.assertTrue(isinstance(result, list))
        self.assertEquals(1, len(result))
        self.assertEquals('host', result[0]['entity'])
        self.assertEquals('create', result[0]['op'])
        self.assertEquals('admin', result[0]['user'])

    def test_get_schema(self):
        self._login()
        rv = self.app.get('/schema')
        self.assertEquals(200, rv.status_code)
        #self.assertEquals(TEST_SCHEMA, rv.data)

    def test_login(self):
        rv = self.app.post('/login',
                           data=json.dumps({'username': 'admin',
                                            'password': 'admin'}),
                           content_type='application/json')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertEquals({'ok': True, 'result': True}, data)

    def test_login_error(self):
        rv = self.app.post('/login',
                           data=json.dumps({'username': 'admin',
                                            'password': 'wrong'}),
                           content_type='application/json')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertEquals(
            {'ok': False, 'error': 'Authentication error'}, data)

