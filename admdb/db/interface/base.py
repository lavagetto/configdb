

class DbInterface(object):
    """A generic interface to a database."""

    def get_by_name(self, class_name, object_name):
        """Return an instance of an entity, by name."""

    def session(self):
        """Return a session object.

        This object must be passed to the create() and delete()
        methods. Furthermore, it must implement an add() method which,
        when given a database object as returned by get_by_name(),
        will take care of saving the changes to the object in the
        database.
        """

    def find(self, class_name, attrs):
        """Query an entity according to an attribute-wise query."""

    def delete(self, class_name, object_name, session):
        """Delete an instance."""

    def create(self, class_name, attrs, session):
        """Create a new instance of an entity."""

