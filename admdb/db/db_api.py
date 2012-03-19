from admdb import exceptions
from admdb.db import schema


class AdmDbApi(object):

    def __init__(self, schema, db):
        self.db = db
        self.schema = schema

    def _diff_object(self, entity, obj, new_data):
        """Returns a list of modified fields."""
        diffs = {}
        for field in entity.fields.itervalues():
            if field.name not in new_data:
                continue
            old_value = getattr(obj, field.name)
            new_value = new_data[field.name]
            if isinstance(field, schema.Relation):
                old_value = set(x.name for x in old_value)
                new_value = set(new_value or [])
            if old_value != new_value:
                diffs[field.name] = (old_value, new_value)
        return diffs

    def _apply_diff(self, entity, obj, diffs):
        for field_name, diffpair in diffs.iteritems():
            field = entity.fields[field_name]
            old_value, new_value = diffpair
            if isinstance(old_value, set):
                remote_class_name = field.remote_name
                to_add = new_value - old_value
                to_remove = old_value - new_value
                relation = getattr(obj, field_name)
                for rel_name in to_add:
                    rel_obj = self.db.get_by_name(field.remote_name, rel_name)
                    if not rel_obj:
                        raise exceptions.RelationError(
                            'no such object, %s=%s' % (
                                field.remote_name, rel_name))
                    relation.append(rel_obj)
                for rel_name in to_remove: 
                    rel_obj = self.db.get_by_name(field.remote_name, rel_name)
                    relation.remove(rel_obj)
            else:
                setattr(obj, field_name, new_value)

    def _authorize_obj_op(self, entity, auth_context, op, obj, fields):
        for field_name in fields:
            field = entity.fields[field_name]
            if ((field.has_acl()
                 and not field.acl_check(auth_context, op, obj))
                or not entity.acl_check(auth_context, op, obj)):
                raise exceptions.AclError(
                    'unauthorized change to %s.%s' % (
                        entity.name, field_name))

    def _authorize_op(self, entity, auth_context, op, obj):
        if not entity.acl_check(auth_context, op, obj):
            raise exceptions.AclError(
                'unauthorized change to %s' % (
                    entity.name,))

    def update(self, class_name, object_name, data, auth_context):
        ent = self.schema.get_entity(class_name)
        if not ent:
            raise exceptions.NotFound(class_name)

        obj = self.db.get_by_name(class_name, object_name)
        if not obj:
            raise exceptions.NotFound('%s/%s' % (class_name, object_name))

        diffs = self._diff_object(ent, obj, data)
        self._authorize_obj_op(ent, auth_context, 'w', obj, diffs.keys())
        self._apply_diff(ent, obj, diffs)
        return True

    def delete(self, class_name, object_name, auth_context):
        ent = self.schema.get_entity(class_name)
        if not ent:
            raise exceptions.NotFound(class_name)

        obj = self.db.get_by_name(class_name, object_name)
        if not obj:
            return True

        self._authorize_op(ent, auth_context, 'w', obj)
        with self.db.session() as session:
            self.db.delete(class_name, object_name, session)
        return True

    def create(self, class_name, data, auth_context):
        ent = self.schema.get_entity(class_name)
        if not ent:
            raise exceptions.NotFound(class_name)

        self._authorize_op(ent, auth_context, 'w', None)
        with self.db.session() as session:
            obj = self.db.create(class_name, data, session)

        obj = self.db.get_by_name(class_name, data['name'])
        return obj.id

    def get(self, class_name, object_name, auth_context):
        ent = self.schema.get_entity(class_name)
        if not ent:
            raise exceptions.NotFound(class_name)

        obj = self.db.get_by_name(class_name, object_name)
        if not obj:
            raise exceptions.NotFound('%s/%s' % (class_name, object_name))

        self._authorize_op(ent, auth_context, 'r', obj)
        return obj

    def find(self, class_name, query, auth_context):
        ent = self.schema.get_entity(class_name)
        if not ent:
            raise exceptions.NotFound(class_name)

        self._authorize_op(ent, auth_context, 'r', None)
        return self.db.find(class_name, query).all()
