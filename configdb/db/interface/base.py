import contextlib
from configdb import exceptions
from configdb.db import query


@contextlib.contextmanager
def session_context_manager(session):
    try:
        yield session
    except:
        session.rollback()
        raise
    else:
        try:
            session.commit()
        except:
            session.rollback()
            raise


class DbInterface(object):
    """A generic interface to a database."""

    QUERY_TYPE_MAP = {
        'eq': query.Equals,
        'substring': query.SubstringMatch,
        'regexp': query.RegexpMatch,
        }

    def session(self):
        """Return a session object.

        This object must be passed to the create() and delete()
        methods. Furthermore, it must implement an add() method which,
        when given a database object as returned by get_by_name(),
        will take care of saving the changes to the object in the
        database.
        """

    def get_by_name(self, class_name, object_name, session):
        """Return an instance of an entity, by name."""

    def find(self, class_name, query, session):
        """Query an entity."""

    def delete(self, class_name, object_name, session):
        """Delete an instance."""

    def create(self, class_name, attrs, session):
        """Create a new instance of an entity."""

    def parse_query_spec(self, query_spec):
        """Parse a query spec (a dictionary)."""
        try:
            return self.QUERY_TYPE_MAP[query_spec['type']](query_spec)
        except KeyError:
            raise exceptions.QueryError('invalid query spec')
        except TypeError:
            raise exceptions.QueryError('Query must be a dictionary specifyng type and value of the query')

    def _run_query(self, entity, query, items):
        """Apply a query filter to a list of items."""
        for item in items:
            ok = True
            for field_name, q in query.iteritems():
                field = entity.fields[field_name]
                value = getattr(item, field_name, None)
                if field.is_relation():
                    if value is None or not any(q.match(v.name) for v in value):
                        ok = False
                        break
                elif not q.match(value):
                    ok = False
                    break
            if ok:
                yield item

    def close(self):
        """Release resources associated with the db."""
