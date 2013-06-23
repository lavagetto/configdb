try:
    from configdb.db.interface import leveldb_interface
except ImportError:
    from nose.exc import SkipTest
    raise SkipTest('LevelDB not found')

from configdb.tests import *
from configdb.tests.wsgiapp_complex_test_base import WsgiComplexTestBase


class WsgiComplexLevelDbTest(WsgiComplexTestBase, WsgiTestBase):

    def setUp(self):
        WsgiTestBase.setUp(self)
        WsgiComplexTestBase.setUp(self)

    def get_app_args(self):
        return {'DB_DRIVER': 'leveldb',
                'DB_URI': self._tmpdir + '/db'}


    
    
