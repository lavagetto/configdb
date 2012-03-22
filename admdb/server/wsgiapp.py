import functools
import json
import logging
from flask import Flask, Blueprint, request, jsonify, current_app, \
    session, abort, g
from admdb import exceptions
from admdb.db import schema
from admdb.db import db_api
from admdb.db.interface import sa_interface
from admdb.server import auth

log = logging.getLogger(__name__)
api_app = Blueprint('admdb', __name__)


def json_request(fn):
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


def to_dict(class_name, item):
    if isinstance(item, list):
        return [to_dict(class_name, x) for x in item]
    entity = g.api.schema.get_entity(class_name)
    return entity.to_net(item)


# Authentication works like a standard web app: if no signed session
# cookie is present, we return a status of 403. The client is supposed
# to request a login session with username and password at the /login
# URL endpoint.
#
# The authentication support is fully modular, two hooks are provided
# to support different authentication behaviors than the default:
#
# app.config['AUTH_FN']
#   A function that gets called with on /login, with the request data
#   dictionary as its argument. It should authenticate the credentials
#   and return an authentication token if the authentication was
#   successful, or None otherwise. The returned auth token will be
#   saved in the client session and passed to the AUTH_CONTEXT_FN.
#
# app.config['AUTH_CONTEXT_FN']
#   A function that is called on every request, with the auth token
#   as argument. It is supposed to return an instance of acl.AuthContext
#   initialized with the proper authentication context data.



@api_app.before_request
def set_api():
    g.api = current_app.api


def authenticate(fn):
    @functools.wraps(fn)
    def _auth_wrapper(*args, **kwargs):
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


@api_app.route('/get/<class_name>/<object_name>')
@authenticate
@json_response
def get(class_name, object_name):
    return to_dict(class_name,
                   g.api.get(class_name, object_name, g.auth_ctx))


@api_app.route('/update/<class_name>/<object_name>', methods=['POST'])
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
    return to_dict(class_name,
                   g.api.find(class_name, g.request_data, g.auth_ctx))


@api_app.route('/delete/<class_name>/<object_name>')
@authenticate
@json_response
def delete(class_name, object_name):
    return g.api.delete(class_name, object_name, g.auth_ctx)


@api_app.route('/schema')
@authenticate
def get_schema():
    return current_app.config['SCHEMA_JSON']


def make_app(config={}):
    """Read config and initialize Flask app."""
    # Create Flask app.
    app = Flask(__name__)
    app.config.from_envvar('APP_CONFIG', silent=True)
    app.config.update(config)
    app.register_blueprint(api_app)

    # Initialize admdb configuration.
    if 'SCHEMA_FILE' not in app.config:
        raise Exception('SCHEMA_FILE undefined!')
    if 'AUTH_FN' not in app.config:
        app.config['AUTH_FN'] = auth.user_auth_fn()
    if 'AUTH_CONTEXT_FN' not in app.config:
        app.config['AUTH_CONTEXT_FN'] = auth.user_auth_context_fn()

    # Read schema from the schema file.
    with open(app.config['SCHEMA_FILE'], 'r') as fd:
        app.config['SCHEMA_JSON'] = fd.read()

    # Initialize the database interface.
    schema_obj = schema.Schema(app.config['SCHEMA_JSON'])
    db = sa_interface.SqlAlchemyDb(
        app.config.get('DB_URI', 'sqlite:///:memory:'),
        schema_obj)
    app.api = db_api.AdmDbApi(schema_obj, db)

    return app

