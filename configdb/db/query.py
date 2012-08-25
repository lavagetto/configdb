import re


class Criteria(object):
    pass


class Equals(Criteria):

    def __init__(self, spec):
        self.target = spec['value']

    def match(self, value):
        return value == self.target


class SubstringMatch(Criteria):

    def __init__(self, spec):
        self.target = spec['value']

    def match(self, value):
        if value is not None:
            return (value.find(self.target) >= 0)


class RegexpMatch(Criteria):

    def __init__(self, spec):
        self.pattern = re.compile(spec['pattern'])

    def match(self, value):
        if value is not None:
            return (self.pattern.search(value) is not None)

