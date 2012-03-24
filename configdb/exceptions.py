
class Error(Exception):
    pass


class SchemaError(Error):
    pass


class RelationError(Error):
    pass


class AclError(Error):
    pass


class NotFound(Error):
    pass


class RpcError(Error):
    pass


class ValidationError(Error):
    pass


class AuthError(Error):
    pass
