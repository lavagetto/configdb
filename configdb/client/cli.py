import argparse
import getpass
import inflect
import json
import logging
import re
import os
import sys
from configdb import exceptions
from configdb.db import schema
from configdb.client import connection
from configdb.client import query
from configdb.client import backup


log = logging.getLogger(__name__)
pl = inflect.engine()


class CmdError(Exception):
    pass


def read_password(value):
    return getpass.getpass(prompt='Password: ')


def read_from_file(value):
    with open(value, 'r') as fd:
        return fd.read()

class JsonPlain(object):
    @staticmethod
    def pprint(value):
        """Pretty-print value as JSON."""
        print json.dumps(value, sort_keys=True, indent=4)



class Action(object):
    view = JsonPlain

    @classmethod
    def set_view(cls, viewclass):
        cls.view = viewclass
        
    def parse_field_value(self, field, value):
        type_map = {
            'string': str,
            'int': int,
	    'number': float,
            'password': read_password,
            'text': read_from_file,
            'binary': read_from_file,
            'relation': lambda x: x.split(','),
            }
        return type_map[field.type](value)

    def add_standard_entity_fields(self, entity, parser):
        for field in entity.fields.itervalues():
            parser.add_argument('--%s' % field.name)

    def get_standard_entity_fields(self, entity, args):
        out = {}
        for field in entity.fields.itervalues():
            # There are three different cases we must handle here:
            # 1) the value is None, in this case no option was
            # specified, skip the field altogether.
            # 2) the value is empty, the option was specified but no
            # content was given: this means that we should clear the
            # field, so set it to None here.
            # 3) a non-empty value was given.
            value = getattr(args, field.name)
            if value == '':
                out[field.name] = None
            elif value is not None:
                # Interpret the value according to the field type.
                out[field.name] = self.parse_field_value(field, value)
        return out


class CreateAction(Action):
    """Create a new instance."""

    name = 'create'

    def __init__(self, entity, parser):
        self.add_standard_entity_fields(entity, parser)

    def run(self, conn, entity, args):
        data = self.get_standard_entity_fields(entity, args)
        log.info('create: %s', data)
        conn.create(entity.name, data)


class UpdateAction(Action):
    """Update an instance."""

    name = 'mod'

    def __init__(self, entity, parser):
        parser.add_argument('_name', metavar='NAME')
        self.has_relations = None
        for field in entity.fields.itervalues():
            descr = field.attrs.get('description', '')
            if field.is_relation():
                opt_name = '--%s' % pl.singular_noun(field.name)
                descr += '%s(use with --add / --delete)' % (
                    ' ' if descr else '')
                parser.add_argument(opt_name, help=descr,
                                    dest=field.name)
                self.has_relations = True
            else:
                opt_name = '--%s' % field.name
                parser.add_argument(opt_name, help=descr,
                                    dest=field.name)
        if self.has_relations:
            parser.add_argument('--add', action='store_true')
            parser.add_argument('--delete', action='store_true')

    def run(self, conn, entity, args):
        if self.has_relations and args.add and args.delete:
            raise CmdError('Can\'t specify --add and --delete together')

        obj = conn.get(entity.name, args._name)
        update_data = {}
        for field in entity.fields.itervalues():
            value = getattr(args, field.name)
            if value is None:
                continue
            if field.is_relation():
                if not value:
                    raise CmdError('Relational argument "%s" is empty' % (
                            field.name,))
                rel_list = set(obj[field.name])
                if args.add:
                    rel_list.add(value)
                elif args.delete:
                    rel_list.discard(value)
                else:
                    raise CmdError('Specified relational attribute without '
                                   '--add or --delete')
                update_data[field.name] = list(rel_list)
            else:
                # Auto-clear items.
                if not value:
                    value = None
                update_data[field.name] = value

        log.info('update: %s/%s %s', entity.name, args._name, update_data)
        conn.update(entity.name, args._name, update_data)


class GetAction(Action):
    """Get a specific instance."""

    name = 'get'

    def __init__(self, entity, parser):
        parser.add_argument('_name', metavar='NAME')

    def run(self, conn, entity, args):
        obj = conn.get(entity.name, args._name)
        self.view.pprint(obj)

class TimestampAction(Action):
    """Get the timestamp of last update on an entity."""

    name = 'timestamp'

    def __init__(self, entity, parser):
        pass

    def run(self, conn, entity, args):
        print conn.get_timestamp(entity.name)
        


class FindAction(Action):
    """Find instances."""

    name = 'find'

    def __init__(self, entity, parser):
        self.add_standard_entity_fields(entity, parser)

    def _get_query(self, entity, args):
        qargs = {}
        for field in entity.fields.itervalues():
            value = getattr(args, field.name)
            if value is None:
                continue
            if value.startswith('\\~') or value.startswith('\\%'):
                value = query.Equals(value[1:])
            elif value.startswith('~'):
                value = query.RegexpMatch(value[1:])
            elif value.startswith('%'):
                value = query.SubstringMatch(value[1:])
            else:
                value = query.Equals(value)
            qargs[field.name] = value
        return query.Query(**qargs)

    def run(self, conn, entity, args):
        objects = conn.find(entity.name, self._get_query(entity, args))
        self.view.pprint(objects)


