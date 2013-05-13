"""WSGI database API application.

A note on authentication:

Authentication works like a standard web app: session data is stored
in a signed client-side cookie. If no signed session cookie is
present, we return a status of 403. The client is supposed to request
a login session at the /login URL endpoint.

"""

import functools
import json
import logging
from flask import Flask, Blueprint, request, jsonify, current_app, \
    session, abort, g
from configdb import exceptions
from configdb.db import acl
from configdb.db import db_api
from configdb.db import schema
from configdb.server import auth
from datetime import timedelta

log = logging.getLogger(__name__)
api_app = Blueprint('configdb', __name__)


def json_request(fn):
    """JSON request encoding.

    Incoming POST requests must have a Content-Type of
    'application/json', and the request body must contain a
    JSON-encoded dictionary of key/value pairs.
    """
    @functools.wraps(fn)
    def _json_request_wrapper(*args, **kwargs):
        if request.method == 'POST':
            if request.content_type != 'application/json':
                abort(400)
            try:
                g.request_data = json.loads(request.data)
            except:
                abort(400)
        return fn(*args, **kwargs)
    return _json_request_wrapper


def json_response(fn):
    """JSON response encoding.

    All responses will have a Content-Type of 'application/json', and
    they will contain a JSON-encoded dictionary wrapping the actual
    result. The dictionary will always contain an 'ok' boolean
    attribute indicating whether an error occurred or not. If 'ok' is
    True, the result will be found in the 'result' attribute,
    otherwise the 'error' attribute will contain details about the
    error.

    Any exception in the wrapped method will be caught and wrapped.
    """
    @functools.wraps(fn)
    def _json_response_wrapper(*args, **kwargs):
        try:
            return jsonify(
                {'ok': True,
                 'result': fn(*args, **kwargs)})
        except Exception, e:
            log.exception('exception in url=%s' % request.url)
            return jsonify(
                {'ok': False,
                 'error': str(e)})
    return _json_response_wrapper


def _to_net(class_name, item):
    """An Entity.to_net() wrapper that works on items and lists."""
    if hasattr(item, 'next'):
        return [_to_net(class_name, x) for x in item]
    entity = g.api.schema.get_entity(class_name)
    return entity.to_net(item)


@api_app.before_request
def set_api():
    g.api = current_app.api
    session.permanent = True
    current_app.permanent_session_lifetime = timedelta(minutes=120)


def authenticate(fn):
    @functools.wraps(fn)
    def _auth_wrapper(*args, **kwargs):
        if current_app.config.get('AUTH_BYPASS'):
            g.auth_ctx = acl.AuthContext(None)
        else:
            if (session.new
                or (session.get('auth_ok') != True)
                or not session.get('auth_token')):
                abort(403)
            auth_ctx_fn = current_app.config['AUTH_CONTEXT_FN']
            g.auth_ctx = auth_ctx_fn(g.api, session['auth_token'])
        return fn(*args, **kwargs)
    return _auth_wrapper


@api_app.route('/login', methods=['POST'])
@json_request
@json_response
def login():
    auth_fn = current_app.config['AUTH_FN']
    auth_token = auth_fn(g.api, g.request_data)
    if not auth_token:
        raise exceptions.AuthError('Authentication error')

    session['auth_ok'] = True
    session['auth_token'] = auth_token
    return True


@api_app.route('/create/<class_name>', methods=['POST'])
@authenticate
@json_request
@json_response
def create(class_name):
    return g.api.create(class_name, g.request_data, g.auth_ctx)


@api_app.route('/get/<class_name>/<path:object_name>')
@authenticate
@json_response
def get(class_name, object_name):
    return _to_net(class_name,
                   g.api.get(class_name, object_name, g.auth_ctx))


@api_app.route('/update/<class_name>/<path:object_name>', methods=['POST'])
@authenticate
@json_request
@json_response
def update(class_name, object_name):
    return g.api.update(class_name, object_name, g.request_data, g.auth_ctx)


@api_app.route('/find/<class_name>', methods=['POST'])
@authenticate
@json_request
@json_response
def find(class_name):
    return _to_net(class_name,
                   g.api.find(class_name, g.request_data, g.auth_ctx))


@api_app.route('/delete/<class_name>/<path:object_name>')
@authenticate
@json_response
def delete(class_name, object_name):
    return g.api.delete(class_name, object_name, g.auth_ctx)


@api_app.route('/timestamp/<class_name>')
@authenticate
@json_response
def ts(class_name):
    return g.api.get_timestamp(class_name, g.auth_ctx)


@api_app.route('/audit', methods=['POST'])
@authenticate
@json_request
@json_response
def get_audit():
    def _audit_to_dict(x):
        return {'entity': x.entity,
                'object': x.object,
                'op': x.op,
                'data': x.data,
                'user': x.user,
                'stamp': x.stamp.isoformat()}
    return [_audit_to_dict(x)
            for x in g.api.get_audit(g.request_data, g.auth_ctx)]


@api_app.route('/schema')
@authenticate
def get_schema():
    return current_app.config['SCHEMA_JSON']


def make_app(config={}):
    """Read config and initialize WSGI application.

    The 'config' argument can be used to override autodetected
    configuration settings. The code will first attempt to load the
    application config from the file defined in the environment
    variable APP_CONFIG, if present.
    """

    # Create Flask app.
    app = Flask(__name__)
    app.config.from_envvar('APP_CONFIG', silent=True)
    app.config.update(config)
    app.register_blueprint(api_app)
    # Initialize configdb configuration.
    if 'AUTH_FN' not in app.config:
        app.config['AUTH_FN'] = auth.user_auth_fn()
    if 'AUTH_CONTEXT_FN' not in app.config:
        app.config['AUTH_CONTEXT_FN'] = auth.user_auth_context_fn()

    # Read schema from the schema file.
    if 'SCHEMA_FILE' not in app.config:
        raise Exception('SCHEMA_FILE undefined!')
    with open(app.config['SCHEMA_FILE'], 'r') as fd:
        app.config['SCHEMA_JSON'] = fd.read()

    # Initialize the database interface.
    schema_obj = schema.Schema(app.config['SCHEMA_JSON'])
    db_driver = app.config.get('DB_DRIVER', 'sqlalchemy')
    if db_driver == 'sqlalchemy':
        from configdb.db.interface import sa_interface
        db = sa_interface.SqlAlchemyDbInterface(
            app.config.get('DB_URI', 'sqlite:///:memory:'),
            schema_obj)
    elif db_driver == 'leveldb':
        from configdb.db.interface import leveldb_interface
        db = leveldb_interface.LevelDbInterface(
            app.config['DB_URI'],
            schema_obj)
    elif db_driver == 'zookeeper':
        from configdb.db.interface import zookeeper_interface
        if not 'ZK_HOSTS' in app.config:
            raise Exception('you need to define ZK_HOSTS list to use zookeeper as db backend')
        db = zookeeper_interface.ZookeeperInterface(app.config['ZK_HOSTS'], schema_obj, app.config['DB_URI'])
    else:
        raise Exception('DB_DRIVER not one of "sqlalchemy" or "leveldb"')

    app.api = db_api.AdmDbApi(schema_obj, db)

    return app


def main(argv=None):
    import argparse
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument('--config',
                        help='Location of the app config file')
    parser.add_argument('--port', type=int, default=3000,
                        help='TCP port to listen to (default 3000)')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args(argv)

    if args.config:
        os.environ['APP_CONFIG'] = args.config

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO)

    try:
        app = make_app()
        app.run(port=args.port, debug=args.debug)
    except Exception, e:
        log.exception('Fatal error')
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
