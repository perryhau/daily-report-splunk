import os
import subprocess
import re
import ConfigParser
import threading
from jinja2.environment import Template
from mailer.mailer import Message, Mailer
from reportextractor import ReportExtractor

__author__ = 'jakub.zygmunt'

class DailyReport(object):

    def __init__(self, home_folder=None, splunk_home=None, base_url=None, config=None, username='', password='', url_static=''):

        self.home_folder = home_folder if home_folder is not None else self.__get_home_folder()
        self.splunk_home = '.' if splunk_home is None else splunk_home
        self.base_url = base_url
        # load default config
        default_mailer_config = '%s/etc/system/default/alert_actions.conf' % self.splunk_home
        self.mailer_config = self.__load_config(config_file=default_mailer_config, section='email')
        for k,v in self.__load_config(config, 'email').items():
            self.mailer_config[k] = v
        for k,v in self.__load_config(config, 'dailyreport').items():
            setattr(self, k, v)

        self.base_url = self.__remove_ending_slash(self.base_url)
        self.username = username
        self.password = password
        self.url_static = url_static

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

    def __load_config(self, config_file, section):
        parser = ConfigParser.SafeConfigParser()
        try:
            parser.read(config_file)
            config_dict = {x[0]:x[1] for x in parser.items(section)}
        except (TypeError, ConfigParser.NoSectionError, ConfigParser.MissingSectionHeaderError):
            config_dict = dict()
        return config_dict
    def __reformat_content_for_gmail(self, content):
        extractor = ReportExtractor(content)
        data = extractor.extract()
        data['cloudreach_logo'] = 'https://cr-splunk-1.cloudreach.co.uk:8000/en-US/static/app/cloudreach-modules/cloudreach-logo-small-transparent.png'
        data['green_table_header'] = data['green_table'][0]
        data['green_table_rows'] = data['green_table'][1:]
        data['blue_table_header'] = data['blue_table'][0]
        data['blue_table_rows'] = data['blue_table'][1:]

        filename = 'static/template_splunk_email.html'
        fr=open(filename,'r')
        inputSource = fr.read()
        template = Template(inputSource).render(data)
        return template

    def __get_daily_report_for_app(self, filepath):
        email_addresses = self.get_email_addresses(filepath)
        if len(email_addresses) > 0:
            url = self.get_url_to_homepage(filepath)
            content = self.get_report(url, self.url_static, self.username, self.password)
            if len(content) > 0:
                content = self.__reformat_content_for_gmail(content)
                self.__log(content)
                for email in email_addresses:
                    print "send report to email: %s" % email
                    self.send_email(to=email, html_body=content)
#               print "send report to email: %s" % email_addresses
#               self.send_email(BCC=email_addresses, html_body=content)
            else:
                print "content is empty"

    def __log(self, msg):
        with open( "dailyreport.html", "w" ) as f:
            f.write( msg + "\n")

    def __get_home_folder(self):
        path = '/'.join(os.path.abspath(__file__).split('/')[:-1])
        return path

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

    def get_report(self, url='', url_static='', username='', password=''):
        content = ''.join([line for line in self.__run_process(
            ['%s/phantomjs/phantomjs' % self.home_folder, '--ignore-ssl-errors=yes',
             '%s/renderHTML.js' % self.home_folder, url, url_static, username, password])]).strip()
        content = re.sub(r'[\s]{2,}', r'\n', content, flags=re.M)
        return content

    def send_email(self, to=None, BCC=None, html_body=None):
#        message = Message(From=self.mailer_config['from'],To=to, BCC=BCC, charset='utf-8' )
        message = Message(From=self.mailer_config['from'],To=to, BCC=BCC )
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
            print "Found app: %s" % app
            self.__get_daily_report_for_app(app)







targetUrl = ''
sessionKey = ''
#content = ''.join([line for line in runProcess(['phantomjs/phantomjs', 'renderHTML.js', targetUrl, sessionKey])]).strip()

#content = re.sub(r'[\s]{2,}', r'\n', content, flags=re.M)

#print "content [%s]" % content


