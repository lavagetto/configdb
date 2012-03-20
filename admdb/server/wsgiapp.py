import functools
import json
import logging
from flask import Flask, Blueprint, request, jsonify, current_app, abort, g
from admdb.db import schema
from admdb.db import db_api
from admdb.db.interface import sa_interface

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
    out = {}
    for f in entity.fields.itervalues():
        value = getattr(item, f.name)
        if f.is_relation():
            out[f.name] = [x.name for x in value]
        else:
            out[f.name] = value
    return out


@api_app.before_request
def set_auth_context():
    g.api = current_app.api
    if current_app.config.get('TESTING'):
        user_name = 'admin'
    else:
        user_name = request.environ.get('REMOTE_USER')
    g.auth_ctx = g.api.auth_context_for_user(user_name)


@api_app.route('/create/<class_name>', methods=['POST'])
@json_request
@json_response
def create(class_name):
    return g.api.create(class_name, g.request_data, g.auth_ctx)


@api_app.route('/get/<class_name>/<object_name>')
@json_response
def get(class_name, object_name):
    return to_dict(class_name,
                   g.api.get(class_name, object_name, g.auth_ctx))


@api_app.route('/update/<class_name>/<object_name>', methods=['POST'])
@json_request
@json_response
def update(class_name, object_name):
    return g.api.update(class_name, object_name, g.request_data, g.auth_ctx)


@api_app.route('/find/<class_name>', methods=['POST'])
@json_request
@json_response
def find(class_name):
    return to_dict(class_name,
                   g.api.find(class_name, g.request_data, g.auth_ctx))


@api_app.route('/delete/<class_name>/<object_name>', methods=['POST'])
@json_response
def delete(class_name, object_name):
    return g.api.delete(class_name, object_name, g.auth_ctx)


@api_app.route('/schema')
@json_response
def get_schema():
    return current_app.config['SCHEMA_JSON']


def make_app(config={}):
    """Read config and initialize Flask app."""
    # Create Flask app.
    app = Flask(__name__)
    app.config.from_envvar('APP_CONFIG', silent=True)
    app.config.update(config)
    app.register_blueprint(api_app)

    # Initialize admdb from config.
    if 'SCHEMA_FILE' not in app.config:
        raise Exception('SCHEMA_FILE undefined!')
    with open(app.config['SCHEMA_FILE'], 'r') as fd:
        app.config['SCHEMA_JSON'] = fd.read()
        schema_obj = schema.Schema(app.config['SCHEMA_JSON'])
        db = sa_interface.SqlAlchemyDb(
            app.config.get('DB_URI', 'sqlite:///:memory:'),
            schema_obj)
        app.api = db_api.AdmDbApi(schema_obj, db)

    return app

