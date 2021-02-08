# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
# Copyright 2019 The fiowebviewer Authors. All rights reserved.

import datetime
import os
import re
from collections import OrderedDict
from fiowebviewer.engine.exceptions import FioOutputError
from shutil import rmtree

from flask import (
    Response,
    abort,
    redirect,
    render_template,
    request,
)
from jinja2 import UndefinedError
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.utils import secure_filename

from fiowebviewer.engine.database import (
    DBSession,
    Result,
    Tag,
)
from fiowebviewer.engine.run import fio_webviewer
from fiowebviewer.engine.models import (
    FioResult,
    FioResultComparator,
)

logger = fio_webviewer.logger
DATA_PATH = fio_webviewer.config['DATA_PATH']

fio_table = OrderedDict()
fio_table["Info"] = OrderedDict([
    ("Job name", "jobname"),
    ("fio version", "fio_version"),
    ("Group id", "group_id"),
    ("error", "error"),
])
fio_table["READ"] = OrderedDict([
    ("io", "read_total_io_kb"),
    ("bw", "read_bw_kbps"),
    ("iops", "read_iops"),
    ("runt", "read_runtime_ms"),
])
fio_table["READ SLAT"] = OrderedDict([
    ("MIN", "read_submission_lat_min_usec"),
    ("MAX", "read_submission_lat_max_usec"),
    ("AVG", "read_submission_lat_stddev_usec"),
    ("STDEV", "read_submission_lat_stddev_usec"),
])
fio_table["READ CLAT"] = OrderedDict([
    ("MIN", "read_completion_lat_min_usec"),
    ("MAX", "read_completion_lat_max_usec"),
    ("AVG", "read_completion_lat_mean_usec"),
    ("STDEV", "read_completion_lat_stddev_usec"),
])
fio_table["READ LAT"] = OrderedDict([
    ("MIN", "read_total_lat_min_usec"),
    ("MAX", "read_total_lat_max_usec"),
    ("AVG", "read_total_lat_mean_usec"),
    ("STDEV", "read_total_lat_stddev_usec"),
])
fio_table["READ CLAT PERCENTILES"] = OrderedDict([
    ("1.0th", 1.0),
    ("5.0th", 5.0),
    ("10.0th", 10.0),
    ("20.0th", 20.0),
    ("30.0th", 30.0),
    ("40.0th", 40.0),
    ("50.0th", 50.0),
    ("60.0th", 60.0),
    ("70.0th", 70.0),
    ("80.0th", 80.0),
    ("90.0th", 90.0),
    ("95.0th", 95.0),
    ("99.0th", 99.0),
    ("99.5th", 99.5),
    ("99.9th", 99.9),
    ("99.95th", 99.95),
    ("99.99th", 99.99),
])
fio_table["READ BW (KB/s)"] = OrderedDict([
    ("min", "read_bw_min_kbps"),
    ("max", "read_bw_max_kbps"),
    ("per", "read_bw_aggr_of_total_per"),
    ("avg", "read_bw_mean_kbps"),
    ("stdev", "read_bw_stddev_kbps"),
])
fio_table["WRITE"] = OrderedDict([
    ("io", "write_total_io_kb"),
    ("bw", "write_bw_kbps"),
    ("iops", "write_iops"),
    ("runt", "write_runtime_ms"),
])
fio_table["WRITE SLAT"] = OrderedDict([
    ("MIN", "write_submission_lat_min_usec"),
    ("MAX", "write_submission_lat_max_usec"),
    ("AVG", "write_submission_lat_stddev_usec"),
    ("STDEV", "write_submission_lat_stddev_usec"),
])
fio_table["WRITE CLAT"] = OrderedDict([
    ("MIN", "write_completion_lat_min_usec"),
    ("MAX", "write_completion_lat_max_usec"),
    ("AVG", "write_completion_lat_mean_usec"),
    ("STDEV", "write_completion_lat_stddev_usec"),
])
fio_table["WRITE LAT"] = OrderedDict([
    ("MIN", "write_total_lat_min_usec"),
    ("MAX", "write_total_lat_max_usec"),
    ("AVG", "write_total_lat_mean_usec"),
    ("STDEV", "write_total_lat_stddev_usec"),
])
fio_table["WRITE CLAT PERCENTILES"] = OrderedDict([
    ("1.0th", 1.0),
    ("5.0th", 5.0),
    ("10.0th", 10.0),
    ("20.0th", 20.0),
    ("30.0th", 30.0),
    ("40.0th", 40.0),
    ("50.0th", 50.0),
    ("60.0th", 60.0),
    ("70.0th", 70.0),
    ("80.0th", 80.0),
    ("90.0th", 90.0),
    ("95.0th", 95.0),
    ("99.0th", 99.0),
    ("99.5th", 99.5),
    ("99.9th", 99.9),
    ("99.95th", 99.95),
    ("99.99th", 99.99),
])
fio_table["WRITE BW (KB/s)"] = OrderedDict([
    ("min", "write_bw_min_kbps"),
    ("max", "write_bw_max_kbps"),
    ("per", "write_bw_aggr_of_total_per"),
    ("avg", "write_bw_mean_kbps"),
    ("stdev", "write_bw_stddev_kbps"),
])
fio_table["IO DEPTH"] = OrderedDict([
    ("<=1", '1'),
    ("2", '2'),
    ("4", '4'),
    ("8", '8'),
    ("16", '16'),
    ("32", '32'),
    (">=64", '64'),
])
fio_table["CPU USAGE"] = OrderedDict([
    ("usr", "cpu_user"),
    ("sys", "cpu_system"),
    ("ctx", "cpu_context_switches"),
    ("majf", "cpu_major_page_faults"),
    ("minf", "cpu_minor_page_faults"),
])
fio_table["lat (usec)"] = OrderedDict([
    ("<=2", '2'),
    ("4", '4'),
    ("10", '10'),
    ("20", '20'),
    ("50", '50'),
    ("100", '100'),
    ("250", '250'),
    ("500", '500'),
    ("750", '750'),
    ("1000", '1000'),
])
fio_table["lat (msec)"] = OrderedDict([
    ("<=2", '2'),
    ("4", '4'),
    ("10", '10'),
    ("20", '20'),
    ("50", '50'),
    ("100", '100'),
    ("250", '250'),
    ("500", '500'),
    ("750", '750'),
    ("1000", '1000'),
    ("2000", '2000'),
    (">=2000", '2001'),
])


