from configdb.tests import *
from configdb.db import validation


OK_TESTS = [
    ('int', '32', 32),
    ('int', 32, 32),
    ('int', None, None),

    ('bool', True, True),
    ('bool', False, False),
    ('bool', 'true', True),
    ('bool', 'y', True),
    ('bool', 'false', False),
    ('bool', None, None),

    ('number', '3.2', 3.2),
    ('number', 32, 32),
    ('number', None, None),

    ('string', 'a', 'a'),
    ('string', u'\xe3', u'\xe3'),
    ('string', None, None),

    ('email', 'test@example.com', 'test@example.com'),
    ('email', None, None),

    ('ip', '1.2.3.4', '1.2.3.4'),
    ('ip', None, None),

    ('relation', None, None),
    ('relation', [], []),
    ('relation', ['a', 'b'], ['a', 'b']),
    ('relation', 'not a list', ['not a list']),
    ]

FAIL_TESTS = [
    ('int', 'a'),
    ('int', [1, 2, 3]),

    ('bool', 'something'),

    ('email', 'not_an_email'),

    ('ip', '299.0.0.1'),
    ('ip', 'not an ip'),

    ('relation', 32),
    ('relation', [1, 2, 3]),
    ]


class Field(validation.ValidatorMixin):
    pass


class ValidationTest(TestBase):

    def _validate(self, validator_type, value):
        f = Field()
        f.set_validator(validator_type)
        return f.validate(value)

    def test_validation_ok(self):
        for validator_type, value, expected in OK_TESTS:
            result = self._validate(validator_type, value)
            self.assertEquals(
                expected, result,
                "Validation failure for '%s': %s: result=%s, expected=%s" % (
                    validator_type, value, result, expected))

    def test_validation_failures(self):
        for validator_type, value in FAIL_TESTS:
            try:
                self._validate(validator_type, value)
                assert False, "Validation failure for '%s': %s" % (
                    validator_type, value)
            except validation.Invalid:
                pass
