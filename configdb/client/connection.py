import cookielib
import getpass
import gzip
import json
import logging
import os
import sys
import urllib
import urllib2
import StringIO
from configdb import exceptions
from configdb.client import query

log = logging.getLogger(__name__)


class GzipProcessor(urllib2.BaseHandler):
    """HTTP handler that supports the 'gzip' content encoding."""

    def http_request(self, req):
        req.add_header('Accept-Encoding', 'gzip')
        return req

    def http_response(self, req, resp):
        if resp.headers.get('content-encoding') == 'gzip':
            gz = gzip.GzipFile(
                fileobj=StringIO.StringIO(resp.read()),
                mode='r')
            resp.read = gz.read
        return resp

    https_request = http_request
    https_response = http_response


class Connection(object):
    """Proxy for a remote configdb server.

    We'll use HTTP requests to communicate to the remote server.

    The caller will need to pass authentication parameters (username
    and password), if missing the username will default to the current
    user, and the password will be requested interactively.

    Authentication is handled via session cookies, which can
    optionally be saved in a cookie file for later reuse (so that, in
    the connection lifetime, we can login only once).
    """

    def __init__(self, url, schema, username=None, password=None,
                 auth_file=None):
        """Initialize a new Connection object.

        Args:
          url: string, URL of the remote API endpoint
          schema: configdb.db.schema.Schema, the db schema
          username: string (optional), username for authentication
          password: string (optional), password for authentication
          auth_file: string (optional), file where we will store
            permanent authentication credentials
        """
        self._schema = schema
        self._url = url.rstrip('/')
        self._cj = cookielib.MozillaCookieJar()
        self._auth_file = auth_file
        if auth_file and os.path.exists(auth_file):
            try:
                self._cj.load(self._auth_file,  ignore_discard=True)
            except cookielib.LoadError, e:
                log.warn('Could not save session state to %s: %s',
                         self._auth_file, e)
        self._username = username or getpass.getuser()
        self._password = password
        self._opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self._cj) ,
            GzipProcessor())

    def _request(self, path, data=None, logged_in=False):
        """Perform a HTTP request.

        POST requests contain JSON-encoded data, with a Content-Type
        of 'application/json'.

        Raises:
          exceptions.RpcError
        """
        url = '%s/%s' % (
            self._url,
            '/'.join([urllib.quote(x, safe='') for x in path]))
        if data:
            log.debug('POST: %s %s', url, data)
            request = urllib2.Request(
                url,
                data=json.dumps(data),
                headers={'Content-Type': 'application/json'})
        else:
            log.debug('GET: %s', url)
            request = urllib2.Request(url)
        try:
            response = self._opener.open(request)
            response_data = json.loads(response.read())
            if not response_data.get('ok'):
                raise exceptions.RpcError(response_data['error'])
            return response_data['result']
        except urllib2.HTTPError, e:
            if e.code == 403 and not logged_in:
                self._login()
                return self._request(path, data, logged_in=True)
            raise exceptions.RpcError('HTTP status code %d' % e.code)
        except urllib2.URLError, e:
            raise exceptions.RpcError(str(e))

    def _call(self, entity_name, op, arg=None, data=None):
        entity = self._schema.get_entity(entity_name)
        if not entity:
            raise exceptions.NotFound('No such entity "%s"' % entity_name)
        if data:
            data = entity.to_net(data, ignore_missing=True)
        args = [op, entity_name]
        if arg:
            args.append(arg)
        return self._request(args, data)

    def _from_net(self, entity_name, data):
        return self._schema.get_entity(entity_name).from_net(data)

    def _login(self):
        # Ask for password if possible.
        if self._password is None:
            # Yes this is equivalent to sys.stdin.isatty(), but easier
            # to test with Mox apparently...
            if os.isatty(sys.stdin.fileno()):
                self._password = getpass.getpass()
            else:
                raise exceptions.AuthError('No password provided')
        # Perform login request. Raises RpcError if login fails.
        result = self._request(['login'],
                               {'username': self._username,
                                'password': self._password})
        # If successful, save the auth tokens to file.
        if self._auth_file:
            old_umask = os.umask(077)
            try:
                self._cj.save(self._auth_file, ignore_discard=True)
            except Exception, e:
                log.warn('Could not save session state to %s: %s',
                         self._auth_file, e)
            os.umask(old_umask)

    def create(self, entity_name, data):
        """Create a new object.

        Args:
          entity_name: string, entity name
          data: dict, attributes of the new object

        Returns:
          True on success.

        Raises:
          exceptions.NotFound if the entity does not exist
          exceptions.ValidationError if the data does not pass
          validation.
        """
        return self._call(entity_name, 'create', data=data)

    def delete(self, entity_name, object_name):
        """Delete an object.

        Deleting an object that does not exist is not considered an
        error.

        Args:
          entity_name: string, entity name
          object_name: string, primary key (name) of the object
        """
      
        return self._call(entity_name, 'delete', object_name)

    def find(self, entity_name, data):
        """Perform a query.

        The 'query' argument should represent a valid query. It should
        be a dictionary whose keys are entity attribute names, and
        whose values are query criteria. A query criteria can be
        expressed either in its raw dictionary form, or as a class in
        the configdb.client.query module.

        Args:
          entity_name: string, entity name
          data: query data

        Returns:
          A list of database objects.

        Raises:
          exceptions.NotFound if the entity does not exist
        """
        if isinstance(data, query.Query):
            data = data.to_net()
        return [self._from_net(entity_name, x)
                for x in self._call(entity_name, 'find', data=data)]

    def get(self, entity_name, object_name):
        """Fetch a single object.

        Args:
          entity_name: string, entity name
          object_name: string, primary key (name) of the object

        Returns:
          A database object.

        Raises:
          exceptions.NotFound if the object or entity do not exist.
        """
        return self._from_net(
            entity_name,
            self._call(entity_name, 'get', object_name))

    def update(self, entity_name, object_name, data):
        """Update the contents of an object.

        Args:
          entity_name: string, entity name
          object_name: string, primary key (name) of the object
          data: dict, attributes of the new object

        Returns:
          True on success.

        Raises:
          exceptions.NotFound if the object does not exist.
          exceptions.ValidationError if the new data does not pass
          validation.
        """
        return self._call(entity_name, 'update', object_name, data)

    def get_audit(self, query):
        """Query the audit log.

        Args:
          query: dict, query criteria

        Returns:
          A list of audit objects (dictionaries).
        """
        return self._request(['audit'], query)

