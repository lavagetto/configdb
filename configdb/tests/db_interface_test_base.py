from configdb import exceptions


class DbInterfaceTestBase(object):

    def init_db(self):
        raise NotImplementedError()

    def load_db(self):
        db = self.init_db()
        with db.session() as s:
            a = db.create('host', {'ip': '1.2.3.4', 'name': 'obz'}, s)
            r = db.create('role', {'name': 'role1'}, s)
            a.roles.append(r)
            s.add(a)
        return db
        
    def test_init_ok(self):
        db = self.init_db()
        self.assertTrue(db is not None)

    def test_simple_insert(self):
        db = self.load_db()

        # verify
        b = db.get_by_name('host', 'obz')
        self.assertEquals('obz', b.name)
        self.assertEquals('1.2.3.4', b.ip)
        self.assertEquals(None, b.ip6)

        r = db.get_by_name('role', 'role1')
        self.assertEquals('role1', r.name)
        self.assertTrue(r in b.roles)

    def test_relation_semantics(self):
        db = self.load_db()
        b = db.get_by_name('host', 'obz')
        role_names = [x.name for x in b.roles]
        self.assertEquals(['role1'], role_names)

    def _find(self, db, entity_name, raw_query):
        query = dict((k, db.parse_query_spec(v))
                     for k, v in raw_query.iteritems())
        return list(db.find(entity_name, query))

    def test_find(self):
        db = self.load_db()
        r = self._find(db, 'host', {'name': {'type': 'eq', 'value': 'obz'}})
        self.assertEquals(1, len(r))
        self.assertEquals('obz', r[0].name)

    def test_find_relation(self):
        db = self.load_db()
        r = self._find(db, 'host', {'roles': {'type': 'eq', 'value': 'role1'}})
        self.assertEquals(1, len(r))
        self.assertEquals('obz', r[0].name)

    def test_find_nonexisting(self):
        db = self.load_db()
        r = self._find(db, 'host', {'name': {'type': 'eq', 'value': 'nonexisting'}})
        self.assertEquals(0, len(r))

    def test_find_multiple_criteria(self):
        db = self.load_db()
        r = self._find(db, 'host', {'roles': {'type': 'eq', 'value': 'role1'},
                                    'name': {'type': 'eq', 'value': 'obz'}})
        self.assertEquals(1, len(r))
        self.assertEquals('obz', r[0].name)

    def test_find_nonmatching_multiple_criteria(self):
        db = self.load_db()
        r = self._find(db, 'host', {'roles': {'type': 'eq', 'value': 'role1'},
                                    'name': {'type': 'eq', 'value': 'ooops'}})
        self.assertEquals(0, len(r))

    def test_find_nonexisting_relation(self):
        db = self.load_db()
        r = self._find(db, 'host', {'roles': {'type': 'eq', 'value':'zzzz'}})
        self.assertEquals(0, len(r))
                
