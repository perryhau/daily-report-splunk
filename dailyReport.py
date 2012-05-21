import os
import subprocess
import re
import ConfigParser
import threading
from mailer.mailer import Message, Mailer

__author__ = 'jakub.zygmunt'

class DailyReport(object):

    def __init__(self, splunk_home=None, base_url=None, mailer_config=None, session_key = None):
        self.splunk_home = '.' if splunk_home is None else splunk_home
        self.base_url = self.__remove_ending_slash(base_url)
        # load default config
        default_mailer_config = '%s/etc/system/default/alert_actions.conf' % self.splunk_home
        self.mailer_config = self.__load_mailer_config(default_mailer_config)
        new_mailer_config = '%s/%s' % (splunk_home, mailer_config)
        for k,v in self.__load_mailer_config(new_mailer_config).items():
            self.mailer_config[k] = v

        self.session_key = session_key

    def __run_process(self, cmd):
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while(True):
            retcode = p.poll()
            line = p.stdout.readline()
            yield line
            if(retcode is not None):
                break

    def __remove_ending_slash(self, url):
        return url[:-1] if url is not None and url[-1] == '/' else url

    def __load_mailer_config(self, config_file):
        parser = ConfigParser.SafeConfigParser()
        try:
            parser.read(config_file)
            config_dict = {x[0]:x[1] for x in parser.items('email')}
        except (TypeError, ConfigParser.NoSectionError):
            config_dict = dict()
        return config_dict

    def __get_daily_report_for_app(self, filepath):
        email_addresses = self.get_email_addresses(filepath)
        if len(email_addresses) > 0:
            url = self.get_url_to_homepage(filepath)
            content = self.get_report(url, self.session_key)
            if len(content) > 0:
#               for email in email_addresses:
#                   print "send report to email: %s" % email
#                   self.send_email(to=email, html_body=content)
                print "send report to email: %s" % email_addresses
                self.send_email(BCC=email_addresses, html_body=content)

    def get_apps(self):
        appsFolder = "%s/etc/apps" % self.splunk_home
        confFiles = []
        if os.path.exists(appsFolder):
            for filename in os.listdir(appsFolder):
                file = "%s/%s/local/dailyreport.conf" % (appsFolder, filename)
                if os.path.isfile(file):
                    confFiles.append(file)
        return confFiles

    def get_url_to_homepage(self, input_string):
        url = None
        if self.base_url:
            match = re.search(r'/([^/]*)/local/dailyreport.conf$', input_string)
            if match.group(1):
                url = '%s/en-US/app/%s/awsManagedServicesHomepage' % (self.base_url, match.group(1))
        return url

    def get_email_addresses(self, config_file):
        emails = []
        if os.path.isfile(config_file):
            parser = ConfigParser.SafeConfigParser()
            parser.read(config_file)
            try:
                emails_option = parser.get('dailyreport', 'emails')
                emails_option = re.sub('[, ]+',',', emails_option)
                emails = emails_option.split(',')
            except ConfigParser.NoSectionError:
                pass
        return emails

    def get_report(self, url='', session_key=''):
        content = ''.join([line for line in self.__run_process(['phantomjs/phantomjs', '--ignore-ssl-errors=yes', 'renderHTML.js', url, session_key])]).strip()
        content = re.sub(r'[\s]{2,}', r'\n', content, flags=re.M)
        return content

    def send_email(self, to='', BCC=None, html_body=None):
        message = Message(From=self.mailer_config['from'],To=to, BCC=BCC, charset='utf-8' )
        message.Subject = 'A Daily Report'
        message.Html = html_body

        mailer_url_data = self.mailer_config['mailserver'].split(':')

        sender = Mailer(host=mailer_url_data[0],
                        port=mailer_url_data[1],
                        use_tls=True if self.mailer_config['use_tls'] == '1' else False,
                        usr=self.mailer_config['auth_username'],
                        pwd=self.mailer_config['auth_password'])

        sender.send(message)

    def do_daily_report(self):
        apps = self.get_apps()
        for app in apps:
            self.__get_daily_report_for_app(app)







targetUrl = ''
sessionKey = ''
#content = ''.join([line for line in runProcess(['phantomjs/phantomjs', 'renderHTML.js', targetUrl, sessionKey])]).strip()

#content = re.sub(r'[\s]{2,}', r'\n', content, flags=re.M)

#print "content [%s]" % content


