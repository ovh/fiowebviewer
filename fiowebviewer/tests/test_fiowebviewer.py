# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
# Copyright 2019 The fiowebviewer Authors. All rights reserved.

import os

import pytest
import requests

from fiowebviewer.engine import (
    view,
)
from fiowebviewer.engine.database import (
    Result,
)
from fiowebviewer.engine.models import (
    FioResult,
)


def test_fio_result_command_input_output(app, client,
                                         database_with_results_only,
                                         temp_path_with_data):
    all_fio_results = view.get_all_fio_results(temp_path_with_data)
    for fio_result in all_fio_results:
        detail_path = '/summary/{}'.format(fio_result.dir_name)
        response = client.get(detail_path)
        assert 'id="fio-input"' in str(response.data)
        assert 'id="fio-output"' in str(response.data)


def test_main_page_no_results(app, client, temp_path_with_data, session):
    response = client.get('/')
    status = response.status_code
    assert status == requests.codes.ok
    assert "type=\"checkbox\"" not in str(response.data)
    assert len(os.listdir(temp_path_with_data)) == 0


def test_main_page_with_results(app, client, temp_path_with_data,
                                database_with_results_only):
    response = client.get('/')
    status = response.status_code
    assert status == requests.codes.ok
    assert "type=\"checkbox\"" in str(response.data)
    assert len(os.listdir(temp_path_with_data)) != 0


@pytest.mark.parametrize("request_scheme,domain", [
    ("http", "example.com"),
    ("https", "example.net"),
    ("http", "localhost"),
])
def test_fio_webviewer_sh_script(app, client, request_scheme, domain):
    base_url = "{}://{}/".format(request_scheme, domain)
    response = client.get('/fio-webviewer.sh', base_url)
    assert response.status_code == requests.codes.ok
    assert "fio" in str(response.data)
    assert response.content_type == "application/x-shellscript"
    assert base_url in str(response.data)


@pytest.mark.parametrize("fio_name", [
    ("Testname1"),
    ("Testname2"),
])
def test_names(app, client, fio_name, database_with_names):
    response = client.get('/')
    assert fio_name in str(response.data)


@pytest.mark.parametrize("fio_tag", [
    ("test1"),
    ("test1 with space"),
    ("test2"),
    ("test2 with space"),
])
def test_tags(app, client, fio_tag, database_with_tags):
    response = client.get('/')
    assert fio_tag in str(response.data)


@pytest.mark.parametrize("fio_name", [
    ("Testname1"),
    ("Testname2"),
])
def test_fio_name(app, client, fio_name, temp_path_with_data,
                  database_with_names):
    all_fio_names = [fio_result.fio_name for fio_result in
                     view.get_all_fio_results(temp_path_with_data)]
    assert fio_name in all_fio_names


def test_compare_no_result_selected(app, client, database_with_names):
    response = client.get('/compare?compare=Compare+selected')
    assert response.status_code == 400
    assert "Bad Request" in str(response.data)


def test_delete_no_result_selected(app, client, database_with_names):
    response = client.get('/compare?delete=Yes')
    assert response.status_code == 302


@pytest.mark.parametrize("fio_result_ids", [
    ("1"),
    ("2"),
    (("1", "2")),
])
def test_delete_result_selected(app, client, fio_result_ids, session,
                                temp_path_with_data, database_with_tags):
    base_url = "/compare?delete=Yes"
    for fio_result_id in fio_result_ids:
        base_url += "&result={}".format(fio_result_id)
    response = client.get(base_url)
    assert response.status_code == 302
    for fio_result_id in fio_result_ids:
        assert not session.query(Result).filter(Result.id ==
                                                fio_result_id).count()
        assert not os.path.exists(os.path.join(temp_path_with_data,
                                  fio_result_id))


@pytest.mark.parametrize("fio_result_id", [
    ("1"),
    ("2"),
])
def test_fio_result_navigation(app, client, database_with_tags,
                               fio_result_id, temp_path_with_data):
    response = client.get("/summary/{}".format(fio_result_id))
    assert response.status_code == requests.codes.ok
    fio_result = FioResult(temp_path_with_data, fio_result_id)
    group_size = len(fio_result.group_reports)
    group_shown = "#READ{}".format(group_size - 1)
    assert group_shown in str(response.data)


@pytest.mark.parametrize("fio_result_id", [
    ("1"),
    ("2"),
])
def test_fio_result_table(app, client, database_with_tags, fio_result_id,
                          temp_path_with_data):
    response = client.get("/summary/{}".format(fio_result_id))
    assert response.status_code == requests.codes.ok
    fio_result = FioResult(temp_path_with_data, fio_result_id)
    group_size = len(fio_result.group_reports)
    group_shown_size = "id=\"READ{}\"".format(group_size - 1)
    assert group_shown_size in str(response.data)


@pytest.mark.parametrize("fio_result_id", [
    ("1"),
    ("2"),
])
def test_fio_result_job_select(app, client, database_with_tags,
                               fio_result_id, temp_path_with_data):
    response = client.get("/summary/{}/detailed".format(fio_result_id))
    assert response.status_code == requests.codes.ok
    fio_result = FioResult(temp_path_with_data, fio_result_id)
    result_local = 0
    for group_report in fio_result.group_reports:
        result_local += len(group_report.jobs)
    result_generated = str(response.data).count("type=\"checkbox\"")
    assert result_generated == result_local


@pytest.mark.parametrize("fio_result_ids", [
    ("1"),
    ("2"),
    (("1", "2")),
])
def test_fio_compare_table(app, client, database_with_tags, fio_result_ids,
                           temp_path_with_data):
    base_url = "/compare?compare=Compare+selected"
    for fio_result_id in fio_result_ids:
        base_url += "&result={}".format(fio_result_id)
    response = client.get(base_url)
    assert response.status_code == requests.codes.ok
    results_local = 0
    for fio_result_id in fio_result_ids:
        fio_result = FioResult(temp_path_with_data, fio_result_id)
        results_local += len(fio_result.group_reports)
    # -1 because entry in css
    results_generated = str(response.data).count("table-head") - 1
    assert results_generated == results_local
