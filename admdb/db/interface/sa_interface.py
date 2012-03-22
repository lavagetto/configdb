import contextlib
import os
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from admdb import exceptions
from admdb.db import schema
from admdb.db.interface import base
from admdb.db.interface import sa_generator


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


class SqlAlchemyDb(base.DbBase):
    """Interface to an SQL database using SQLAlchemy."""

    def __init__(self, uri, schema, schema_dir=None):

        self.Session = scoped_session(
            sessionmaker(autocommit=False, autoflush=False))
        Base = declarative_base()
        Base.query = self.Session.query_property()

        self._objs = {'Base': Base}
        self._schema = schema
        if not schema_dir:
            schema_dir = tempfile.mkdtemp()
        self._schema_dir = schema_dir
        self._load_schema()

        self.engine = create_engine(uri, pool_recycle=1800)
        self.Session.configure(bind=self.engine)
        Base.metadata.create_all(self.engine)
        
    def _load_schema(self):
        schema_file = os.path.join(self._schema_dir, '_admdb_schema.py')
        schema_gen = sa_generator.SqlAlchemyGenerator(self._schema)
        with open(schema_file, 'w') as fd:
            fd.write(schema_gen.generate())
        execfile(schema_file, self._objs)

    def _get_class(self, class_name):
        return self._objs[class_name.capitalize()]

    def get_by_name(self, class_name, object_name):
        return self._get_class(class_name).query.filter_by(
            name=object_name).first()

    def find(self, class_name, attrs):
        # Make relational queries work by name.
        classobj = self._get_class(class_name)
        entity = self._schema.get_entity(class_name)
        query = classobj.query
        for qattr, qvalue in attrs.iteritems():
            classattr = getattr(self._get_class(class_name), qattr)
            field = entity.fields[qattr]
            if field.is_relation():
                rel_obj = self.get_by_name(field.remote_name, qvalue)
                if not rel_obj:
                    raise exceptions.NotFound('%s=%s' % (qattr, qvalue))
                query = query.filter(classattr.contains(rel_obj))
            else:
                query = query.filter(classattr == qvalue)
        return query

    def session(self):
        return unshared_session_manager(self.Session)

    def delete(self, class_name, object_name, session):
        session.delete(self.get_by_name(class_name, object_name))

    def create(self, class_name, attrs, session):
        obj = self._get_class(class_name)()
        entity = self._schema.get_entity(class_name)
        for k, v in attrs.iteritems():
            field = entity.fields[k]
            if field.is_relation():
                rel_attr = getattr(obj, k)
                for lv in v:
                    rel_obj = self.get_by_name(field.remote_name, lv)
                    rel_attr.append(rel_obj)
            else:
                setattr(obj, k, v)
        session.add(obj)
        return obj


