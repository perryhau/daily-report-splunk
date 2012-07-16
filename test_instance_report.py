import logging
import unittest
from instance_report import InstanceReport
from mock_logging_handler import MockLoggingHandler

__author__ = 'jakub.zygmunt'
class InstanceReportTest(unittest.TestCase):

    def setUp(self):
        self.mockLogger = MockLoggingHandler()
        self.logger = logging.getLogger()
        self.logger.addHandler(self.mockLogger)

    def test_should_log_error_on_no_section_in_config(self):
        expected_message = 'No section named email'
        instance_report = InstanceReport(config="test_splunk/invalid_configs/no_email_section.conf")
        errors = self.mockLogger.messages['error']
        self.assertTrue(expected_message in errors)

    def test_should_log_error_on_invalid_splunk_config(self):
        expected_message = 'Cannot connect to splunk'
        instance_report = InstanceReport(config="test_splunk/invalid_configs/no_email_section.conf")
        errors = self.mockLogger.messages['error']
        self.assertTrue(expected_message in errors)

    def test_should_return_nothing_on_valid_config(self):
        expected_errors = []
        instance_report = InstanceReport(config='config/total_report.conf')
        errors = self.mockLogger.messages['error']
        self.assertEqual(expected_errors, errors)

    def test_should_return_error_on_config_without_dailyreport(self):
        expected_message = 'No section named dailyreport'
        instance_report = InstanceReport(config="config/total_report.conf")
        instance_report.get_report(app_folder='test_splunk/etc/apps/app2')
        errors = self.mockLogger.messages['error']
        self.assertTrue(expected_message in errors)

    def test_should_return_error_on_config_without_instancealert(self):
        expected_message = 'No section named instance_alert'
        instance_report = InstanceReport(config="config/total_report.conf")
        instance_report.get_report(app_folder='test_splunk/etc/apps/app2')
        errors = self.mockLogger.messages['error']
        self.assertTrue(expected_message in errors)

    def test_should_return_no_error_on_valid_app_config(self):
        expected_errors = []
        instance_report = InstanceReport(config="config/total_report.conf")
        instance_report.get_report(app_folder='test_splunk/etc/apps/app5')
        errors = self.mockLogger.messages['error']
        self.assertEqual(expected_errors, errors)



