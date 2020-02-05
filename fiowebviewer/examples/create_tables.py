#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
# Copyright 2019 The fiowebviewer Authors. All rights reserved.

import argparse

from sqlalchemy import (
    create_engine,
)

from fiowebviewer import (
    application,
)
from fiowebviewer.engine import (
    database,
)

DATABASE = application.config['DATABASE']

engine = create_engine(DATABASE, echo=True)

parser = argparse.ArgumentParser()
parser.add_argument('--drop', help='drop existing tables', action='store_true',
                    default=False)

args = parser.parse_args()

if args.drop:
    database.Base.metadata.drop_all(engine)
database.Base.metadata.create_all(engine)
