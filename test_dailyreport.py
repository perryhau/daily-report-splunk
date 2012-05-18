import unittest
from dailyreport import DailyReport

__author__ = 'jakub.zygmunt'

class DailyReportTest(unittest.TestCase):
    def test_should_return_empty_list_on_wrong_splunk_home_path(self):
        expected_list = []
        dr = DailyReport()
        apps_with_config = dr.get_apps()
        self.assertEquals(expected_list, apps_with_config)


    def test_should_return_app_names_with_dailyreport_config(self):
        splunk_home = 'test_splunk'
        expected_item = ['%s/etc/apps/app1/local/dailyreport.conf' % splunk_home,
                         '%s/etc/apps/app3/local/dailyreport.conf' % splunk_home ]
        dr = DailyReport(splunk_home=splunk_home)
        apps_with_config = dr.get_apps()
        self.assertEquals(expected_item, apps_with_config)

    def test_should_return_none_when_base_url_is_not_set(self):
        expected_url = None
        dr = DailyReport()
        output_url = dr.get_url_to_homepage('app_folder')
        self.assertEquals(expected_url, output_url)

    def test_should_return_link_to_homepage(self):
        expected_url = 'http://127.0.0.1:8000/en-US/app/app1/awsManagedServicesHomepage'
        splunk_home = 'test_splunk'
        input_string = '%s/etc/apps/app1/local/dailyreport.conf' % splunk_home

        dr = DailyReport(splunk_home=splunk_home, base_url='http://127.0.0.1:8000/')
        output_url = dr.get_url_to_homepage(input_string)
        self.assertEquals(expected_url, output_url)

    def test_should_return_empty_list_on_no_config_file(self):
        expected_email_addresses = [ ]
        splunk_home = 'test_splunk'
        input_string = '%s/etc/apps/app2/local/dailyreport.conf' % splunk_home

        dr = DailyReport()
        emailAddresses = dr.get_email_addresses(input_string)
        self.assertEquals(expected_email_addresses, emailAddresses)

    def test_should_return_empty_list_on_invalid_config_file(self):
        expected_email_addresses = [ ]
        splunk_home = 'test_splunk'
        input_string = '%s/etc/apps/app3/local/dailyreport.conf' % splunk_home

        dr = DailyReport()
        emailAddresses = dr.get_email_addresses(input_string)
        self.assertEquals(expected_email_addresses, emailAddresses)

    def test_should_return_two_email_addresses(self):
        expected_email_addresses = [ 'test1@cloudreach.co.uk', 'test2+something@cloudreach.co.uk']
        splunk_home = 'test_splunk'
        input_string = '%s/etc/apps/app1/local/dailyreport.conf' % splunk_home

        dr = DailyReport()
        emailAddresses = dr.get_email_addresses(input_string)
        self.assertEquals(expected_email_addresses, emailAddresses)




