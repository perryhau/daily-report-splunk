import ConfigParser
import unittest
from dailyreport import DailyReport

__author__ = 'jakub.zygmunt'

class DailyReportTest(unittest.TestCase):
    def load_config(self):
        config_file = 'config/confidential.conf'
        parser = ConfigParser.SafeConfigParser()
        parser.read(config_file)
        try:
            for section in parser.sections():
                for x in parser.items(section):
                    setattr(self, x[0], x[1])
        except ConfigParser.NoSectionError:
            self.host = ''
            self.port = ''
            self.splunk_username = ''
            self.splunk_password = ''
            self.auth_username = ''
            self.auth_password = ''
            self.mailserver = ''
            self.use_ssl = 0
            self.use_tls = 0
            self['from'] = ''
            self.index_name = None


    def read_file(self, filename):
        file = open(filename)
        output = []
        for line in file.xreadlines():
            output.append(line)
        return ''.join(output)

    def test_should_return_empty_list_on_wrong_splunk_home_path(self):
        expected_list = []
        dr = DailyReport()
        apps_with_config = dr.get_apps()
        self.assertEquals(expected_list, apps_with_config)


    def test_should_return_app_names_with_dailyreport_config(self):
        splunk_home = 'test_splunk'
        expected_item = ['%s/etc/apps/app1/local/dailyreport.conf' % splunk_home,
                         '%s/etc/apps/app3/local/dailyreport.conf' % splunk_home]
        dr = DailyReport(splunk_home=splunk_home)
        apps_with_config = dr.get_apps()
        self.assertEquals(expected_item, apps_with_config)


    def test_should_return_empty_list_on_no_config_file(self):
        expected_email_addresses = []
        splunk_home = 'test_splunk'
        input_string = '%s/etc/apps/app2/local/dailyreport.conf' % splunk_home

        dr = DailyReport()
        emailAddresses, title = dr.get_email_app_config(input_string)
        self.assertEquals(expected_email_addresses, emailAddresses)

    def test_should_return_empty_list_on_invalid_config_file(self):
        expected_email_addresses = []
        splunk_home = 'test_splunk'
        input_string = '%s/etc/apps/app3/local/dailyreport.conf' % splunk_home

        dr = DailyReport()
        emailAddresses, title = dr.get_email_app_config(input_string)
        self.assertEquals(expected_email_addresses, emailAddresses)

    def test_should_return_two_email_addresses(self):
        expected_email_addresses = ['test1@cloudreach.co.uk', 'test2+something@cloudreach.co.uk']
        splunk_home = 'test_splunk'
        input_string = '%s/etc/apps/app1/local/dailyreport.conf' % splunk_home

        dr = DailyReport()
        emailAddresses, title = dr.get_email_app_config(input_string)
        self.assertEquals(expected_email_addresses, emailAddresses)

    def test_should_return_title(self):
        expected_title = 'email title'
        splunk_home = 'test_splunk'
        input_string = '%s/etc/apps/app1/local/dailyreport.conf' % splunk_home

        dr = DailyReport()
        nothing, output_title = dr.get_email_app_config(input_string)
        self.assertEquals(expected_title, output_title)

    def test_should_return_empty_index_name_on_no_config_file(self):
        expected_index_name = None
        splunk_home = 'test_splunk'
        input_string = '%s/etc/apps/app2/local/dailyreport.conf' % splunk_home

        dr = DailyReport()
        index_name = dr.get_index_app_config(input_string)
        self.assertEquals(expected_index_name, index_name)

    def test_should_return_empty_index_name_on_invalid_config_file(self):
        expected_index_name = None
        splunk_home = 'test_splunk'
        input_string = '%s/etc/apps/app3/local/dailyreport.conf' % splunk_home

        dr = DailyReport()
        index_name = dr.get_index_app_config(input_string)
        self.assertEquals(expected_index_name, index_name)

    def test_should_return_index_name_on_valid_config_file(self):
        expected_index_name = 'splunk-index'
        splunk_home = 'test_splunk'
        input_string = '%s/etc/apps/app1/local/dailyreport.conf' % splunk_home

        dr = DailyReport()
        index_name = dr.get_index_app_config(input_string)
        self.assertEquals(expected_index_name, index_name)

    def test_should_return_no_content_on_invalid_credentials(self):
        self.load_config()
        expected_content = ''
        dr = DailyReport(host=self.host, port=self.port, username='invalid', password='nopassword')
        output = dr.get_report(index_name='lalala')
        self.assertEquals(expected_content, output)


    def test_should_return_content_on_valid_connection_data(self):
        # update connection.conf
        self.load_config()
        dr = DailyReport(host=self.host, port=self.port, username=self.splunk_username,
            password=self.splunk_password)
        output = dr.get_report(index_name=self.index_name)
        self.assertTrue(len(output) > 0)


    def test_should_return_empty_mailer_settings_on_invalid_splunk_home(self):
        expected_config = {}
        dr = DailyReport()
        output_config = dr.mailer_config
        self.assertEqual(expected_config, output_config)


    def test_should_return_default_mailer_settings_with_valid_splunk_home(self):
        expected_config = {'auth_username': 'default_user',
                           'auth_password': 'default_password',
                           'mailserver': 'default.mailserver:123',
                           'use_ssl': '0',
                           'use_tls': '0',
                           'from': 'default_from@localhost'
        }
        dr = DailyReport(splunk_home='test_splunk')
        output_config = dr.mailer_config
        self.assertEqual(expected_config, output_config)


    def test_should_return_updated_mailer_settings_with_valid_splunk_home(self):
        expected_config = {'auth_username': 'new_user',
                           'auth_password': 'new_password',
                           'mailserver': 'new.mailserver:567',
                           'use_ssl': '0',
                           'use_tls': '1',
                           'from': 'default_from@localhost'
        }
        mailer_config = 'test_splunk/etc/apps/app4/local/mailer.conf'
        dr = DailyReport(splunk_home='test_splunk', config=mailer_config)
        output_config = dr.mailer_config
        self.assertEqual(expected_config, output_config)


    def test_should_send_email_to_private_account(self):
        self.load_config()
        dr = DailyReport()
        mail_fields = ['auth_username', 'auth_password', 'mailserver', 'use_ssl', 'use_tls', 'from']
        for x in mail_fields:
            dr.mailer_config[x] = getattr(self, x)

        bodyHTML = 'This is <b>HTML</b> email'
        dr.send_email(to=self.test_to, html_body=bodyHTML)
        # check mailbox
        self.assertTrue(True)





