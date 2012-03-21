import argparse
import getpass
import inflect
import logging
import re
import os
from admdb.db import schema
from admdb.client import connection

log = logging.getLogger(__name__)
pl = inflect.engine()


def read_password(value):
    return getpass.getpass(prompt='Password: ')


def read_from_file(value):
    with open(value, 'r') as fd:
        return fd.read()


class Action(object):

    def parse_field_value(self, field, value):
        type_map = {
            'string': str,
            'int': int,
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
        has_relations = None
        for field in entity.fields.itervalues():
            descr = field.attrs.get('description', '')
            if field.is_relation():
                opt_name = '--%s' % pl.singular_noun(field.name)
                descr += '%s(use with --add / --delete)' % (
                    ' ' if descr else '')
                parser.add_argument(opt_name, help=descr,
                                    dest=field.name)
                has_relations = True
            else:
                opt_name = '--%s' % field.name
                parser.add_argument(opt_name, help=descr,
                                    dest=field.name)
        if has_relations:
            parser.add_argument('--add', action='store_true')
            parser.add_argument('--delete', action='store_true')

    def run(self, conn, entity, args):
        if args.add and args.delete:
            raise Exception('Can\'t specify --add and --delete together')

        log.info('update: %s/%s', entity.name, args._name)
        obj = conn.get(entity.name, args._name)
        update_data = {}
        for field in entity.fields.itervalues():
            value = getattr(args, field.name)
            if value is None:
                continue
            if field.is_relation():
                if not value:
                    raise Exception('Relational argument "%s" is empty' % (
                            field.name,))
                rel_list = set(obj[field.name])
                if args.add:
                    rel_list.add(value)
                elif args.delete:
                    rel_list.discard(value)
                else:
                    raise Exception('Specified relational attribute without '
                                    '--add or --delete')
                update_data[field.name] = list(rel_list)
            else:
                # Auto-clear items.
                if not value:
                    value = None
                update_data[field.name] = value

        log.info('update: %s', update_data)
        conn.update(entity.name, args._name, update_data)


class GetAction(Action):
    """Get a specific instance."""

    name = 'get'

    def __init__(self, entity, parser):
        parser.add_argument('_name', metavar='NAME')

    def run(self, conn, entity, args):
        obj = conn.get(entity.name, args._name)
        print obj


class FindAction(Action):
    """Find instances."""

    name = 'find'

    def __init__(self, entity, parser):
        self.add_standard_entity_fields(entity, parser)

    def run(self, conn, entity, args):
        query = self.get_standard_entity_fields(entity, parser)
        objects = conn.find(entity.name, query)


class DeleteAction(Action):
    """Delete a specific instance."""

    name = 'del'

    def __init__(self, entity, parser):
        parser.add_argument('name', metavar='NAME')

    def run(self, conn, entity, args):
        conn.delete(entity.name, args.name)


class Parser(object):

    actions = (
        CreateAction,
        DeleteAction,
        UpdateAction,
        GetAction,
        FindAction)

    def __init__(self, schema, **kw):
        self.schema = schema
        self.parser = self._create_parser(**kw)
        self.parser.add_argument('--url',
                                 default='http://localhost:8230')

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
            subparser = subparsers.add_parser(entity.name,
                                              help=entity.description)
            self._init_subparser(entity, subparser)
            subparser.set_defaults(_entity=entity)
        return parser

    def run(self, input_args):
        args = self.parser.parse_args(input_args)
        conn = connection.Connection(args.url)
        args._action.run(conn, args._entity, args)


def main(args=None):
    logging.basicConfig(level=logging.DEBUG)

    schema_file = os.getenv('SCHEMA', './schema.json')
    with open(schema_file, 'r') as fd:
        schema_json = fd.read()

    parser = Parser(schema.Schema(schema_json))
    parser.run(args)
    return 0


if __name__ == '__main__':
    main()
