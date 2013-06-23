import json
import os
import unittest
import shutil
import tempfile
from configdb.db import acl
from configdb.db import schema
from configdb.server import wsgiapp
from nose.plugins.attrib import attr


class TestBase(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._tmpdir)

    def get_schema(self):
        schema_file = os.path.join(
            os.path.dirname(__file__), 'schema-simple.json')
        with open(schema_file, 'r') as fd:
            self._schema = schema.Schema(fd.read())
        return self._schema


def auth_fn(api, data):
    username = data.get('username')
    password = data.get('password')
    if username == 'admin' and password == 'admin':
        return username

def auth_context_fn(api, auth_token):
    return acl.AuthContext(auth_token)


class WsgiTestBase(TestBase):

    def create_app(self, **kwargs):
        config = {
            'DEBUG': True,
            'TESTING': True,
            'SECRET_KEY': 'test key',
            'AUTH_FN': auth_fn,
            'AUTH_CONTEXT_FN': auth_context_fn,
        }
        config.update(kwargs)
        return wsgiapp.make_app(config)

    def create_app_with_schema(self, schema_file, **kwargs):
        schema_file = os.path.join(
            os.path.dirname(__file__), schema_file)
        return self.create_app(SCHEMA_FILE=schema_file, **kwargs)

    def _login(self):
        rv = self.app.post('/login',
                           data=json.dumps({'username': 'admin',
                                            'password': 'admin'}),
                           content_type='application/json')
        self.assertEquals(200, rv.status_code)

    def _parse(self, rv):
        self.assertEquals(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertTrue(data['ok'])
        return data['result']
