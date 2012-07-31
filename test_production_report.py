import ConfigParser
import logging
import unittest
from dailyreport import DailyReport

__author__ = 'jakub.zygmunt'

class DailyReportProductionDataTest(unittest.TestCase):

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




    def test_should_return_content_on_valid_connection_data(self):
        # update connection.conf
        logging.basicConfig(level=logging.DEBUG)
        self.load_config()
        dr = DailyReport(config='config/confidential.conf', debug=True)
        output = dr.get_report(index_name='imagination')
        # dr.send_email(to="jakub.zygmunt@cloudreach.co.uk", title="production test", html_body=output)
        self.assertTrue(len(output) > 0)

if __name__ == "__main__":
    print "Running test"
    suite = unittest.TestLoader().loadTestsFromTestCase(DailyReportProductionDataTest)
    unittest.TextTestRunner(verbosity=2).run(suite)





