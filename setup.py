#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import (
    setup,
)

from fiowebviewer.engine.run import (
    __version__,
)


def get_install_requires():
    """
    parse requirements.txt, ignore links, exclude comments
    """
    requirements = []
    for line in open('requirements.txt').readlines():
        # skip to next iteration if comment or empty line
        if line.startswith('#') or line == '' or line.startswith('http') \
                or line.startswith('git'):
            continue
        # add line to requirements
        requirements.append(line)
    return requirements


setup(name='fiowebviewer',
      version=__version__,
      description='Webapp for visualising fio results',
      author='OVH SAS',
      author_email='opensource@ovh.net',
      packages=[
          'fiowebviewer',
          'fiowebviewer.alembic',
          'fiowebviewer.engine',
          'fiowebviewer.examples',
          'fiowebviewer.static',
          'fiowebviewer.templates',
      ],
      install_requires=get_install_requires(),
      package_data={
          'fiowebviewer.static': [
              'bootstrap/css/*',
              'bootstrap/fonts/*',
              'bootstrap/js/*',
              'css/*',
              'js/*'
          ],
          'fiowebviewer.templates': [
              '*.html',
              'fio-webviewer.sh.tmpl',
          ],
          'fiowebviewer.alembic': [
              'alembic.ini',
              'data/script.py.mako',
              'data/env.py',
              'data/versions/*.py',
          ],
          'fiowebviewer.examples': [
              'config.cfg',
              'create_tables.py',
              'fiowebviewer.wsgi',
          ],
      },
)
