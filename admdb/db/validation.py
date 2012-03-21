import formencode
from formencode import validators
from dateutil import parser as dateutil_parser

Invalid = formencode.Invalid

class iso_timestamp_validator(formencode.FancyValidator):

    def _to_python(self, value, state):
        try:
            return dateutil_parser.parse(value)
        except ValueError, e:
            raise formencode.Invalid(str(e), value, state)


_validator_map = {
    'int': validators.Int(),
    'bool': validators.Bool(),
    'number': validators.Number(),
    'string': validators.UnicodeString(strip=True, not_empty=True),
    'email': validators.Email(resolve_domain=False, not_empty=True),
    'url': validators.URL(add_http=True, check_exists=False,
                          require_tld=False, not_empty=True),
    'ip': validators.IPAddress(),
    'cidr': validators.CIDR(),
    'iso_timestamp': iso_timestamp_validator(),
    }


class ValidatorMixin(object):
    """Mixin class for entity validation."""

    def set_validator(self, validator_def=None):
        if not validator_def:
            return
        vclass = _validator_map.get(validator_def.lower())
        if not vclass:
            vclass = validators.Regex(validator_def)
        self._validator = vclass

    def validate(self, value):
        if hasattr(self, '_validator') and value:
            return self._validator.to_python(value)
        else:
            return value
