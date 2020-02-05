# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
# Copyright 2019 The fiowebviewer Authors. All rights reserved.

import pandas as pd
from flask import (
    Response,
    jsonify,
    request,
    send_file,
)
from pandas.tseries.offsets import Milli
from pint import UnitRegistry
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.exceptions import BadRequest

from fiowebviewer.engine.database import (
    DBSession,
    Result,
)
from fiowebviewer.engine.run import fio_webviewer
from fiowebviewer.engine.models import FioResult

ureg = UnitRegistry()
ureg.default_format = '~'
logger = fio_webviewer.logger
DATA_PATH = fio_webviewer.config['DATA_PATH']


@fio_webviewer.route('/api/<fio_result_id>', methods=['GET', 'PUT'])
def api_fio_result(fio_result_id):
    if request.method == 'GET':
        fio_data = FioResult(DATA_PATH, fio_result_id)
        fio_log_types = {}
        run_time = None
        for fio_group_report in fio_data.group_reports:
            run_time = max(fio_group_report.read_runtime_ms,
                           fio_group_report.write_runtime_ms)
            for job in fio_group_report.jobs:
                fio_log_types[job.job_id] = [log.log_type for log in job.logs
                                             if log.exists]
        fio_result = {
            'runtime': run_time,
            'jobs': fio_log_types,
            'name': fio_data.fio_name,
            'id': fio_data.dir_name,
            'fio-userargs': fio_data.fio_userargs,
            'fio-output': fio_data.fio_output,
        }
        return jsonify(fio_result)
    elif request.method == 'PUT':
        try:
            input_data = request.get_json()
        except BadRequest:
            return "Bad Request", 400  # triggered when input data
                                       # cannot be parsed as json
        try:
            if input_data['name']:
                session = DBSession()
                try:
                    result = session.query(Result).filter(Result.id ==
                                                          fio_result_id).one()
                    result.name = input_data['name']
                except NoResultFound:
                    session.rollback()
                    return "Bad Request", 400
                else:
                    session.commit()
                    return "OK", 200
            return "Bad Request", 400  # triggered when 'name' is empty
        except Exception as e:  # triggered when there is no name in input data
            logger.exception(e)
            return "Bad Request", 400


@fio_webviewer.route('/api/<fio_result_id>/json', methods=['GET'])
def api_fio_result_json(fio_result_id):

    fio_data = FioResult(DATA_PATH, fio_result_id).group_reports
    fio_result = {
        'fio version': fio_data[0].fio_version,
        'jobs': [
            {
                'jobname': job.jobname,
                'groupid': job.group_id,
                'error': job.error,
                'read':
                    {
                        'io_kbytes': job.read_total_io_kb,
                        'bw_bytes': job.read_bw_kbps,
                        'iops': job.read_iops,
                        'runtime': job.read_runtime_ms,
                        'slat_ns':
                            {
                                'min': job.read_submission_lat_min_usec * 2 ** 10,
                                'max': job.read_submission_lat_max_usec * 2 ** 10,
                                'mean': job.read_submission_lat_mean_usec * 2 ** 10,
                                'stddev': job.read_submission_lat_stddev_usec * 2 ** 10,
                            },
                        'clat_ns':
                            {
                                'min': job.read_completion_lat_min_usec * 2 ** 10,
                                'max': job.read_completion_lat_max_usec * 2 ** 10,
                                'mean': job.read_completion_lat_mean_usec * 2 ** 10,
                                'stddev': job.read_completion_lat_stddev_usec * 2 ** 10,
                                'percentile': {key: value * 2 ** 10 for key, value
                                               in job.read_completion_lat_percentiles_usec.items()},
                            },
                        'lat_ns':
                            {
                                'min': job.read_total_lat_min_usec * 2 ** 10,
                                'max': job.read_total_lat_max_usec * 2 ** 10,
                                'mean': job.read_total_lat_mean_usec * 2 ** 10,
                                'stddev': job.read_total_lat_stddev_usec * 2 ** 10,
                            },
                        'bw_min': job.read_bw_min_kbps,
                        'bw_max': job.read_bw_max_kbps,
                        'bw_agg': job.read_bw_aggr_of_total_per,
                        'bw_mean': job.read_bw_mean_kbps,
                        'bw_dev': job.read_bw_stddev_kbps,
                    },
                'write':
                    {
                        'io_kbytes': job.write_total_io_kb,
                        'bw_bytes': job.write_bw_kbps,
                        'iops': job.write_iops,
                        'runtime': job.write_runtime_ms,
                        'slat_ns':
                            {
                                'min': job.write_submission_lat_min_usec * 2 ** 10,
                                'max': job.write_submission_lat_max_usec * 2 ** 10,
                                'mean': job.write_submission_lat_mean_usec * 2 ** 10,
                                'stddev': job.write_submission_lat_stddev_usec * 2 ** 10,
                            },
                        'clat_ns':
                            {
                                'min': job.write_completion_lat_min_usec * 2 ** 10,
                                'max': job.write_completion_lat_max_usec * 2 ** 10,
                                'mean': job.write_completion_lat_mean_usec * 2 ** 10,
                                'stddev': job.write_completion_lat_stddev_usec * 2 ** 10,
                                'percentile': {key: value * 2 ** 10 for key, value
                                               in job.write_completion_lat_percentiles_usec.items()},
                            },
                        'lat_ns':
                            {
                                'min': job.write_total_lat_min_usec * 2 ** 10,
                                'max': job.write_total_lat_max_usec * 2 ** 10,
                                'mean': job.write_total_lat_mean_usec * 2 ** 10,
                                'stddev': job.write_total_lat_stddev_usec * 2 ** 10,
                            },
                        'bw_min': job.write_bw_min_kbps,
                        'bw_max': job.write_bw_max_kbps,
                        'bw_agg': job.write_bw_aggr_of_total_per,
                        'bw_mean': job.write_bw_mean_kbps,
                        'bw_dev': job.write_bw_stddev_kbps,
                    },
                'usr_cpu': job.cpu_user,
                'sys_cpu': job.cpu_system,
                'ctx': job.cpu_context_switches,
                'majf': job.cpu_major_page_faults,
                'minf': job.cpu_minor_page_faults,

                'iodepth_level': job.io_depth_distrib,
                'latency_us': job.io_lat_distrib_usec,
                'latency_ms': job.io_lat_distrib_msec,
            }
            for job in fio_data
        ]

    }
    return jsonify(fio_result)


