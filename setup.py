#!/usr/bin/python

from setuptools import setup, find_packages

setup(
  name='admdb',
  version='0.1',
  description='database framework for configuration info',
  author='ale',
  author_email='ale@incal.net',
  url='http://git.autistici.org/p/admdb',
  install_requires=['Flask', 'inflect', 'SQLAlchemy>0.7'],
  setup_requires=[],
  zip_safe=True,
  packages=find_packages(),
  entry_points={
    'console_scripts': [
      'admdb-http-api = admdb.server.wsgiapp:main',
      'admdb-cli = admdb.client.cli:main',
    ],
  },
  )

