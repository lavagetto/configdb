import formencode
from formencode import validators

Invalid = formencode.Invalid


class RelationValidator(formencode.FancyValidator):

    def _to_python(self, value, state):
        # Promote string to list.
        if isinstance(value, basestring):
            return [value]
        if (value is None or
            (isinstance(value, list) and
             (not value or isinstance(value[0], basestring)))):
            return value
        raise Invalid('relation not a list of strings', value, state)


_validator_map = {
    'int': validators.Int(),
    'bool': validators.StringBool(),
    'number': validators.Number(),
    'string': validators.UnicodeString(strip=True, not_empty=True),
    'email': validators.Email(resolve_domain=False, not_empty=True),
    'url': validators.URL(add_http=True, check_exists=False,
                          require_tld=False, not_empty=True),
    'ip': validators.IPAddress(),
    'cidr': validators.CIDR(),
    'relation': RelationValidator(),
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