def get_all_fio_results(DATA_PATH):
    session = DBSession()
    return [FioResult(DATA_PATH, r.id)
            for r in session.query(Result).all()]


@fio_webviewer.errorhandler(400)
def bad_request(error):
    return "Bad Request", 400


@fio_webviewer.errorhandler(404)
def page_not_found(error):
    return "Page Not Found", 404


@fio_webviewer.errorhandler(500)
def internal_server_error(error):
    return "Internal Server Error", 500


@fio_webviewer.route('/fio-webviewer.sh', methods=['GET'])
def generate_fio_webviewer_script():
    ip = request.remote_addr
    logger.info("Call for fio-webviewer.sh from {}".format(ip))
    upload_url = request.url_root
    return Response(render_template('fio-webviewer.sh.tmpl', upload_url=upload_url),
                    mimetype='application/x-shellscript')


@fio_webviewer.route('/summary/<fio_result_id>', methods=['GET'])
def view_detailed_fio_result(fio_result_id):
    try:
        fio_result = FioResult(DATA_PATH, fio_result_id)
        return render_template('fio_result.html',
                               fio_result=fio_result)
    except NoResultFound as e:
        abort(404)
    except Exception as e:
        logger.exception(e)
        abort(500)


@fio_webviewer.route('/compare', methods=['GET'])
def compare_fio_result():
    try:
        all_fio_results = get_all_fio_results(DATA_PATH)
        fio_results_list = request.args.getlist('result')
        if request.args.get('delete'):
            session = DBSession()
            for fio_result in fio_results_list:
                try:
                    result = session.query(Result).filter(Result.id ==
                                                          fio_result).one()
                    session.delete(result)
                    tags = session.query(Tag).filter(Tag.result_id ==
                                                     fio_result).all()
                    for tag in tags:
                        session.delete(tag)
                except Exception as e:
                    session.rollback()
                    logger.exception(e)
                    abort(500)
                else:
                    session.commit()
                try:
                    CACHE_PATH = fio_webviewer.config['CACHE_PATH']
                except KeyError:
                    CACHE_PATH = None
                if CACHE_PATH is not None:  # Caching enabled
                    fio_result_cache_path = os.path.join(CACHE_PATH,
                                                         fio_result)
                    if os.path.exists(fio_result_cache_path):
                        rmtree(fio_result_cache_path)
                fio_result_data_path = os.path.join(DATA_PATH, fio_result)
                if os.path.exists(fio_result_data_path):
                    rmtree(fio_result_data_path)
            session.close()
            return redirect('/', code=302)

        elif request.args.get('compare'):
            selected_fio_results = [FioResult(DATA_PATH, fio_result)
                                    for fio_result in fio_results_list]
            compared_fio_result = {}
            group_report_count = 0
            for fio_result in selected_fio_results:
                compared_fio_result[fio_result.dir_name] = {}
                group_report_count += len(fio_result.group_reports)
                for fio_group_report in fio_result.group_reports:
                    compared_fio_result[
                        fio_result.dir_name
                    ][fio_group_report.group_id] = {}
                    fio_comparator = FioResultComparator()
                    compared_fio_result[fio_result.dir_name][
                        fio_group_report.group_id
                    ] = fio_comparator.compare(
                        fio_group_report,
                        selected_fio_results[0].group_reports[0]
                    )
            return render_template('fio_compare.html',
                                   results=fio_results_list,
                                   fio_results=all_fio_results,
                                   fio_table=fio_table,
                                   selected_fio_results=selected_fio_results,
                                   compared_fio_result=compared_fio_result,
                                   group_report_count=group_report_count + 1)
        else:
            raise UndefinedError
    except UndefinedError as e:
        abort(400)
    except NoResultFound as e:
        abort(404)
    except Exception as e:
        logger.exception(e)
        abort(500)


