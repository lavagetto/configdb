from configdb.db import schema
import inflect

pl = inflect.engine()


class SqlAlchemyGenerator(object):

    def __init__(self, schema_obj):
        self.schema = schema_obj
        self.defined_relations = []

    def _audit_table_def(self):
        return """
audit_table = Table('_audit', Base.metadata,
    Column('user', String(64), index=True),
    Column('entity', String(64), index=True),
    Column('object', String(64), index=True),
    Column('op', String(8), index=True),
    Column('stamp', DateTime(), default=datetime.now),
    Column('data', UnicodeText()))
"""

    def _sa_entity_def(self, entity):
        cols = []
        for field in entity.fields.itervalues():
            if field.is_relation():
                cols.append(self._sa_field_relation_def(entity, field))
            else:
                cols.append(self._sa_field_def(entity, field))
        return """
class %(class_name)s(Base):
    __tablename__ = '%(table_name)s'
    id = Column(Integer, primary_key=True)
    %(cols)s
""" % {'class_name': entity.name.capitalize(),
       'table_name': entity.name,
       'cols': '\n    '.join(cols)}

    def _sa_entity_aux_tables(self, entity):
        out = []
        for field in entity.fields.itervalues():
            if field.is_relation():
                out.append(self._sa_field_assoc_table_def(entity, field))
        return '\n'.join(out)

    def _sa_field_type(self, field):
        type_map = {
            'datetime': 'DateTime',
            'bool': 'Boolean',
            'int': 'Integer',
            'number': 'Float',
            'string': 'Unicode',
            'text': 'UnicodeText',
            'binary': 'BLOB',
            'password': 'String',
            }
        type_args = []
        if 'size' in field.attrs:
            type_args.append(str(field.attrs['size']))
        return '%s(%s)' % (type_map[field.type],
                           ', '.join(type_args))

    def _sa_field_def(self, entity, field):
        # Split db attributes from the rest.
        attrs = field.attrs
        sa_type = self._sa_field_type(field)
        sa_attrs = {}
        for sa_attr in ('index', 'unique', 'nullable', 'default'):
            if sa_attr in attrs:
                sa_attrs[sa_attr] = attrs.pop(sa_attr)

        # Generate field definition (SA declarative style).
        args = [sa_type] + [
            '%s=%s' % (k, v) for k, v in sa_attrs.items()]
        return '%s = Column(%s)' % (
            field.name, ', '.join(args))

    def _sa_field_relation_def(self, entity, field):
        assoc_table = self._sa_assoc_table_name(field)
        if assoc_table in self.defined_relations:
            # In this case, we don't need a backref (it already exists)
            return '%s = relationship("%s", secondary=%s)' % (
                field.name,
                field.remote_name.capitalize(),
                assoc_table + '_table')
        return '%s = relationship("%s", secondary=%s, backref="%s")' % (
            field.name,
            field.remote_name.capitalize(),
            self._sa_assoc_table_name(field) + '_table',
            pl.plural(entity.name))

    def _sa_field_assoc_table_def(self, entity, field):
        table_name = self._sa_assoc_table_name(field)
        if table_name in self.defined_relations:
            #we have a 2-way used relation, and do not want to re-define it
            return ""
        self.defined_relations.append(table_name)
        return """
%s_table = Table('%s', Base.metadata,
    Column('left_id', Integer, ForeignKey('%s.id')),
    Column('right_id', Integer, ForeignKey('%s.id')))""" % (
            table_name,
            table_name,
            field.local_name,
            field.remote_name)

    def _sa_assoc_table_name(self, field):
        tbls = sorted([field.local_name, field.remote_name])
        tbls.append(field.relation_id)
        return '%s_%s_assoc_%s' % tuple(tbls)

    def generate(self):
        out = ['from sqlalchemy import *',
               'from sqlalchemy.orm import *',
               'from datetime import datetime',
               self._audit_table_def()]
        for ent in self.schema.get_entities():
            out.append(self._sa_entity_aux_tables(ent))
            out.append(self._sa_entity_def(ent))
        return '\n'.join(out)
