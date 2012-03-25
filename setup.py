#!/usr/bin/python

from setuptools import setup, find_packages

setup(
  name='configdb',
  version='0.1',
  description='database framework for configuration info',
  author='ale',
  author_email='ale@incal.net',
  url='http://git.autistici.org/p/configdb',
  install_requires=['argparse', 'Flask', 'formencode', 'inflect',
                    'SQLAlchemy>0.7'],
  setup_requires=[],
  zip_safe=True,
  packages=find_packages(),
  entry_points={
    'console_scripts': [
      'configdb-api-server = configdb.server.wsgiapp:main',
      'configdb-client = configdb.client.cli:main',
    ],
  },
  )

