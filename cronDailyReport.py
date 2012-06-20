import ConfigParser
import sys
from dailyreport import DailyReport

__author__ = 'jakub.zygmunt'

class CronDailyReport(object):

    def __init__(self, home_folder=None, config_file = None):
        self.home_folder = home_folder
        self.config_file = config_file if config_file is not None else 'config/confidential.conf'

    def load_config(self):
        parser = ConfigParser.SafeConfigParser()
        parser.read(self.config_file)
        try:
            for x in parser.items('confidential'):
                setattr(self, x[0], x[1])
        except ConfigParser.NoSectionError:

            self.splunk_username = ''
            self.splunk_password = ''
            self.splunk_home = ''



    def run(self):
        self.load_config()
        dr = DailyReport(splunk_home=self.splunk_home,  config=self.config_file)
        dr.do_daily_report()


if __name__ == "__main__":
    home_folder = '/'.join(sys.argv[0].split('/')[:-1])
    conf_file = sys.argv[1] if len(sys.argv) > 1 else None
    cron_daily = CronDailyReport(home_folder=home_folder, config_file=conf_file)
    cron_daily.run()
    print "done."




