import cookielib
import getpass
import json
import logging
import os
import sys
import urllib
import urllib2
from configdb import exceptions

log = logging.getLogger(__name__)


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
        self._schema = schema
        self._url = url.rstrip('/')
        self._cj = cookielib.MozillaCookieJar()
        self._auth_file = auth_file
        if auth_file and os.path.exists(auth_file):
            self._cj.load(self._auth_file)
        self._username = username or getpass.getuser()
        self._password = password
        self._opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self._cj))

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
            if os.isatty(sys.stdin):
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
                self._cj.save(self._auth_file)
            except Exception, e:
                log.warn('Could not save session state to %s: %s',
                         self._auth_file, e)
            os.umask(old_umask)

    def create(self, entity_name, data):
        return self._call(entity_name, 'create', data=data)

    def delete(self, entity_name, object_name):
        return self._call(entity_name, 'delete', object_name)

    def find(self, entity_name, query):
        return [self._from_net(entity_name, x)
                for x in self._call(entity_name, 'find', data=query)]

    def get(self, entity_name, object_name):
        return self._from_net(
            entity_name,
            self._call(entity_name, 'get', object_name))

    def update(self, entity_name, object_name, data):
        return self._call(entity_name, 'update', object_name, data)
