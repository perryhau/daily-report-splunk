import logging
import ConfigParser
from splunky import SplunkyCannotConnect, Splunky

__author__ = 'jakub.zygmunt'

class InstanceReport(object):
    def __init__(self, config):
        self.logger = logging.getLogger(type(self).__name__)

        self.mailer_config = {}
        for k,v in self.__load_config(config, 'email').items():
            self.mailer_config[k] = v

        self.splunk_config = {}
        for k,v in self.__load_config(config, 'splunk').items():
            self.splunk_config[k] = v

        self.splunky = None
        try:
            self.splunky = Splunky(username=self.splunk_config['username'],
                password=self.splunk_config['password'],
                host=self.splunk_config['host'],
                port=self.splunk_config['port'])
        except KeyError, e:
            self.logger.error('Invalid splunk config. Cannot find key: %s' % e)
        except SplunkyCannotConnect, e:
            self.logger.error("Cannot connect to splunk")


    def __load_config(self, config_file, section):
        parser = ConfigParser.SafeConfigParser()
        config_dict = {}
        try:
            parser.read(config_file)
            config_dict = {x[0]:x[1] for x in parser.items(section)}
        except ConfigParser.NoSectionError:
            self.logger.error('No section named %s' % section)
        except (TypeError, ConfigParser.MissingSectionHeaderError):
            config_dict = dict()
        return config_dict

    def get_report(self, app_folder):
        if self.splunky:
            config_file = "%s/local/dailyreport.conf" % app_folder
            global_config = self.__load_config(config_file=config_file, section='dailyreport')
            instance_alert_config = self.__load_config(config_file=config_file, section='instance_alert')
            tags = instance_alert_config['tags']
        else:
            self.logger.error('Not connected to splunk')