# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
# Copyright 2019 The fiowebviewer Authors. All rights reserved.

import csv
import datetime
import json
import os
import re
import tarfile
from collections import namedtuple
from io import StringIO
from io import BytesIO

import pandas as pd
from pandas.tseries.offsets import Milli
from pint import UnitRegistry

from fiowebviewer.engine.database import (
    DBSession,
    Result,
    Tag,
)
from fiowebviewer.engine.run import fio_webviewer

ROUNDING_RANGE = 3


class FioResult(object):
    _fio_output_filename = 'fio-webviewer.input'
    _fio_output_terse_filename = 'fio-webviewer.input.terse'
    _fio_output_json_filename = 'fio-webviewer.input.json'
    _fio_userargs_filename = 'fio-webviewer.userargs'
    _fio_log_prefix = 'fio-webviewer_'
    _fio_tags = 'fio-webviewer.tags'

    @classmethod
    def new_from_database(cls, base_dir, result_id):
        return cls(base_dir, result_id)

    def __init__(self, base_dir, dir_name):
        self.base_dir = base_dir
        self.dir_name = str(dir_name)
        self._fio_name = None
        self.upload_date = self._get_upload_date()
        self._fio_output = None
        self._fio_terse_output = None
        self._fio_json_output = None
        self._fio_userargs = None
        self._group_reports = None
        self._group_id_to_job_ids = None

    def __str__(self):
        return self.dir_name

    def _get_file_path(self, filename):
        return os.path.join(self.path, filename)

    def _get_fio_group_reports_from_json(self):
        with open(self._get_file_path(self._fio_output_json_filename), 'r') as f:
            data = json.load(f)
            return [FioGroupReport(self.path, self.group_id_to_job_ids, data)]

    def _get_upload_date(self):
        session = DBSession()
        result = session.query(Result). \
            filter(Result.id == self.dir_name).one()
        return result.date_submitted

    @property
    def tags_list(self):
        session = DBSession()
        result = session.query(Result).filter(Result.id ==
                                              self.dir_name).one()
        tags = session.query(Tag).filter(Tag.result == result).all()
        return tags

    @property
    def fio_name(self):
        if self._fio_name is None:
            session = DBSession()
            result = session.query(Result).filter(Result.id ==
                                                  self.dir_name).first()
            if result.name is not None:
                self._fio_name = str(result.name)
            else:
                self._fio_name = result.date_submitted
            return self._fio_name
        else:
            return self._fio_name

    @property
    def path(self):
        return os.path.join(self.base_dir, self.dir_name)

    @property
    def group_reports(self):
        if self._group_reports is None:
            try:
                self._group_reports = self._get_fio_group_reports_from_json()
            except IOError:
                raise IOError('JSON No proper input file'
                              ' (.input or .input.json).')
        return self._group_reports

    @property
    def group_id_to_job_ids(self):
        if self._group_id_to_job_ids is None:
            self._group_id_to_job_ids = {}
            job_id = 1
            for group_id, job_cnt in \
                    re.findall(r'\(groupid=(\d+), jobs=(\d+)\)',
                               self.fio_output):
                self._group_id_to_job_ids[int(group_id)] = tuple(range(job_id,
                                                            int(job_cnt) +
                                                            job_id))
                job_id = job_id + int(job_cnt)
        return self._group_id_to_job_ids

    @property
    def fio_userargs(self):
        if self._fio_userargs is None:
            with open(self._get_file_path(self._fio_userargs_filename),
                      'r') as f:
                self._fio_userargs = f.read()
        return self._fio_userargs

    @property
    def fio_output(self):
        if self._fio_output is None:
            with open(self._get_file_path(self._fio_output_filename),
                      'r') as f:
                self._fio_output = f.read()
        return self._fio_output

    @property
    def fio_terse_output(self):
        if self._fio_terse_output is None:
            with open(self._get_file_path(self._fio_output_terse_filename),
                      'r') as f:
                self._fio_terse_output = f.read()
        return self._fio_terse_output

    @property
    def fio_json_output(self):
        if self._fio_json_output is None:
            with open(self._get_file_path(self._fio_output_json_filename),
                      'r') as f:
                self._fio_json_output = f.read()
        return self._fio_json_output

    def get_group_report(self, group_id):
        for group_report in self.group_reports:
            if group_report.group_id == group_id:
                return group_report
        return None

    def get_job(self, job_id):
        for group_report in self.group_reports:
            job = group_report.get_job(job_id)
            if job is not None:
                return job
        return None

    def _get_dataframe(self, job_id, log_type, iotype):
        fio_job = self.get_job(job_id)
        fio_log = fio_job.get_log_by_type(log_type)
        if getattr(fio_log.exists, iotype):
            data_frame = pd.read_csv(getattr(fio_log.path, iotype),
                                     index_col=0, header=None,
                                     parse_dates=True,
                                     date_parser=self._dateparse)
            data_frame.drop(data_frame.columns[[1, 2]], axis=1, inplace=True)
            return data_frame
        return None

    def _dateparse(self, time):
        return pd.Timedelta(Milli(time))

    def to_dataframe(self, job_id, log_type, iotype):
        try:
            CACHE_PATH = fio_webviewer.config['CACHE_PATH']
        except KeyError:
            CACHE_PATH = None
        if CACHE_PATH is not None:  # Caching enabled
            dataframe_file_dir = os.path.join(CACHE_PATH, str(self.dir_name))
            dataframe_file = os.path.join(dataframe_file_dir,
                                          "{}.{}.{}.h5".format(log_type,
                                                               job_id,
                                                               iotype))
            if os.path.isfile(dataframe_file):  # Cached version exists
                data_frame = pd.read_hdf(dataframe_file, 'df')
            else:  # Cached version doesn't exists
                if not os.path.exists(dataframe_file_dir):
                    os.makedirs(dataframe_file_dir)
                data_frame = self._get_dataframe(job_id, log_type, iotype)
                if data_frame is None:
                    return None
                data_frame.to_hdf(dataframe_file, 'df', mode='w')
            return data_frame
        else:  # Caching disabled
            # Just return the dataframe
            return self._get_dataframe(job_id, log_type, iotype)

    def to_json(self, job_id, log_type):
        fio_job = self.get_job(job_id)
        fio_log = fio_job.get_log_by_type(log_type)
        x = []
        y = []
        with open(fio_log.path) as fh:
            for line in csv.reader(fh, delimiter=','):
                x.append(float(line[0]))
                y.append(float(line[1]))
        return dict(x=x, y=y)

    def to_csv(self, job_id, log_type, iotype):
        fio_job = self.get_job(job_id)
        fio_log = fio_job.get_log_by_type(log_type)
        data_buf = StringIO()
        buf_writer = csv.writer(data_buf, delimiter=',')
        with open(getattr(fio_log.path, iotype)) as fr:
            for line in csv.reader(fr, delimiter=','):
                buf_writer.writerow((float(line[0]), float(line[1])))
        return data_buf

    def to_tar_gz(self):
        tar_gz_file = BytesIO()
        tar = tarfile.open(mode="w:gz", fileobj=tar_gz_file)
        for log_file in os.listdir(self.path):
            if log_file.endswith('.log'):
                tar.add(os.path.join(self.path, log_file), arcname=log_file)
        tar.close()
        tar_gz_file.seek(0)
        return tar_gz_file


