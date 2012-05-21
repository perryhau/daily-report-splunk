import ConfigParser
import unittest
from dailyreport import DailyReport

__author__ = 'jakub.zygmunt'

class DailyReportTest(unittest.TestCase):

    def load_config(self):
        config_file = 'config/connection.conf'
        parser = ConfigParser.SafeConfigParser()
        parser.read(config_file)
        try:
            for x in parser.items('connection'):
                setattr(self, x[0], x[1])
        except ConfigParser.NoSectionError:
            self.url = ''
            self.session_key = ''




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

    def test_should_return_no_content_on_invalid_url(self):
        expected_content = ''
        invalid_url = 'http://127.0.0.1:8000/totally_invalid_url'
        dr = DailyReport()
        output = dr.get_report(url=invalid_url)
        self.assertEquals(expected_content, output)

    def test_should_return_no_content_on_invalid_session(self):
        self.load_config()
        expected_content = ''
        dr = DailyReport()
        output = dr.get_report(url=self.url, session_key='invalid' )
        self.assertEquals(expected_content, output)

    def test_should_return_content_on_valid_connection_data(self):
        # update connection.conf
        self.load_config()
        dr = DailyReport()
        output = dr.get_report(url=self.url, session_key=self.session_key )
        self.assertTrue(len(output) > 0)

    def test_should_return_empty_mailer_settings_on_invalid_splunk_home(self):
        expected_config = {}
        dr = DailyReport()
        output_config = dr.mailer_config
        self.assertEqual(expected_config, output_config)

    def test_should_return_default_mailer_settings_with_valid_splunk_home(self):
        expected_config = {'auth_username':'default_user',
                          'auth_password':'default_password',
                          'mailserver':'default.mailserver:123',
                          'use_ssl':'0',
                          'use_tls':'0',
                          'from':'default_from@localhost'
                          }
        dr = DailyReport(splunk_home='test_splunk')
        output_config = dr.mailer_config
        self.assertEqual(expected_config, output_config)

    def test_should_return_updated_mailer_settings_with_valid_splunk_home(self):
        expected_config = {'auth_username':'new_user',
                           'auth_password':'new_password',
                           'mailserver':'new.mailserver:567',
                           'use_ssl':'0',
                           'use_tls':'1',
                           'from':'default_from@localhost'
        }
        mailer_config = '/etc/apps/app4/local/mailer.conf'
        dr = DailyReport(splunk_home='test_splunk', mailer_config= mailer_config)
        output_config = dr.mailer_config
        self.assertEqual(expected_config, output_config)




