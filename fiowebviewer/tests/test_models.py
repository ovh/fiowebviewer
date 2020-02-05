# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
# Copyright 2019 The fiowebviewer Authors. All rights reserved.

import numbers

import pytest

from fiowebviewer.engine import (
    models,
)

ROUNDING_RANGE = models.ROUNDING_RANGE


@pytest.mark.parametrize("percentage_difference, result", [
    ((0, 0), 0),
    ((1, 0), 100),
    ((3, 5), -40),
    ((6, 7), -14.285714285714292),
    ((13, 13), 0),
    ((12, 14), -14.285714285714292),
    ((27, 15), 80),
    ((2.34, 4.67), -49.892933618843685),
    ((7.89, 5.67), 39.15343915343914),
    ((12.12, 40.23), -69.87322893363162),
    ((34.67, 23.22), 49.31093884582259)
], indirect=["percentage_difference"])
def test_fio_result_comparator_get_percentage_difference(
        result,
        percentage_difference):
    assert round(result, ROUNDING_RANGE) == percentage_difference


@pytest.mark.parametrize("state, result", [
    (("lat", 0), "neutral"),
    (("test_cpu", 10), "negative"),
    (("bw_test", -10), "negative"),
    (("test_io_test", 0), "neutral"),
    (("testlat", 0.0000001), "negative"),
    (("cputest", -0.0000001), "positive"),
    (("testbwtest", 0), "neutral"),
], indirect=["state"])
def test_fio_result_comparator_get_state(result, state):
    assert state == result


@pytest.mark.parametrize(
    "values, subtraction_result, percentage_difference_result, state_result", [
        (("lat", 0, 0), 0, 0, "neutral"),
        (("test_cpu", 1, 0), 1, 100, "negative"),
        (("bw_test", 3, 5), -2, -40, "negative"),
        (("testlat", 13, 13), 0, 0, "neutral"),
        (("cputest", 12, 14), -2, -14.285714285714292, "positive"),
        (("test_io_test", 7.89, 5.67), 2.2199999999999998, 39.15343915343914,
            "positive"),
        (("testbwtest", 12.12, 40.23), -28.11, -69.87322893363162, "negative")
    ], indirect=["values"]
)
def test_fio_result_comparator_get_values(subtraction_result,
                                          percentage_difference_result,
                                          state_result,
                                          values):
    # Test subtraction
    assert round(subtraction_result,
                 ROUNDING_RANGE) == values.subtraction
    assert round(percentage_difference_result,
                 ROUNDING_RANGE) == values.percentage_difference
    # Test state
    assert state_result == values.state


def test_fio_result_comparator_compare(database_with_results_only,
                                       temp_path_with_data,
                                       fio_comparator,
                                       reports_to_compare,
                                       compare_result):
    # Test FioResultDiff object values
    for key, value in compare_result.__dict__.items():
        if not isinstance(value, dict):
            # Initialize compare data
            selected_value = reports_to_compare.selected.__dict__[key]
            referenced_value = reports_to_compare.referenced.__dict__[key]
            # Test subtraction
            assert isinstance(value.subtraction, numbers.Number)
            assert round((selected_value - referenced_value),
                         ROUNDING_RANGE) == value.subtraction
            # Test percentage_difference
            assert isinstance(value.percentage_difference, numbers.Number)
            if referenced_value != 0:
                percentage_difference = round((
                    float(selected_value) /
                    float(referenced_value) * 100 - 100), ROUNDING_RANGE
                )
                assert percentage_difference == round(
                    value.percentage_difference,
                    ROUNDING_RANGE
                )
            else:
                percentage_difference = round((float(selected_value) * 100),
                                              ROUNDING_RANGE)
                assert percentage_difference == round(
                    value.percentage_difference,
                    ROUNDING_RANGE
                )
            # Test state
            if "lat" in key or "cpu" in key:
                if percentage_difference == 0:
                    assert "neutral" == value.state
                elif percentage_difference > 0:
                    assert "negative" == value.state
                else:
                    assert "positive" == value.state
            elif "bw" in key or "io" in key or "runtime" in key:
                if percentage_difference == 0:
                    assert "neutral" == value.state
                elif percentage_difference > 0:
                    assert "positive" == value.state
                else:
                    assert "negative" == value.state

        else:
            for inner_key, inner_value in value.items():
                # Initialize compare data
                selected_value = reports_to_compare.selected.__dict__[
                    key
                ][inner_key]
                referenced_value = reports_to_compare.referenced.__dict__[
                    key
                ][inner_key]
                # Test subtraction
                assert isinstance(inner_value.subtraction, numbers.Number)
                assert round((selected_value - referenced_value),
                             ROUNDING_RANGE) == inner_value.subtraction
                # Test percentage_difference
                assert isinstance(
                    inner_value.percentage_difference,
                    numbers.Number
                )
                if referenced_value != 0:
                    percentage_difference = round((
                        float(selected_value) /
                        float(referenced_value) * 100 - 100), ROUNDING_RANGE
                    )
                    assert percentage_difference == round(
                        inner_value.percentage_difference,
                        ROUNDING_RANGE
                    )
                else:
                    percentage_difference = round((
                        float(selected_value) * 100),
                        ROUNDING_RANGE
                    )
                    assert percentage_difference == round(
                        inner_value.percentage_difference,
                        ROUNDING_RANGE
                    )
                # Test state
                if "lat" in key or "cpu" in key:
                    if percentage_difference == 0:
                        assert "neutral" == inner_value.state
                    elif percentage_difference > 0:
                        assert "negative" == inner_value.state
                    else:
                        assert "positive" == inner_value.state
                elif "bw" in key or "io" in key or "runtime" in key:
                    if percentage_difference == 0:
                        assert "neutral" == inner_value.state
                    elif percentage_difference > 0:
                        assert "positive" == inner_value.state
                    else:
                        assert "negative" == inner_value.state