class FioGroupReport(object):
    supported_terse_versions = (3,)
    ureg = UnitRegistry()
    ureg.default_format = '~'

    def __init__(self, base_dir, group_id_to_job_ids, fio_data):
        self.base_dir = base_dir
        self._set_params(fio_data)
        self.jobs = [FioJob(self.base_dir, job_id)
                     for job_id in group_id_to_job_ids[self.group_id]]

    def _set_params(self, data):

        def format_latency(nano_value):
            return round(float(nano_value) / 10 ** 3, ROUNDING_RANGE)

        self.fio_version = data['fio version']

        job = data['jobs'][0]
        self.jobname = job['jobname']
        self.group_id = job['groupid']
        self.error = job['error']

        # reads
        read = job['read']
        self.read_total_io_kb = int(read['io_kbytes'])
        self.read_bw_kbps = int(int(read['bw_bytes'])/2**10)
        self.read_iops = int(read['iops'])
        self.read_runtime_ms = int(read['runtime'])

        self.read_submission_lat_min_usec = format_latency(read['slat_ns']['min'])
        self.read_submission_lat_max_usec = format_latency(read['slat_ns']['max'])
        self.read_submission_lat_mean_usec = format_latency(read['slat_ns']['mean'])
        self.read_submission_lat_stddev_usec = format_latency(read['slat_ns']['stddev'])

        self.read_completion_lat_min_usec = format_latency(read['clat_ns']['min'])
        self.read_completion_lat_max_usec = format_latency(read['clat_ns']['max'])
        self.read_completion_lat_mean_usec = format_latency(read['clat_ns']['mean'])
        self.read_completion_lat_stddev_usec = format_latency(read['clat_ns']['stddev'])
        self.read_completion_lat_percentiles_usec = {float(perc): format_latency(value) for perc, value
                                                     in read['clat_ns']['percentile'].items()}

        self.read_total_lat_min_usec = format_latency(read['lat_ns']['min'])
        self.read_total_lat_max_usec = format_latency(read['lat_ns']['max'])
        self.read_total_lat_mean_usec = format_latency(read['lat_ns']['mean'])
        self.read_total_lat_stddev_usec = format_latency(read['lat_ns']['stddev'])

        self.read_bw_min_kbps = int(read['bw_min'])
        self.read_bw_max_kbps = int(read['bw_max'])
        self.read_bw_aggr_of_total_per = float(read['bw_agg'])
        self.read_bw_mean_kbps = int(read['bw_mean'])
        self.read_bw_stddev_kbps = int(read['bw_dev'])

        # writes
        write = job['write']
        self.write_total_io_kb = int(write['io_kbytes'])
        self.write_bw_kbps = int(int(write['bw_bytes'])/2**10)
        self.write_iops = int(write['iops'])
        self.write_runtime_ms = int(write['runtime'])

        self.write_submission_lat_min_usec = format_latency(write['slat_ns']['min'])
        self.write_submission_lat_max_usec = format_latency(write['slat_ns']['max'])
        self.write_submission_lat_mean_usec = format_latency(write['slat_ns']['mean'])
        self.write_submission_lat_stddev_usec = format_latency(write['slat_ns']['stddev'])

        self.write_completion_lat_min_usec = format_latency(write['clat_ns']['min'])
        self.write_completion_lat_max_usec = format_latency(write['clat_ns']['max'])
        self.write_completion_lat_mean_usec = format_latency(write['clat_ns']['mean'])
        self.write_completion_lat_stddev_usec = format_latency(write['clat_ns']['stddev'])
        self.write_completion_lat_percentiles_usec = {float(perc): format_latency(value) for perc, value
                                                      in write['clat_ns']['percentile'].items()}

        self.write_total_lat_min_usec = format_latency(write['lat_ns']['min'])
        self.write_total_lat_max_usec = format_latency(write['lat_ns']['max'])
        self.write_total_lat_mean_usec = format_latency(write['lat_ns']['mean'])
        self.write_total_lat_stddev_usec = format_latency(write['lat_ns']['stddev'])

        self.write_bw_min_kbps = int(write['bw_min'])
        self.write_bw_max_kbps = int(write['bw_max'])
        self.write_bw_aggr_of_total_per = float(write['bw_agg'])
        self.write_bw_mean_kbps = int(write['bw_mean'])
        self.write_bw_stddev_kbps = int(write['bw_dev'])

        # cpu usage
        self.cpu_user = float(job['usr_cpu'])
        self.cpu_system = float(job['sys_cpu'])
        self.cpu_context_switches = int(job['ctx'])
        self.cpu_major_page_faults = int(job['majf'])
        self.cpu_minor_page_faults = int(job['minf'])

        # io depth
        self.io_depth_distrib = job['iodepth_level']

        # io latency
        self.io_lat_distrib_usec = job['latency_us']
        self.io_lat_distrib_msec = job['latency_ms']

    def get_attributes(self):
        for key, value in self.__dict__.items():
            if key.startswith("read_"):
                yield (key, value)
            elif key.startswith("write_"):
                yield (key, value)
            elif key.startswith("cpu_"):
                yield (key, value)
            elif key.startswith("io_"):
                yield (key, value)

    def get_job(self, job_id):
        for job in self.jobs:
            if job.job_id == int(job_id):
                return job
        return None

    def convert_unit(self, key, inner_key=None):
        if "runt" in key:
            data = getattr(self, key)
            duration = datetime.timedelta(milliseconds=data)
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            seconds = int((duration.total_seconds() % 3600) % 60)
            data = "{}h:{:02d}m:{:02d}s".format(
                hours, minutes, seconds)
        else:
            if inner_key:
                data = float(getattr(self, key)[inner_key])
            else:
                data = float(getattr(self, key))
            if "lat"in key:
                data /= 1000
                data *= self.ureg.millisecond
            elif "bw" in key:
                data /= 1000
                data *= (self.ureg.megabyte / self.ureg.second)
            elif "io" in key:
                data /= 1000
                data *= self.ureg.megabyte
            value = data.magnitude
            metric = data.units
            data = round(value, ROUNDING_RANGE) * metric
        return data


