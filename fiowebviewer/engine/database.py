# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
# Copyright 2019 The fiowebviewer Authors. All rights reserved.

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (
    relationship,
    sessionmaker,
)
from sqlalchemy.schema import ForeignKey

from fiowebviewer.engine.run import fio_webviewer

DATABASE = fio_webviewer.config['DATABASE']

engine = create_engine('{}?check_same_thread=False'.format(DATABASE), echo=False)
Base = declarative_base()
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)


class Result(Base):
    __tablename__ = 'results'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=True)
    date_submitted = Column(DateTime, nullable=False)

    def __repr__(self):
        return self.date_submitted


class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    tag = Column(String, nullable=False)
    result_id = Column(Integer, ForeignKey("results.id"), nullable=False)
    result = relationship(Result)

    def __repr__(self):
        return self.tag
