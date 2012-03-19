from admdb.tests import *
from admdb.db.interface import sa_generator


class SqlAlchemyGeneratorTest(TestBase):

    def test_generate(self):
        schema = self.get_schema()
        sagen = sa_generator.SqlAlchemyGenerator(schema)
        result = sagen.generate()
        self.assertTrue(isinstance(result, basestring))
        self.assertTrue(len(result) > 0)
