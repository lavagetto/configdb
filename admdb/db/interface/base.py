

class DbBase(object):
    """A generic interface to a database."""

    def get_by_name(self, class_name, object_name):
        raise NotImplementedError()

    def session(self):
        raise NotImplementedError()

    def find(self, class_name, attrs):
        raise NotImplementedError()

    def delete(self, class_name, object_name, session):
        raise NotImplementedError()

    def create(self, class_name, attrs, session):
        raise NotImplementedError()