class FioJob(object):
    def __init__(self, base_dir, job_id):
        self.job_id = int(job_id)
        self.base_dir = base_dir
        self.bw_log = FioBwLog(base_dir, job_id)
        self.iops_log = FioIopsLog(base_dir, job_id)
        self.lat_log = FioLatLog(base_dir, job_id)
        self.slat_log = FioSlatLog(base_dir, job_id)
        self.clat_log = FioClatLog(base_dir, job_id)

    @property
    def logs(self):
        return (self.bw_log, self.iops_log, self.lat_log, self.slat_log,
                self.clat_log)

    def get_log_by_type(self, log_type):
        for fio_log in self.logs:
            if fio_log.log_type == log_type:
                return fio_log
        return None


class FioLog(object):
    def __init__(self, base_dir, job_id):
        assert self.log_type is not None
        self.base_dir = base_dir
        self.job_id = int(job_id)

    @property
    def filename(self):
        raise NotImplementedError('Use classes deriving from this class')

    def get_file_names(self, log_type, job_id):
        rwlog = namedtuple('{}_{}_log'.format(self.log_type, self.job_id),
                           'read write')
        return rwlog(
            read='fio-webviewer_{}.{}.log.read'.format(self.log_type, self.job_id),
            write='fio-webviewer_{}.{}.log.write'.format(self.log_type, self.job_id)
        )

    @property
    def path(self):
        path = namedtuple("path", 'read write')
        return path(
            read=os.path.join(self.base_dir, self.filename.read),
            write=os.path.join(self.base_dir, self.filename.write)
        )

    @property
    def exists(self):
        exists = namedtuple("exists", 'read write')
        return exists(
            read=(os.path.exists(self.path.read) and
                  os.path.getsize(self.path.read) > 0),
            write=(os.path.exists(self.path.write) and
                   os.path.getsize(self.path.write) > 0)
        )


