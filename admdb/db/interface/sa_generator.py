from admdb.db import schema
import inflect

pl = inflect.engine()


class SqlAlchemyGenerator(object):

    def __init__(self, schema_obj):
        self.schema = schema_obj

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
        return '%s = relationship("%s", secondary=%s, backref="%s")' % (
            field.name,
            field.remote_name.capitalize(),
            self._sa_assoc_table_name(field) + '_table',
            pl.plural(entity.name))

    def _sa_field_assoc_table_def(self, entity, field):
        return """
%s_table = Table('%s', Base.metadata,
    Column('left_id', Integer, ForeignKey('%s.id')),
    Column('right_id', Integer, ForeignKey('%s.id')))""" % (
            self._sa_assoc_table_name(field),
            self._sa_assoc_table_name(field),
            field.local_name,
            field.remote_name)

    def _sa_assoc_table_name(self, field):
        tbls = sorted([field.local_name, field.remote_name])
        return '%s_%s_assoc' % tuple(tbls)
        
    def generate(self):
        out = ['from sqlalchemy import *',
               'from sqlalchemy.orm import *']
        for ent in self.schema.get_entities():
            out.append(self._sa_entity_aux_tables(ent))
            out.append(self._sa_entity_def(ent))
        return '\n'.join(out)

