from admdb import exceptions
from admdb.db import acl
from admdb.db import schema
from admdb.db import validation


class AdmDbApi(object):
    """High-level interface to the database."""

    def __init__(self, schema, db):
        self.db = db
        self.schema = schema

    def _validate(self, entity, data):
        """Perform validation on input data."""
        out = {}
        errors = []
        input_fields = set(data.keys())

        # First, deserialize the input data.
        try:
            data = entity.from_net(data)
        except ValueError, e:
            raise exceptions.ValidationError(
                'Validation error in deserialization: %s' % str(e))

        # Now perform validation on all fields.
        for field in entity.fields.itervalues():
            if field.name not in data:
                continue
            try:
                out[field.name] = field.validate(data[field.name])
                input_fields.remove(field.name)
            except validation.Invalid, e:
                errors.append('%s: %s' % (field.name, e))
        # If there have been any errors, raise a ValidationError.
        if errors:
            raise exceptions.ValidationError(
                'Validation error for "%s": %s' % (
                    entity.name, ', '.join(errors)))
        # Complain about extra fields.
        if input_fields:
            raise exceptions.ValidationError(
                'Unknown extra fields for "%s": %s' % (
                    entity.name, ', '.join(input_fields)))
        return out

    def _diff_object(self, entity, obj, new_data):
        """Returns a list of modified fields."""
        diffs = {}
        for field in entity.fields.itervalues():
            if field.name not in new_data:
                continue
            old_value = getattr(obj, field.name)
            new_value = new_data[field.name]
            if field.is_relation():
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
                remote_entity_name = field.remote_name
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

    def update(self, entity_name, object_name, data, auth_context):
        """Update an existing instance."""
        ent = self.schema.get_entity(entity_name)
        if not ent:
            raise exceptions.NotFound(entity_name)

        obj = self.db.get_by_name(entity_name, object_name)
        if not obj:
            raise exceptions.NotFound('%s/%s' % (entity_name, object_name))

        diffs = self._diff_object(
            ent, obj, self._validate(ent, data))
        self.schema.acl_check_fields(
            ent, diffs.keys(), auth_context, 'w', obj)
        self._apply_diff(ent, obj, diffs)
        return True

    def delete(self, entity_name, object_name, auth_context):
        """Delete an instance."""
        ent = self.schema.get_entity(entity_name)
        if not ent:
            raise exceptions.NotFound(entity_name)

        obj = self.db.get_by_name(entity_name, object_name)
        if not obj:
            return True

        self.schema.acl_check_entity(ent, auth_context, 'w', obj)
        with self.db.session() as session:
            self.db.delete(entity_name, object_name, session)
        return True

    def create(self, entity_name, data, auth_context):
        """Create a new instance."""
        ent = self.schema.get_entity(entity_name)
        if not ent:
            raise exceptions.NotFound(entity_name)

        self.schema.acl_check_entity(ent, auth_context, 'w', None)
        with self.db.session() as session:
            obj = self.db.create(entity_name,
                                 self._validate(ent, data),
                                 session)

        obj = self.db.get_by_name(entity_name, data['name'])
        return obj.id

    def get(self, entity_name, object_name, auth_context):
        """Return a specific instance."""
        ent = self.schema.get_entity(entity_name)
        if not ent:
            raise exceptions.NotFound(entity_name)

        obj = self.db.get_by_name(entity_name, object_name)
        if not obj:
            raise exceptions.NotFound('%s/%s' % (entity_name, object_name))

        self.schema.acl_check_entity(ent, auth_context, 'r', obj)
        return obj

    def find(self, entity_name, query, auth_context):
        """Find all instances matching a query."""
        ent = self.schema.get_entity(entity_name)
        if not ent:
            raise exceptions.NotFound(entity_name)

        self.schema.acl_check_entity(ent, auth_context, 'r', None)
        return self.db.find(entity_name, query).all()
