import contextlib
import json
import os
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from configdb import exceptions
from configdb.db import schema
from configdb.db.interface import base
from configdb.db.interface import sa_generator


@contextlib.contextmanager
def unshared_session_manager(sessionmaker):
    s = sessionmaker()
    try:
        yield s
    except:
        s.rollback()
        raise
    else:
        s.commit()


class SqlAlchemyDbInterface(base.DbInterface):
    """Interface to an SQL database using SQLAlchemy."""

    def __init__(self, uri, schema, schema_dir=None):

        self.Session = scoped_session(
            sessionmaker(autocommit=False, autoflush=False))
        Base = declarative_base()
        Base.query = self.Session.query_property()

        self._objs = {'Base': Base}
        self._schema = schema
        self._schema_dir = schema_dir # unused, meant for caching
        self._load_schema()

        self.engine = create_engine(uri, pool_recycle=1800)
        self.Session.configure(bind=self.engine)
        Base.metadata.create_all(self.engine)
        
    def _load_schema(self):
        with tempfile.NamedTemporaryFile() as schema_file:
            schema_gen = sa_generator.SqlAlchemyGenerator(self._schema)
            schema_file.write(schema_gen.generate())
            schema_file.flush()
            execfile(schema_file.name, self._objs)

    def _get_class(self, entity_name):
        return self._objs[entity_name.capitalize()]

    def session(self):
        return unshared_session_manager(self.Session)

    def add_audit(self, entity_name, object_name, operation,
                  data, auth_ctx, session):
        ins = self._objs['audit_table'].insert()
        session.execute(ins, {'entity': entity_name,
                              'object': object_name,
                              'op': operation,
                              'data': json.dumps(data) if data else None,
                              'user': auth_ctx.get_username()})

    def get_audit(self, query, session):
        audit_table = self._objs['audit_table']
        sql_query = None
        for key, value in query.iteritems():
            qstmt = (getattr(audit_table.c, key) == value)
            if sql_query is None:
                sql_query = qstmt
            else:
                sql_query &= qstmt
        return session.execute(
            audit_table.select().where(sql_query).order_by('stamp desc'))

    def get_by_name(self, entity_name, object_name, session=None):
        if session is None:
            session = self.Session
        return session.query(self._get_class(entity_name)).filter_by(
            name=object_name).first()

    def get_approximate_by_name(self, entity_name, object_name, session=None):
        if session is None:
            session = self.Session
        cls = self._get_class(entity_name)
        return session.query(self._get_class(entity_name)).filter(cls.name.like( u"%%%s%%" % object_name)).first()

    def _substring_match(self, data, query):
        (field, classattr, session) = data
        if field.is_relation():
            return self.get_approximate_by_name(
                            field.remote_name, query, session)
        return classattr.like( u"%%%s%%" % query )

    def _exact_match(self, data, query):
        (field, classattr, session) = data
        if field.is_relation():
            return self.get_by_name(
                            field.remote_name, query, session)
        return classattr ==  query
        
        
    
    def find(self, entity_name, attrs, session=None):
        if session is None:
            session = self.Session
        classobj = self._get_class(entity_name)
        entity = self._schema.get_entity(entity_name)
        query = session.query(classobj)
        for qattr, qdata in attrs.iteritems():
            classattr = getattr(classobj, qattr)
            field = entity.fields[qattr]
            if field.is_relation():                
                # Make relational queries work by name. If the field
                # is a relation, the value will be a list.
                for qvalue in qdata:
                    rel_obj = self._proxy_match((field, classattr, session), qvalue)
                    if not rel_obj:
                        raise exceptions.NotFound('%s=%s' % (qattr, qvalue['arg']))
                    query = query.filter(classattr.contains(rel_obj))
            else:
                query = query.filter(self._proxy_match((field, classattr, session), qdata))
        return query


    def delete(self, entity_name, object_name, session):
        session.delete(self.get_by_name(entity_name, object_name, session))

    def create(self, entity_name, attrs, session):
        obj = self._get_class(entity_name)()
        entity = self._schema.get_entity(entity_name)
        for k, v in attrs.iteritems():
            field = entity.fields[k]
            if field.is_relation():
                rel_attr = getattr(obj, k)
                for lv in v:
                    rel_obj = self.get_by_name(
                        field.remote_name, lv, session)
                    rel_attr.append(rel_obj)
            else:
                setattr(obj, k, v)
        session.add(obj)
        return obj