class DeleteAction(Action):
    """Delete a specific instance."""

    name = 'del'

    def __init__(self, entity, parser):
        parser.add_argument('name', metavar='NAME')

    def run(self, conn, entity, args):
        conn.delete(entity.name, args.name)


class AuditAction(object):
    """Query audit logs (a top-level action)."""

    name = 'audit'
    descr = 'query audit logs'
    view = JsonPlain
    
    AUDIT_ATTRS = ('entity', 'object', 'user', 'op')

    @classmethod
    def set_view(cls, viewclass):
        cls.view = viewclass
    
    def __init__(self, parser):
        for attr in self.AUDIT_ATTRS:
            parser.add_argument('--' + attr)
            
    def run(self, conn, entity, args):
        query = dict((x, getattr(args, x))
                     for x in self.AUDIT_ATTRS
                     if getattr(args, x))
        log.info('audit query: %s', query)
        self.view.pprint(list(conn.get_audit(query)))

class DumpAction(object):
    """Dumps all configdb data to a file"""

    name = 'dump'
    descr = 'dump configdb data data to file'


    def __init__(self, parser):
        parser.add_argument('file')

    def run(self, conn, entity, args):
        d = backup.Dumper(conn)
        with open(args.file, 'w') as fd:
            d.dump(fd)
        log.info("Dump completed to %s",args.file)

class LoadAction(object):
    name = 'load'
    descr = 'loads configdb data from file'

    def __init__(self, parser):
        parser.add_argument('file')

    def run(self, conn, entity, args):
        d = backup.Dumper(conn)
        with open(args.file, 'r') as fd:
            d.restore(fd)
        log.info("Load completed")

class Parser(object):

    actions = (
        CreateAction,
        DeleteAction,
        UpdateAction,
        GetAction,
        FindAction,
        TimestampAction
        )

    toplevel_actions = (
        AuditAction,
        DumpAction,
        LoadAction
        )

    def __init__(self, schema, **kw):
        self.schema = schema
        self.parser = self._create_parser(**kw)
        self.parser.add_argument('--url',
                                 default='http://localhost:8230')
        self.parser.add_argument('--user')
        self.parser.add_argument('--auth-store', dest='auth_store',
                                 default='~/.configdb.auth')
        self.parser.add_argument('--no-auth-store', dest='no_auth_store',
                                 action='store_true')
        self.parser.add_argument('--debug', action='store_true')
    

    def _init_subparser(self, entity, parser):
        subparsers = parser.add_subparsers(
            title='action',
            help='use with --help for additional help',
            dest='_action_name')
        for action_class in self.actions:
            descr = re.split(r'\s{2,}', action_class.__doc__)[0]
            subparser = subparsers.add_parser(action_class.name,
                                              help=descr)
            action = action_class(entity, subparser)
            subparser.set_defaults(_action=action)

    def _create_parser(self, **kw):
        parser = argparse.ArgumentParser(**kw)
        subparsers = parser.add_subparsers(
            title='entity',
            help='use with --help for additional help',
            dest='_entity_name')
        for entity in self.schema.get_entities():
            if entity.name in self.schema.sys_schema_tables:
                continue
            subparser = subparsers.add_parser(entity.name,
                                              help=entity.description)
            self._init_subparser(entity, subparser)
            subparser.set_defaults(_entity=entity)
        for action_class in self.toplevel_actions:
            subparser = subparsers.add_parser(action_class.name,
                                              help=action_class.descr)
            action = action_class(subparser)
            subparser.set_defaults(_action=action, _entity=None)
        return parser

    def run(self, input_args):
        args = self.parser.parse_args(input_args)
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)

        auth_file = (os.path.expanduser(args.auth_store)
                     if not args.no_auth_store else None)
        conn = connection.Connection(args.url, self.schema,
                                     username=args.user,
                                     auth_file=auth_file)
        args._action.run(conn, args._entity, args)


def _die(*args):
    logging.error(*args)
    return 1


def main(args=None):
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)s: %(message)s')

    schema_file = os.getenv('SCHEMA_FILE')
    if not schema_file:
        return _die('The SCHEMA_FILE environment variable is not set, '
                    'please point it at your JSON schema file.')
    try:
        with open(schema_file, 'r') as fd:
            schema_json = fd.read()
    except IOError, e:
        return _die('Could not read schema file: %s', e)

    try:
        parser = Parser(schema.Schema(schema_json))
    except ValueError, e:
        return _die('Syntax error in the JSON schema file: %s: %s',
                    schema_file, e)
    except exceptions.SchemaError, e:
        return _die('Schema validation error: %s', e)

    try:
        parser.run(args)
    except Exception, e:
        return _die(e)

    return 0


if __name__ == '__main__':
    sys.exit(main())
