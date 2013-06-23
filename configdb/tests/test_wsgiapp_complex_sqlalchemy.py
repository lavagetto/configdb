from configdb.tests import *
from configdb.tests.wsgiapp_complex_test_base import WsgiComplexTestBase


class WsgiComplexSQLAlchemyTest(WsgiComplexTestBase, WsgiTestBase):

    def setUp(self):
        WsgiTestBase.setUp(self)
        WsgiComplexTestBase.setUp(self)

    def get_app_args(self):
        return {}
