#!/usr/bin/python
# -*- coding: utf-8 -*-
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
# Copyright 2019 The fiowebviewer Authors. All rights reserved.

import logging
import os
from logging.handlers import (
    RotatingFileHandler,
)

from flask import (
    Flask,
)

__version__ = '1.0.0'

ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(
    os.path.abspath(__file__)), os.pardir))

template_path = os.path.join(ROOT_PATH, 'templates')
static_path = os.path.join(ROOT_PATH, 'static')

fio_webviewer = Flask(__name__,
                      template_folder=template_path, static_folder=static_path)

fio_webviewer.config.from_envvar('FIOWEBVIEWER_SETTINGS', silent=True)

file_handler = RotatingFileHandler(
    fio_webviewer.config['ERROR_LOG'],
    maxBytes=1024 * 1024 * 100,
    backupCount=20
)
file_handler.setLevel(logging.ERROR)

from fiowebviewer.engine.api import *
from fiowebviewer.engine.view import *

if __name__ == '__main__':
    fio_webviewer.debug = True
    fio_webviewer.run(host='0.0.0.0')
else:
    application = fio_webviewer


logger = application.logger
logger.setLevel(logging.ERROR)
logger.addHandler(file_handler)
