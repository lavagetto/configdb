import json
import os
from werkzeug.exceptions import Forbidden
from datetime import datetime
from configdb.db import acl
from configdb.tests import *



class WsgiComplexTest(WsgiTestBase):

    def setUp(self):
        WsgiTestBase.setUp(self)

        app = self.create_app_with_schema('schema-large-noacl.json')
        self.wsgiapp = app
        self.app = app.test_client()

        db = app.api.db
        with db.session() as s:
            u1 = db.create('user', {'name': 'user1',
                                    'uid': 666,
                                    'password': 'pw',
                                    'email': 'user@example.com',
                                    'created_at': datetime(2006, 1, 1),
                                    'updated_at': datetime(2006, 1, 1),
                                }, s)
            u2 = db.create('user', {'name': 'user2',
                                    'uid': 777,
                                    'password': 'pw',
                                    'email': 'user2@example.com',
                                    'created_at': datetime(2006, 2, 2),
                                    'updated_at': datetime(2006, 2, 2),
                                }, s)
            g = db.create('group', {'name': 'group1',
                                    'gid': 2}, s)
            g.owners.append(u1)
            g.users.append(u1)

            r = db.create('role', {'name': 'server'}, s)
            h = db.create('host', {'name': 'hosto',
                                   'server_type': 'vm',
                                   'ip': '1.2.3.4',
                                   'public_id': 1,
                                   'created_at': datetime(2007, 1, 1),
                                   'updated_at': datetime(2007, 1, 1),
                                   'notes': 'a test host',
                                   }, s)
            h.roles.append(r)
            h.sudo_groups.append(g)
            h.login_users.append(u1)

    def test_get_host(self):
        self._login()
        result = self._parse(self.app.get('/get/host/hosto'))
        self.assertEquals('hosto', result['name'])
        self.assertEquals('1.2.3.4', result['ip'])
        self.assertEquals([u'server'], result['roles'])

    def test_host_add_and_remove_role(self):
        self._login()
        
        # Create the new role.
        rv = self._parse(
            self.app.post('/create/role',
                          data=json.dumps({'name': 'role2'}),
                          content_type='application/json'))
        self.assertTrue(rv)

        # Add it to the existing test host. Read/modify/update cycle.
        host = self._parse(self.app.get('/get/host/hosto'))
        host['roles'].append(u'role2')
        rv = self._parse(
            self.app.post('/update/host/hosto',
                          data=json.dumps(host),
                          content_type='application/json'))
        self.assertTrue(rv)

        # Check the reference by using find() on the relation.
        rv = self._parse(
            self.app.post('/find/host',
                          data=json.dumps({'roles': {'type': 'eq', 'value': 'role2'}}),
                          content_type='application/json'))

        self.assertEquals(1, len(rv))
        self.assertEquals(u'hosto', rv[0]['name'])

        # Remove the role (skip reading back the host for simplicity).
        host['roles'] = [u'server']
        rv = self._parse(
            self.app.post('/update/host/hosto',
                          data=json.dumps(host),
                          content_type='application/json'))
        self.assertTrue(rv)

        # Verify that the association is gone by running find() again.
        rv = self._parse(
            self.app.post('/find/host',
                          data=json.dumps({'roles': {'type': 'eq', 'value': 'role2'}}),
                          content_type='application/json'))

        self.assertEquals(0, len(rv))