class FioBwLog(FioLog):
    log_type = 'bw'
    unit = 'B'

    @property
    def filename(self):
        return self.get_file_names(self.log_type, self.job_id)


class FioIopsLog(FioLog):
    log_type = 'iops'
    unit = 'IO'

    @property
    def filename(self):
        return self.get_file_names(self.log_type, self.job_id)


class FioLatLog(FioLog):
    log_type = 'lat'
    unit = 'us'

    @property
    def filename(self):
        return self.get_file_names(self.log_type, self.job_id)


class FioSlatLog(FioLog):
    log_type = 'slat'
    unit = 'us'

    @property
    def filename(self):
        return self.get_file_names(self.log_type, self.job_id)


class FioClatLog(FioLog):
    log_type = 'clat'
    unit = 'us'

    @property
    def filename(self):
        return self.get_file_names(self.log_type, self.job_id)


class FioResultComparator(object):

    def compare(self, selected_report, referenced_report):
        compared_result = FioResultDiff()
        for key, value in selected_report.get_attributes():
            if isinstance(value, dict):
                compared_result.__dict__[key] = {}
                for inner_key in value.keys():
                    compared_result.__dict__[key][inner_key] = \
                        self._get_values(
                            key,
                            value[inner_key],
                            referenced_report.__dict__[key][inner_key])
            else:
                compared_result.__dict__[key] = \
                    self._get_values(key, value,
                                     referenced_report.__dict__[key])
        return compared_result

    def _get_values(self, key, selected_value, referenced_value):
        Point = namedtuple('_get_values',
                           'subtraction percentage_difference state')
        subtraction = round((selected_value - referenced_value),
                            ROUNDING_RANGE)
        percentage_difference = self._get_percentage_difference(
            selected_value, referenced_value)
        state = self._get_state(key, self._get_percentage_difference(
            selected_value, referenced_value))
        return Point(
            subtraction=subtraction,
            percentage_difference=percentage_difference,
            state=state
        )

    def _get_percentage_difference(self, selected_value, referenced_value):
        if referenced_value != 0:
            return round(((float(selected_value) /
                         float(referenced_value) - 1) * 100),
                         ROUNDING_RANGE)
        else:
            return round((float(selected_value) * 100), ROUNDING_RANGE)

    def _get_state(self, key, percentage_difference):
        if "lat" in key or "cpu" in key:
            if percentage_difference == 0:
                return "neutral"
            elif percentage_difference > 0:
                return "negative"
            else:
                return "positive"
        elif "bw" in key or "io" in key or "runtime" in key:
            if percentage_difference == 0:
                return "neutral"
            elif percentage_difference > 0:
                return "positive"
            else:
                return "negative"


class FioResultDiff(object):
    pass