@fio_webviewer.route('/api/<fio_result_id>/<job_id>/<log_type>.csv',
                     methods=['GET'])
def api_fio_csv(fio_result_id, job_id, log_type):
    io_type = request.args.get('io_type')
    fio_data = FioResult(DATA_PATH, fio_result_id)
    data_buf = fio_data.to_csv(job_id, log_type, io_type)
    csv_string = data_buf.getvalue()
    return Response(csv_string, mimetype='text/csv')


@fio_webviewer.route('/api/<fio_result_id>/targz', methods=['GET'])
def api_fio_targz(fio_result_id):
    fio_data = FioResult(DATA_PATH, fio_result_id)
    return send_file(fio_data.to_tar_gz(), mimetype='application/tar+gzip',
                     as_attachment=True,
                     attachment_filename='{}.tar.gz'.format(fio_data.fio_name))


@fio_webviewer.route('/api/<fio_result_id>/<job_id>/<log_type>.json',
                     methods=['GET'])
def api_fio_json(fio_result_id, job_id, log_type):
    start_frame = request.args.get('start_frame')
    end_frame = request.args.get('end_frame')
    granularity = request.args.get('granularity', '1S')
    io_type = request.args.get('io_type')

    fio_data = FioResult(DATA_PATH, fio_result_id)
    if start_frame and end_frame:
        data_frame = fio_data.to_dataframe(job_id, log_type, io_type)
        if data_frame is None:
            return jsonify(dict(error='404'))
            # return error 404 with
            # html status code 200
            # so we can catch this error
            # directly in frontend
            # without triggering errors.

        data_frame = data_frame[(data_frame.index > Milli(start_frame)) &
                                (data_frame.index < Milli(end_frame))]
        if "iops" not in log_type:
            data_frame[1] = data_frame[1].astype(float).values / 1000
            data_frame[1] = data_frame[1].round(2)
        if granularity:
            data_frame = data_frame.\
                resample(granularity, label='right', closed='right').mean().\
                fillna('None')
        return jsonify(dict(
            x=data_frame.index.astype('timedelta64[s]').values.tolist(),
            y=data_frame[1].values.tolist()
        ))
    return jsonify(fio_data.to_json(job_id, log_type))


@fio_webviewer.route('/api/<fio_result_id>/<log_type>.json',
                     methods=['GET'])
def api_fio_json_combined(fio_result_id, log_type):
    start_frame = request.args.get('start_frame')
    end_frame = request.args.get('end_frame')
    granularity = request.args.get('granularity', '1S')
    io_type = request.args.get('io_type')

    fio_data = FioResult(DATA_PATH, fio_result_id)
    fio_results = []
    for fio_group_report in fio_data.group_reports:
        for job in fio_group_report.jobs:
            fio_result = fio_data.to_dataframe(job.job_id, log_type, io_type)
            if fio_result is not None:
                if "iops" not in log_type:
                    fio_result[1] = fio_result[1].astype(float).values / 1000
                    fio_result[1] = fio_result[1].round(2)
                fio_result = fio_result.resample(granularity, label='right',
                                                 closed='right').mean()
                fio_results.append(fio_result)
    if not fio_results:
        return jsonify(dict(error='404'))
        # return error 404 with
        # html status code 200
        # so we can catch this error
        # directly in frontend
        # without triggering errors.
    data_frame = pd.concat(fio_results, join='inner')
    data_frame = data_frame.sort_index()
    data_frame = data_frame.resample(granularity, label='right',
                                     closed='right')
    if "lat" in log_type:
        data_frame = data_frame.mean()
    else:
        data_frame = data_frame.sum()
    data_frame = data_frame.fillna('None')
    if start_frame and end_frame:
        data_frame = data_frame[(data_frame.index > Milli(start_frame)) &
                                (data_frame.index < Milli(end_frame))]
    return jsonify(dict(x=data_frame.index.astype('timedelta64[s]')
                        .values.tolist(), y=data_frame[1].values.tolist()))
