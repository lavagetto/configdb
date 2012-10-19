import crypt
from flask import request
from configdb.db import acl

def user_auth_fn(user_entity_name='user'):
    """Auth function generator for user-based schemas.

    The default authentication functions assume that a "user" entity
    exists in your schema with a "password" field, and it will attempt
    to authenticate against it using the system crypt().
    """
    def _user_auth_fn(api, data):
        username = data.get('username')
        password = data.get('password')
        if username and password:
            user_obj = api.db.get_by_name(user_entity_name, username, api.db.Session())
            if user_obj:
                enc_password = crypt.crypt(password, user_obj.password)
                if enc_password == user_obj.password:
                    return username
    return _user_auth_fn


def user_auth_context_fn(user_entity_name='user'):
    """Auth context function generator for user-based schemas.

    Returns an acl.AuthContext object associated with the logged-in
    user, and sets 'self' to the related database object.
    """
    def _user_auth_context_fn(api, username):
        ctx = acl.AuthContext(username)
        user_obj = api.db.get_by_name(user_entity_name, username, api.db.Session())
        if user_obj:
            ctx.set_self(user_obj)
        return ctx
    return _user_auth_context_fn


def external_auth_fn(api, data):
    """Auth function for external HTTP authentication.

    Use this if you're managing authentication externally (say, in
    Apache).  Supports anything that sets the 'REMOTE_USER'
    environment variable.
    """
    return request.environ.get('REMOTE_USER')


def external_auth_context_fn(api, auth_token):
    """Auth context function for external HTTP authentication.

    Use this if you're managing authentication externally (say, in
    Apache).  Supports anything that sets the 'REMOTE_USER'
    environment variable.
    """
    return acl.AuthContext(auth_token)
