# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
# Copyright 2019 The fiowebviewer Authors. All rights reserved.

import json

import pytest


@pytest.mark.parametrize("result_id, result_name, logtypes", [
    ("1", "Testname1", ['bw', 'iops', 'lat', 'slat', 'clat']),
    ("2", "Testname2", ['bw', 'iops', 'lat', 'slat', 'clat']),
])
def test_api_get_name_and_types(app, client, result_id, result_name, logtypes,
                                temp_path_with_data, database_with_names):
    response = client.get('/api/{}'.format(result_id))
    response_dict = json.loads(response.data.decode())
    assert result_name == response_dict['name']
    for logtype in logtypes:
        assert logtype in response_dict['jobs'][result_id]


@pytest.mark.parametrize("result_id, name", [
    ("1", "Test"),
    ("2", "Test with space"),
])
def test_api_put_valid_name(app, client, result_id, name, temp_path_with_data,
                            database_with_names):
    response = client.put('/api/{}'.format(result_id),
                          content_type="application/json",
                          data=json.dumps({"name": name}))
    assert response.status_code == 200
    response = client.get('/api/{}'.format(result_id))
    response_dict = json.loads(response.data.decode())
    assert response_dict['name'] == name


@pytest.mark.parametrize("result_id", [
    ("1"),
    ("2"),
])
def test_api_put_invalid_name(app, client, result_id, temp_path_with_data,
                              database_with_names):
    # PUT intentionally invalid content type
    response = client.put('/api/{}'.format(result_id),
                          content_type="text/plain",
                          data=json.dumps({"name": "Test"}))
    assert response.status_code == 400
    # PUT intentionally empty data
    response = client.put('/api/{}'.format(result_id),
                          content_type="text/plain",
                          data="data=someinvalid;string")
    assert response.status_code == 400


@pytest.mark.parametrize("result_id, log_type, start_frame, end_frame,\
                         granularity, iotype", [
    ("1", "bw", 0, 15226, "1S", "read"),
    ("1", "iops", 7000, 15226, "2S", "read"),
    ("1", "lat", 0, 7000, "3S", "read"),
    ("1", "slat", 0, 15226, "4S", "read"),
    ("1", "clat", 0, 15226, "5S", "read"),
    ("2", "bw", 0, 30234, "1S", "read"),
    ("2", "iops", 7000, 30234, "2S", "read"),
    ("2", "lat", 0, 15000, "3S", "read"),
    ("2", "slat", 0, 15226, "4S", "read"),
    ("2", "clat", 0, 15226, "5S", "read"),
    ("1", "bw", 0, 15226, "1S", "write"),
    ("1", "iops", 7000, 15226, "2S", "write"),
    ("1", "lat", 0, 7000, "3S", "write"),
    ("1", "slat", 0, 15226, "4S", "write"),
    ("1", "clat", 0, 15226, "5S", "write"),
    ("2", "bw", 0, 30234, "1S", "write"),
    ("2", "iops", 7000, 30234, "2S", "write"),
    ("2", "lat", 0, 15000, "3S", "write"),
    ("2", "slat", 0, 15226, "4S", "write"),
    ("2", "clat", 0, 15226, "5S", "write"),
])
def test_api_json_data_aggregated(app, client, result_id, log_type,
                                  start_frame, end_frame, granularity, iotype,
                                  temp_path_with_data,
                                  database_with_results_only):
    response = client.get('/api/{}/{}.json?start_frame={}&end_frame={}\
            &granularity={}&io_type={}'.format(result_id, log_type,
                                               start_frame, end_frame,
                                               granularity, iotype))
    # this will fail if response cannot be parsed to dict
    json.loads(response.data)
