# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
# Copyright 2019 The fiowebviewer Authors. All rights reserved.

import datetime
import os
import tempfile
from collections import (
    namedtuple,
)
from shutil import (
    copytree,
    rmtree,
)

import pytest
from sqlalchemy import (
    create_engine,
)
from sqlalchemy.ext.declarative import (
    declarative_base,
)
from sqlalchemy.orm import (
    sessionmaker,
)

from fiowebviewer.engine.run import fio_webviewer
from fiowebviewer.engine import (
    api,
    database,
    models,
    view,
)
from fiowebviewer.engine.database import (
    Result,
    Tag,
)
from fiowebviewer.engine.models import (
    FioResultComparator,
)

TEST_PATH = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope="session")
def temp_path(request):
    temp = tempfile.mkdtemp()

    def cleanup():
        rmtree(temp)
    request.addfinalizer(cleanup)
    return temp


@pytest.fixture(scope="session")
def temp_path_with_data(request, temp_path):
    tmp_data_path = os.path.join(temp_path, 'data')
    os.mkdir(tmp_data_path)
    view.DATA_PATH = tmp_data_path
    models.DATA_PATH = tmp_data_path
    api.DATA_PATH = tmp_data_path
    return tmp_data_path


@pytest.fixture
def app(request):
    app = fio_webviewer
    app.testing = True
    return app


@pytest.fixture
def client(request, app):
    client = app.test_client()
    return client


@pytest.fixture
def session(request, temp_path):
    DATABASE = 'sqlite:///{}/database.db'.format(temp_path)
    engine = create_engine(DATABASE, echo=True)
    Base = declarative_base()
    Base.metadata.bind = engine
    database.Base.metadata.create_all(engine)
    DBSession = sessionmaker(bind=engine)
    # Mocking session in view and models so they point to tests' database
    view.DBSession = DBSession
    models.DBSession = DBSession
    api.DBSession = DBSession

    def cleanup():
        database.Base.metadata.drop_all(engine)
    request.addfinalizer(cleanup)

    return DBSession()


@pytest.fixture
def copy_sample_data(request, temp_path_with_data):
    sample_data_dir = os.path.join(TEST_PATH, 'samples')
    for child_dir in sorted(os.listdir(sample_data_dir)):
        sample_data_dir_child = os.path.join(temp_path_with_data, child_dir)
        child_dir_file_path = os.path.join(sample_data_dir, child_dir)
        copytree(child_dir_file_path, sample_data_dir_child)
    yield
    for child_dir in sorted(os.listdir(temp_path_with_data)):
        child_dir_file_path = os.path.join(temp_path_with_data, child_dir)
        rmtree(child_dir_file_path)

    def remove_sample_data():
        for child_dir in sorted(os.listdir(temp_path_with_data)):
            child_dir_file_path = os.path.join(temp_path_with_data, child_dir)
            rmtree(child_dir_file_path)
    request.addfinalizer(remove_sample_data)


@pytest.fixture
def database_with_results_only(request, temp_path_with_data, copy_sample_data,
                               session):
    for directory in sorted(os.listdir(temp_path_with_data)):
        fio_date_submitted_file = os.path.join(temp_path_with_data, directory,
                                               'date_submitted')
        with open(fio_date_submitted_file) as f:
            date_submitted = f.read()
            date_submitted = date_submitted.strip()
        new_result = Result(date_submitted=datetime.datetime.strptime(
            date_submitted, '%Y-%m-%dT%H.%M.%S'))
        session.add(new_result)
    session.commit()


@pytest.fixture
def database_with_names(request, temp_path_with_data, copy_sample_data,
                        session):
    for directory in sorted(os.listdir(temp_path_with_data)):
        fio_date_submitted_file = os.path.join(temp_path_with_data, directory,
                                               'date_submitted')
        with open(fio_date_submitted_file) as f:
            date_submitted = f.read()
            date_submitted = date_submitted.strip()
        new_result = Result(date_submitted=datetime.datetime.strptime(
            date_submitted, '%Y-%m-%dT%H.%M.%S'))
        session.add(new_result)
        fio_name_file = os.path.join(temp_path_with_data, directory,
                                     'fio-webviewer.name')
        with open(fio_name_file) as f:
            fio_name = f.read()
            new_result.name = fio_name.strip()
            session.commit()


@pytest.fixture
def database_with_tags(request, temp_path_with_data, copy_sample_data,
                       session):
    for directory in sorted(os.listdir(temp_path_with_data)):
        fio_date_submitted_file = os.path.join(temp_path_with_data, directory,
                                               'date_submitted')
        with open(fio_date_submitted_file) as f:
            date_submitted = f.read()
            date_submitted = date_submitted.strip()
        new_result = Result(date_submitted=datetime.datetime.strptime(
            date_submitted, '%Y-%m-%dT%H.%M.%S'))
        session.add(new_result)
        fio_tags_file = os.path.join(temp_path_with_data, directory,
                                     'fio-webviewer.tags')
        with open(fio_tags_file) as f:
            for line in f.readlines():
                new_tag = Tag(tag=line.strip(), result=new_result)
                session.add(new_tag)
            session.commit()


@pytest.fixture
def fio_comparator():
    return FioResultComparator()


@pytest.fixture()
def percentage_difference(request, fio_comparator):
    dividend, divisor = request.param
    return fio_comparator._get_percentage_difference(dividend,
                                                     divisor)


@pytest.fixture()
def state(request, fio_comparator):
    key, percentage_difference = request.param
    return fio_comparator._get_state(key, percentage_difference)


@pytest.fixture
def values(request, fio_comparator):
    key, selected_value, referenced_value = request.param
    return fio_comparator._get_values(key, selected_value, referenced_value)


@pytest.fixture
def reports_to_compare(temp_path_with_data):
    Point = namedtuple('results_to_compare', 'selected referenced')
    all_fio_results = view.get_all_fio_results(temp_path_with_data)
    selected = all_fio_results[0].group_reports[0]
    referenced = all_fio_results[1].group_reports[0]
    return Point(selected=selected, referenced=referenced)


@pytest.fixture
def compare_result(fio_comparator, reports_to_compare):
    return fio_comparator.compare(reports_to_compare.selected,
                                  reports_to_compare.referenced)
