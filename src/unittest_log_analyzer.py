import random
import unittest
import datetime

from log_analyzer import (
    config,
    round_float,
    get_log_file_with_max_date,
    get_report_template,
    get_log_file,
    parse_generator,
    prepare_report_data,
    parse_line
)


class FixturesTest(unittest.TestCase):

    def setUp(self):
        self.settings = config
        self.fixture_log_files_list = [
            'nginx-access-ui.log-20170630',
            'nginx-access-ui.log-20170730',
            'nginx-access-ui.log-20180301',
            'nginx-access-ui.log-20180325',
        ]
        self.fixture_report_data = {
            'total_exe_time': 150.50,
            'total_count': 5,
            'test_url_string':
            {
                'count': 4,
                'time_sum': 102.67,
                'time_max': 42.42,
                'exe_time_list': [10.05, 20.10, 30.10, 42.42],
            }
        }

    def test_get_report_template(self):
        template_path = get_report_template(self.settings)
        is_str = isinstance(template_path, str)
        self.assertTrue(is_str, 'Template path must be string.')

    def test_round_float(self):
        random_float = random.uniform(10.555555, 75.555555)
        digits_qt = random.randint(1, 5)
        result = round_float(random_float, digits_qt)

        self.assertEqual(len(result.split('.')[1]), digits_qt - 1)

    def test_get_log_file_with_max_date(self):
        log_path, log_date = get_log_file_with_max_date(self.fixture_log_files_list)
        is_str = isinstance(log_path, str)
        log_date = isinstance(log_date, datetime.date)

        self.assertTrue(is_str, 'Log path must be string.')
        self.assertTrue(log_date, 'Log date must be date.')
        self.failUnlessEqual(log_path, 'nginx-access-ui.log-20180325')

    def test_generator_and_parse(self):
        file_path, report_date = get_log_file(self.settings)
        g = parse_generator(file_path)
        data = parse_line(g)
        total_exe_time = data.get("total_exe_time", None)
        self.failUnless(total_exe_time)

    def test_prepare_report_data(self):
        report_data = prepare_report_data(self.fixture_report_data)
        time_med = report_data[0].get('time_med', None)
        self.assertEqual(time_med, 20.10)


if __name__ == '__main__':
    unittest.main()
