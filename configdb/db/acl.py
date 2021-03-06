from configdb import exceptions


class AuthContext(object):
    """An authentication context.

    Binds together the per-request auth information, so it can be
    evaluated by the ACL rules.

    An AuthContext has the concept of a 'self' object (used to
    implement the '@self' ACL rule), but it does not enforce any
    particular schema on it: it is the responsibility of the
    authentication middleware in the WSGI server to set it to the
    appropriate object (usually the one representing the logged-in
    user).
    """

    def __init__(self, username, groups=None):
        self.user = username
        self.groups = groups or frozenset()
        self.self_obj = None

    def set_self(self, obj):
        self.self_obj = obj

    def is_self(self, obj):
        return (obj and (self.self_obj is not None)
                and (self.self_obj.name == obj.name))

    def get_self(self):
        return self.self_obj

    def get_username(self):
        return self.user


class AclRule(object):

    def match(self, ctx, obj):
        raise NotImplementedError()


class RuleAny(AclRule):

    def match(self, ctx, obj):
        return True


class RuleNone(AclRule):

    def match(self, ctx, obj):
        return False


class RuleMatchUser(AclRule):

    def __init__(self, username):
        self.ok_user = username

    def match(self, ctx, obj):
        return (self.ok_user == ctx.user)


class RuleMatchGroup(AclRule):

    def __init__(self, groupname):
        self.ok_group = groupname

    def match(self, ctx, obj):
        return (self.ok_group in ctx.groups)


class RuleMatchSelf(AclRule):

    def match(self, ctx, obj):
        return ctx.is_self(obj)


class RuleMatchUserByRelation(AclRule):

    def __init__(self, user_attr):
        self.rel_attr = user_attr

    def match(self, ctx, obj):
        if not obj:
            return True
        user_rel_obj = getattr(obj, self.rel_attr)
        self_obj = ctx.get_self()
        return ((self_obj is not None)
                and (user_rel_obj is not None)
                and (self_obj in user_rel_obj))


def _parse_acl_rules(acl_spec):
    """Parse a list of ACL rules (comma separated)."""
    if isinstance(acl_spec, basestring):
        acl_spec = acl_spec.split(',')
    acls = []
    for acl_entry in acl_spec:
        acl_entry = acl_entry.strip()
        if acl_entry == '@self':
            acls.append(RuleMatchSelf())
        elif acl_entry.startswith('@'):
            acls.append(RuleMatchUserByRelation(acl_entry[1:]))
        elif acl_entry.startswith('group/'):
            acls.append(RuleMatchGroup(acl_entry[6:]))
        elif acl_entry.startswith('user/'):
            acls.append(RuleMatchUser(acl_entry[5:]))
        elif acl_entry == '*':
            acls.append(RuleAny())
        elif acl_entry == '!':
            acls.append(RuleNone())
        else:
            raise exceptions.SchemaError('unknown ACL: "%s"' % acl_entry)
    return acls


def parse_acl(acl_dict):
    """Parse an ACL specification.

    A specification is simply a {operation: acl_rules} dictionary,
    where the ACL rules are given as a comma-separated list of
    individual ACL entries. The 'operation' key can be one of 'r' (for
    read access) or 'w' (for modify / create / delete access).

    The default ACL entry allows any access.
    """
    acl = {'r': [RuleAny()], 'w': [RuleAny()]}
    for op, spec in acl_dict.iteritems():
        if op not in ('r', 'w'):
            raise exceptions.SchemaError('unknown ACL op "%s"' % op)
        acl[op] = _parse_acl_rules(spec)
    return acl


class AclMixin(object):
    """A mixin class providing ACL functionality for an object."""

    def set_acl(self, acl_dict=None):
        self._acl = parse_acl(acl_dict) if acl_dict else None

    def has_acl(self):
        return hasattr(self, '_acl') and bool(self._acl)

    def acl_check(self, auth_context, op, obj):
        return (self.has_acl()
                and any(x.match(auth_context, obj)
                        for x in self._acl.get(op, [])))
