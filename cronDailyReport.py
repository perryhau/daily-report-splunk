import ConfigParser
from argparse import ArgumentParser
import logging
import sys
from dailyreport import DailyReport

__author__ = 'jakub.zygmunt'

class CronDailyReport(object):

    def __init__(self, home_folder=None, config_file = None, filter_name = None, no_email = None, debug = None):
        self.home_folder = home_folder
        self.config_file = config_file if config_file is not None else 'config/confidential.conf'
        self.filter_name = filter_name
        self.no_email = True if no_email else False
        self.debug = True if debug else False


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
        dr = DailyReport(splunk_home=self.splunk_home,  config=self.config_file, no_email=self.no_email, debug=self.debug)
        dr.do_daily_report(filter_name=self.filter_name)


if __name__ == "__main__":
    parser = ArgumentParser(description="Load historic cloudability data")
    parser.add_argument("-c", "--config", action="store", help="Location of splunk/mailer config file",  required=True)
    parser.add_argument("-a", "--app_folder", action="store", help="Location of splunk apps folder", required=True)
    parser.add_argument("-f", "--filter", action="store", help="Filter the apps to be executed")
    parser.add_argument("-ne", "--no_email", action="store_true", help="No email")
    parser.add_argument("-d", "--debug", action="store_true", help="Turn on debug messages")

    args = parser.parse_args()


    cron_daily = CronDailyReport(home_folder=args.app_folder, config_file=args.config,
        filter_name = args.filter, no_email=args.no_email, debug=args.debug)
    cron_daily.run()
    print "done."




