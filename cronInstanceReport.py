#!/usr/bin/python
import ConfigParser
from argparse import ArgumentParser
import os
import sys
from instance_report import InstanceReport

__author__ = 'jakub.zygmunt'

class CronInstanceReport(object):

    def __init__(self, app_folder=None, config_file = None):
        self.app_folder = app_folder
        self.config_file = config_file if config_file is not None else 'config/confidential.conf'

    def is_valid_instance_report_app(self, config_file):
        parser = ConfigParser.SafeConfigParser()
        try:
            parser.read(config_file)
            if 'instance_alert' in parser.sections():
                return True
        except (TypeError, ConfigParser.MissingSectionHeaderError):
            pass

        return False

    def get_apps(self):

        confFiles = []
        if os.path.exists(self.app_folder):
            for filename in os.listdir(self.app_folder):
                folder = "%s/%s" % ( self.app_folder, filename)
                file = "%s/local/dailyreport.conf" % folder
                if self.is_valid_instance_report_app(config_file=file):
                    confFiles.append(folder)
        return confFiles

    def run(self):
        ir = InstanceReport(config=self.config_file)
        apps = self.get_apps()
        for app in apps:
            print "Found the instance report configuration in %s" % app
            ir.get_report(app_folder=app)


if __name__ == "__main__":
    parser = ArgumentParser(description="Load historic cloudability data")
    parser.add_argument("-c", "--config", action="store", help="Location of splunk/mailer config file",  required=True)
    parser.add_argument("-a", "--app_folder", action="store", help="Location of splunk apps folder", required=True)

    args = parser.parse_args()

    cron_daily = CronInstanceReport(app_folder=args.app_folder, config_file=args.config)
    cron_daily.run()
    print "done."




