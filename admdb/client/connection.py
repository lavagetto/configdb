import json
import logging
import urllib
import urllib2
from admdb import exceptions

log = logging.getLogger(__name__)


class Connection(object):

    def __init__(self, url):
        self._url = url.rstrip('/')
        self._opener = urllib2.build_opener()

    def _request(self, path, data=None):
        """Perform a HTTP request.

        POST requests contain JSON-encoded data, with a Content-Type
        of 'application/json'.

        Raises:
          exceptions.RpcError
        """
        url = '%s/%s' % (
            self._url,
            '/'.join(urllib.quote(x, '') for x in path))
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
        except urllib2.URLError, e:
            raise exceptions.RpcError(str(e))

    def create(self, class_name, data):
        return self._request(['create', class_name], data)

    def delete(self, class_name, object_name):
        return self._request(['delete', class_name, object_name])

    def find(self, class_name, query):
        return self._request(['find', class_name], query)

    def get(self, class_name, object_name):
        return self._request(['get', class_name, object_name])

    def update(self, class_name, object_name, data):
        return self._request(['update', class_name, object_name], data)
