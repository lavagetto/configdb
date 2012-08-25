


class Equals(object):

    def __init__(self, value):
        self.value = value

    def to_net(self):
        return {'type': 'eq',
                'value': self.value}


class SubstringMatch(object):

    def __init__(self, needle):
        self.needle = needle

    def to_net(self):
        return {'type': 'substring',
                'value': self.needle}


class RegexpMatch(object):

    def __init__(self, pattern):
        self.pattern = pattern

    def to_net(self):
        return {'type': 'regexp',
                'pattern': self.pattern}


class Query(object):

    def __init__(self, **attrs):
        self.query = attrs

    def to_net(self):
        return dict((k, v.to_net()) for k, v in self.query.iteritems())

