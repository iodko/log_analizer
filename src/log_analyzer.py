#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '  
#                     '$request_time';
import json
import os
import gzip
import logging

from datetime import datetime
from typing import Generator, NamedTuple

import argparse


config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
}

logger = logging.getLogger()

request_types = ['GET', 'POST', 'PUT']


class FileInfo(NamedTuple):
    log_file_with_max_date: str
    max_date: datetime


def parse_generator(log_path: str) -> str:
    """Returns one line from log file."""
    try:
        log = gzip.open(log_path,'rb') if log_path.endswith(".gz") else open(log_path)
        for line in log:
            yield line
        log.close()
    except Exception as err:
        logger.exception(err)


def parse_line(g: Generator) -> dict:
    """Parses line and accumulates data."""
    # FIXME посмотреть не подходит ли default dict int
    logger.info("Starts reading file...")
    data = {
        "total_exe_time": 0,
        "total_count": 0
    }
    for line in g:
        for request_type in request_types:
            if request_type in line:
                tmp_line = line.split(request_type)[-1]
                url = tmp_line.strip().split(' ')[0]
                request_time = float(tmp_line.split(' ')[-1])

                data["total_exe_time"] += request_time
                data["total_count"] += 1

                if data.get(url, None):
                    exe_time_list = data[url]['exe_time_list']
                    exe_time_list.append(float(request_time))

                    data[url]['count'] += 1
                    data[url]['time_sum'] += request_time
                    data[url]['time_max'] = request_time \
                            if data[url]['time_max'] < request_time\
                            else data[url]['time_max']
                    data[url]['exe_time_list'] = exe_time_list
                else:
                    data[url] = {
                            'count': 1,
                            'time_sum': float(request_time),
                            'time_max': float(request_time),
                            'exe_time_list': [float(request_time)],
                            }
    return data


def round_float(num: float, digits_qt: int = 4) -> str:
    """Rounds according to the number of digits_qt. Converted to str."""
    dot_position = str(num).find('.')
    return str(num)[:dot_position+digits_qt]


def prepare_report_data(data: dict) -> list:
    """Prepares report data."""
    logger.info(f"Processed lines: {data['total_count']}")
    report_data = []
    total_exe_time = data.get("total_exe_time")
    total_count = data.get("total_count")
    data.pop("total_exe_time", None)
    data.pop("total_count", None)
    for url, url_data in data.items():
        exe_time_list = url_data.get("exe_time_list")
        exe_time_list.sort()
        med_index = (len(exe_time_list) // 2) - 1

        time_perc = (100 * url_data["time_sum"]) / total_exe_time
        count_perc = (100 * url_data['count']) / total_count
        avg_time = url_data['time_sum'] / url_data['count']

        url_data["url"] = url
        url_data["time_med"] = exe_time_list[med_index]
        url_data["time_perc"] = round_float(time_perc)
        url_data["time_sum"] = round_float(url_data["time_sum"])
        url_data['count_perc'] = round_float(count_perc)
        url_data['avg_time'] = round_float(avg_time)

        url_data.pop('exe_time_list', None)

        report_data.append(url_data)
    return report_data


def get_files(logs_dir: str) -> list:
    """Gets list of files."""
    if not logs_dir:
        logger.error("Log dir not set in config.")
    return os.listdir(logs_dir)


def get_log_file_with_max_date(log_files: list) -> FileInfo:
    """Returns file with max date."""
    log_file_with_max_date = ""
    max_date = datetime(1, 1, 1)
    for file in log_files:
        if not log_file_with_max_date:
            log_file_with_max_date = file
            max_date = datetime.strptime(log_file_with_max_date.split('-')[-1], '%Y%m%d')
        if '-' in file:
            file_date = datetime.strptime(file.split('-')[-1], '%Y%m%d')
            if max_date < file_date:
                log_file_with_max_date = file
                max_date = file_date
    return FileInfo(log_file_with_max_date, max_date)


def is_report_exists(report_date: datetime.date, settings: dict) -> bool:
    """Checks exists reports."""
    report_dir = settings.get("REPORT_DIR", None)
    report_path = f"{report_dir}/report-{report_date}.html"
    return os.path.isfile(report_path)


def get_log_file(settings: dict) -> FileInfo:
    """Gets path to log file and date of it."""
    logs_dir = settings.get('LOG_DIR', None)
    if not logs_dir:
        logger.error("Logs dir not set.")

    is_exists = os.path.isdir(logs_dir)

    if is_exists:
        log_files = get_files(logs_dir)
        log_file_with_max_date, max_date = get_log_file_with_max_date(log_files)
        logger.info(f"Selected log file: {log_file_with_max_date}")
        return FileInfo(f"{logs_dir}/{log_file_with_max_date}", max_date.date())
    else:
        logger.error(f"Logs dir: {logs_dir} not exists.")
        return FileInfo("", datetime(1, 1, 1))


def get_report_template(settings: dict) -> str:
    """Returns text from template file."""
    report_template = settings.get('REPORT_TEMPLATE', None)
    if report_template:
        try:
            template_file = open(report_template, "r")
            template_text = template_file.read()
            template_file.close()
        except Exception as err:
            template_text = ""
            logger.exception(err)
    else:
        template_text = ""
        logger.error("Path for report template not set.")
    return template_text


def create_report(table_json: list, template_text: str, settings: dict, report_date: datetime.date) -> None:
    """Puts data to template and save report file."""
    report_dir = settings.get("REPORT_DIR", None)
    if report_dir and template_text and len(table_json):
        report_path = f"{report_dir}/report-{report_date}.html"
        report_data = template_text.replace('$table_json', str(table_json[:10]))
        try:
            with open(report_path, "w") as report_file:
                report_file.write(report_data)
                logger.info(f"Report saved to {report_path}.")
        except Exception as err:
            logger.exception(err)


def config_logger(settings: dict) -> None:
    """Configured logger."""
    log_level = settings.get("LOG_LEVEL", "INFO")
    log_file = settings.get("LOG_FILE", None)
    logging.basicConfig(
        filename=log_file,
        level=log_level,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S'
    )


def get_config(settings: dict) -> dict:
    """Gets params from config file and create script settings."""
    config_logger(settings)
    try:
        parser = argparse.ArgumentParser(description='Process config.')
        parser.add_argument('-c', '--config', default='example_config')
        args = parser.parse_args()
        config_file = args.config
        with open(config_file) as f:
            lines = f.readlines()
            for line in lines:
                params = line.split(":")
                settings[params[0]] = params[1].strip()
    except Exception as err:
        logger.exception(err)

    return settings


def main() -> None:
    try:
        settings = get_config(config)
        config_logger(settings)
        logger.debug(msg=f'Script settings: {json.dumps(settings, indent=4)}')
        file_path, report_date = get_log_file(settings)
        is_file_exists = is_report_exists(report_date, settings)
        if not is_file_exists:
            g = parse_generator(file_path)
            url_dict = parse_line(g)
            table_json = prepare_report_data(url_dict)
            template_text = get_report_template(settings)
            create_report(table_json, template_text, settings, report_date)
        else:
            logger.info(f"Log file {file_path}, alredy parsed. Report file - report-{report_date}.html.")
    except KeyboardInterrupt:
        logging.exception("The execution was interrupted by the user")


if __name__ == "__main__":
    main()
