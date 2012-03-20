import json
import os
from admdb.tests import *
from admdb.server import wsgiapp


class WsgiTest(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.schema_file = os.path.join(self._tmpdir, 'schema.json')
        with open(self.schema_file, 'w') as fd:
            fd.write(TEST_SCHEMA)

        app = wsgiapp.make_app({'SCHEMA_FILE': self.schema_file})
        app.config['TESTING'] = True
        self.app = app.test_client()

        db = app.api.db
        with db.session() as s:
            a = db.create('host', {'ip': '1.2.3.4', 'name': 'obz'}, s)
            r = db.create('role', {'name': 'role1'}, s)
            a.roles.append(r)

    def test_get_host(self):
        rv = self.app.get('/get/host/obz')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertTrue(data['ok'])
        result = data['result']
        self.assertEquals({'name': 'obz',
                           'ip': '1.2.3.4',
                           'ip6': None,
                           'roles': ['role1']},
                          result)

    def test_create(self):
        rv = self.app.post('/create/user',
                           data=json.dumps({'name': 'testuser'}),
                           content_type='application/json')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertEquals({'ok': True, 'result': True}, data)

    def test_update(self):
        rv = self.app.post('/update/host/obz',
                           data=json.dumps({'name': 'obz',
                                            'ip': '2.3.4.5'}),
                           content_type='application/json')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertEquals({'ok': True, 'result': True}, data)

    def test_find(self):
        rv = self.app.post('/find/host',
                           data=json.dumps({'name': 'obz',
                                            'roles': 'role1'}),
                           content_type='application/json')
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertTrue(data.get('ok'))
        result = data['result']
        self.assertEquals(1, len(result))
        self.assertEquals('obz', result[0]['name'])
