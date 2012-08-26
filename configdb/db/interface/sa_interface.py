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


class SqlAlchemyQueryCriteria(object):
    pass


class SqlAlchemyQueryEquals(SqlAlchemyQueryCriteria):

    def __init__(self, spec):
        self.target = spec['value']

    def get_filter(self, classattr):
        return classattr == self.target


class SqlAlchemyQuerySubstringMatch(SqlAlchemyQueryCriteria):

    def __init__(self, spec):
        self.like_str = '%%%s%%' % spec['value']

    def get_filter(self, classattr):
        return classattr.like(self.like_str)


class SqlAlchemyDbInterface(base.DbInterface):
    """Interface to an SQL database using SQLAlchemy."""

    QUERY_TYPE_MAP = dict(base.DbInterface.QUERY_TYPE_MAP)
    QUERY_TYPE_MAP.update({
            'eq': SqlAlchemyQueryEquals,
            'substring': SqlAlchemyQuerySubstringMatch,
            })

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
        return base.session_context_manager(self.Session())

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
            session = self.Session()
        return session.query(self._get_class(entity_name)).filter_by(
            name=object_name).first()
    
    def find(self, entity_name, query, session=None):
        if session is None:
            session = self.Session()
        classobj = self._get_class(entity_name)
        entity = self._schema.get_entity(entity_name)
        sa_query = session.query(classobj)

        # Assemble the SQL query.  The query is split between
        # SQL-compatible criteria, and postprocessed criteria (which
        # will be applied by the standard _run_query method).
        pp_query = {}
        for field_name, q in query.iteritems():
            if not isinstance(q, SqlAlchemyQueryCriteria):
                pp_query[field_name] = q
            else:
                field = entity.fields[field_name]
                if field.is_relation():
                    classattr = getattr(self._get_class(field.remote_name), 'name')
                else:
                    classattr = getattr(classobj, field_name)
                sa_query = sa_query.filter(q.get_filter(classattr))

        # Apply the post-process query to the SQL results.
        return self._run_query(entity, pp_query, sa_query)

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
