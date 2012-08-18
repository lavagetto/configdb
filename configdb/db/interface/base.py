

class DbInterface(object):
    """A generic interface to a database."""

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

    def find(self, class_name, attrs, session):
        """Query an entity according to an attribute-wise query."""

    def delete(self, class_name, object_name, session):
        """Delete an instance."""

    def create(self, class_name, attrs, session):
        """Create a new instance of an entity."""

    def _proxy_match(self, data, query):
        """Proxy method to choose between different querying methods.

        In this method, the meaning of 'data' is really different for
        different interfaces.
        """
        qs = query['arg']
        qt = query['type']
        if qt == 'eq':
            return self._exact_match(data, qs)
        elif qt == 'substring':
            return self._substring_match(data, qs)
        else:
            raise NotImplementedError("Query method %s is not implemented" % qt)

