import logging
import unittest
from instance_report import InstanceReport
from mock_logging_handler import MockLoggingHandler
from validators import Validators

__author__ = 'jakub.zygmunt'
class InstanceReportTest(unittest.TestCase):

    def setUp(self):
        self.mockLogger = MockLoggingHandler()
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
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

    def test_should_return_search_string(self):
        expected_debug = 'search index="client-splunk-index" source="ec2_instances" earliest=@d latest=now | dedup instance_id | ' \
            'table instance_id, aws_account_name, placement, instance_type, tag_One, tag_Two'
        instance_report = InstanceReport(config="config/total_report.conf")
        index, title, emails, tags = instance_report.load_app_config(app_folder='test_splunk/etc/apps/app5')
        search_string = instance_report.create_search_string(index, tags)
        self.assertEqual(expected_debug, search_string)

    def test_should_assign_default_validator_to_tags(self):
        default_validator = Validators.default_validator
        instance_report = InstanceReport(config="config/total_report.conf")
        index, title, emails, tags = instance_report.load_app_config(app_folder='test_splunk/etc/apps/app5')
        for k,v in tags.items():
            self.assertEqual(default_validator, v)

    def test_should_return_true_on_valid_row(self):
        row =    {'instance_id': 'id_1', 'tag_One':'one', 'tag_Two':'two'}
        instance_report = InstanceReport(config="config/total_report.conf")
        index, title, emails, tags = instance_report.load_app_config(app_folder='test_splunk/etc/apps/app5')
        is_valid, error = instance_report.is_valid(row=row, tags_map=tags)
        self.assertTrue(is_valid)

    def test_should_return_false_on_invalid_row(self):
        row =    {'instance_id': 'id_1', 'tag_One':'', 'tag_Two':'two'}
        instance_report = InstanceReport(config="config/total_report.conf")
        index, title, emails, tags = instance_report.load_app_config(app_folder='test_splunk/etc/apps/app5')
        is_valid, error = instance_report.is_valid(row=row, tags_map=tags)
        self.assertFalse(is_valid)

    def test_should_return_false_on_invalid_row_missing_tag(self):
        row =    {'instance_id': 'id_1', 'tag_Two':'two'}
        instance_report = InstanceReport(config="config/total_report.conf")
        index, title, emails, tags = instance_report.load_app_config(app_folder='test_splunk/etc/apps/app5')
        is_valid, error = instance_report.is_valid(row=row, tags_map=tags)
        self.assertFalse(is_valid)

    def test_should_return_one_row_as_result(self):
        expected_result = [{'instance_id': 'id_1', 'tag_Two':'two'}]
        search_results = [
            {'instance_id': 'id_1', 'tag_Two':'two'},
            {'instance_id': 'id_1', 'tag_One':'one', 'tag_Two':'two'}

        ]
        instance_report = InstanceReport(config="config/total_report.conf")
        index, title, emails, tags = instance_report.load_app_config(app_folder='test_splunk/etc/apps/app5')
        filtered_results = instance_report.filter_results(search_results=search_results, tags_map=tags)
        self.assertEqual(expected_result, filtered_results)