@fio_webviewer.route('/summary/<fio_result_id>/detailed', methods=['GET'])
def view_detailed_fio_result_detailed(fio_result_id):
    try:
        fio_result = FioResult(DATA_PATH, fio_result_id)
        return render_template('fio_result_detailed.html',
                               fio_result=fio_result)
    except NoResultFound as e:
        abort(404)
    except Exception as e:
        logger.exception(e)
        abort(500)


@fio_webviewer.route('/', methods=['GET'])
def view_fio_results_index():
    all_fio_results = get_all_fio_results(DATA_PATH)
    return render_template('index.html',
                           fio_results=all_fio_results)


@fio_webviewer.route('/', methods=['POST'])
def upload_fio_results():
    session = DBSession()
    new_result = Result(date_submitted=datetime.datetime.utcnow())
    session.add(new_result)
    session.flush()
    fio_result_path = os.path.join(DATA_PATH, str(new_result.id))
    try:
        os.mkdir(fio_result_path)
        for upload_filename, upload_file in request.files.items():
            logger.debug("Uploading file: {}".format(upload_file.filename))
            local_file_path = os.path.join(
                fio_result_path, secure_filename(upload_file.filename))
            if "fio-webviewer.name" in upload_file.filename:
                new_result.name = upload_file.read().strip()
            if "fio-webviewer.tags" in upload_file.filename:
                for line in upload_file.readlines():
                    line = line.strip()
                    new_tag = Tag(tag=line.decode(), result=new_result)
                    session.add(new_tag)
            upload_file.stream.seek(0)
            upload_file.save(local_file_path)

    except FioOutputError:
        logger.warning("Wrong format of fio-webviewer.input")
        logger.warning(
            "Deleting fio results upload dir: {}".format(fio_result_path))
        rmtree(fio_result_path)
        session.rollback()
        return "Bad Request (fio-webviewer.input Error)\n", 400
    except Exception as e:
        logger.exception(e)
        logger.warning("Got exception while processing uploaded fio files",
                       exc_info=True)
        logger.warning(
            "Deleting fio results upload dir: {}".format(fio_result_path))
        rmtree(fio_result_path)
        session.rollback()
        return "Bad Request\n", 400
    else:
        session.commit()
        return "Upload OK\n"
