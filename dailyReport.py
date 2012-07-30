import locale
import os
from smtplib import SMTPDataError
import subprocess
import re
import ConfigParser
import threading
from MyFormat import MyFormat
import time
import calendar
import datetime
from jinja2.environment import Template
from mailer.mailer import Message, Mailer
from reportextractor import ReportExtractor
from splunky import Splunky, SplunkyCannotConnect
import logging

__author__ = 'jakub.zygmunt'

class DailyReport(object):

    def __init__(self, home_folder=None, splunk_home=None, host=None, port=None, config=None, username='', password='', no_email=True, debug=False):
        '''
        home_folder - base folder of the script, used to find HTML templates
        splunk_home - base splunk folder
        host, port, username, password - credentials needed to connect to splunk backend
        '''
        self.home_folder = home_folder if home_folder is not None else self.__get_home_folder()
        self.splunk_home = '.' if splunk_home is None else splunk_home
        self.no_email = True if no_email else False

        # load default config
        default_mailer_config = '%s/etc/system/default/alert_actions.conf' % self.splunk_home
        self.mailer_config = self.__load_config(config_file=default_mailer_config, section='email')
        for k,v in self.__load_config(config, 'email').items():
            self.mailer_config[k] = v

        self.splunk_config = {'host': self.__remove_ending_slash(host),
                              'port': port,
                              'username' : username,
                              'password' : password
                              }
        for k,v in self.__load_config(config, 'splunk').items():
            self.splunk_config[k] = v



        self.splunky = None
        try:
            self.splunky = Splunky(username=self.splunk_config['username'],
                                   password=self.splunk_config['password'],
                                   host=self.splunk_config['host'],
                                   port=self.splunk_config['port'])
        except SplunkyCannotConnect, e:
            print "Cannot connect to splunk %s" % self.splunk_config

        logging.basicConfig()
        self.LOG = logging.getLogger(__name__)

        if debug:
            self.LOG.setLevel(logging.DEBUG)

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
        data['cloudreach_logo'] = 'https://s3-eu-west-1.amazonaws.com/splunk-dailyreport/cloudreach-logo-smaller-transparent.png'
        data['green_table_header'] = data['green_table'][0]
        data['green_table_rows'] = data['green_table'][1:]
        data['blue_table_header'] = data['blue_table'][0]
        data['blue_table_rows'] = data['blue_table'][1:]

        filename = '%s/static/template_splunk_email.html' % self.home_folder
        fr=open(filename,'r')
        inputSource = fr.read()
        template = Template(inputSource).render(data)
        return template

    def __get_daily_report_for_app(self, filepath):
        email_addresses, email_title = self.get_email_app_config(filepath)
        index_name = self.get_index_app_config(filepath)

        content = self.get_report(index_name=index_name)
        if len(email_addresses) > 0 and not self.no_email:
            for email in email_addresses:
                print "send report to email: %s" % email
                self.send_email(to=email, html_body=content, title=email_title)
#               print "send report to email: %s" % email_addresses
#               self.send_email(BCC=email_addresses, html_body=content)
        else:
            print "not sending email. Email addresses: %s, no_email flag: %s" % (len(email_addresses), self.no_email)


    def __log(self, msg):
        with open( "dailyreport.html", "w" ) as f:
            f.write( msg + "\n")

    def __get_home_folder(self):
        path = '/'.join(os.path.abspath(__file__).split('/')[:-1])
        return path

    def get_apps(self, filter_name = None):
        appsFolder = "%s/etc/apps" % self.splunk_home
        confFiles = []
        if os.path.exists(appsFolder):
            for filename in os.listdir(appsFolder):
                if filter_name and not filter_name.lower() in filename.lower():
                    continue
                file = "%s/%s/local/dailyreport.conf" % (appsFolder, filename)
                if os.path.isfile(file):
                    confFiles.append(file)
        return confFiles

    def get_email_app_config(self, config_file):
        emails = []
        title = None
        if os.path.isfile(config_file):
            parser = ConfigParser.SafeConfigParser()
            parser.read(config_file)

            try:
                title = parser.get('dailyreport', 'title')
            except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
                pass

            try:
                emails_option = parser.get('dailyreport', 'emails')
                emails_option = re.sub('[, ]+',',', emails_option)
                emails = emails_option.split(',')

            except ConfigParser.NoSectionError:
                pass
        return (emails, title)

    def get_index_app_config(self, config_file):
        index_name = None
        if os.path.isfile(config_file):
            parser = ConfigParser.SafeConfigParser()
            parser.read(config_file)

            try:
                index_name = parser.get('dailyreport', 'index_name')
            except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
                pass

        return index_name

    def compute_additional_values_yellow_table(self, table_header, table_results):
        self.LOG.debug(table_header)
        table_header.remove('last_month_total')
        table_header.remove('last_month_date')
        table_header.append('Estimation')
        table_header.append('Est diff')

        now = datetime.datetime.now()
        try:
            last_month = time.strptime(table_results[0].get('last_month_date',''), "%Y/%m/%d")
            last_month_no, last_month_days = calendar.monthrange(last_month.tm_year, last_month.tm_mon)
            month_no, month_days = calendar.monthrange(now.year, now.month)
            for row in table_results:
                try:
                    estimation = ((int(float(row['last_month_total']) * 100) / last_month_days) * month_days )/ 100
                    row['Estimation'] = estimation
                    estimation_current_day = ((int(float(row['last_month_total']) * 100) / last_month_days) * now.day )/ 100

                    row['Est diff'] = float(row['Costs']) - estimation_current_day
                except KeyError:
                    row['Estimation'] = row['Est diff'] = 0
        except ValueError:
            for row in table_results:
                row['Estimation'] = row['Est diff'] = '0'

        self.LOG.debug(table_results)

    def get_report(self, index_name):
        # use splunky
        content = ''
        if self.splunky:
            yellow_table_search = 'search index="client-{0}" sourcetype="cloudability" earliest=@d latest=now '\
                     '| eval date = strftime(_time, "%B") | stats max(total) as total by aws_account_number, aws_account_name, date '\
                     '| eval total=if(total>0, total, 0.00) '\
                     '| join type=left  aws_account_number [ search index="client-{0}" sourcetype="cloudability" earliest=-mon@d-1d latest=-mon@d '\
                     '| dedup aws_account_number | eval total_2=if(total>0, total, 0.00) '\
                     '| table aws_account_number, total_2 ] '\
                     '| join type=left aws_account_number [ search index="client-{0}" sourcetype="cloudability_monthly" earliest=-1mon@mon latest=@mon ' \
                     '| eval last_month_date= strftime(_time, "%Y/%m/%d") | rename total as last_month_total ' \
                     '| table aws_account_number, aws_account_name, last_month_total,last_month_date ] ' \
                     '| table aws_account_name, total, date, total_2, last_month_total, last_month_date ' \
                     '| eval total_2=if(total_2>=0, total_2, 0.00) ' \
                     '| rename aws_account_name as "AWS Account", total as "Costs", date as Date, total_2 as "-30d"'.format(index_name)
            yellow_table_header = self.splunky.get_header(yellow_table_search)
            yellow_table_results = self.splunky.search(search=yellow_table_search)
            self.LOG.debug("yellow_table_header:\n%s" % yellow_table_header)
            self.LOG.debug("yellow_table_search:\n%s" % yellow_table_search)
            if len(yellow_table_results) > 0:
                self.compute_additional_values_yellow_table(table_header=yellow_table_header, table_results=yellow_table_results)

            green_table_search =    'search index="client-{0}" source="ec2_elastic" earliest=@d latest=now() | dedup public_ip | stats count(eval(attached!="True")) as value1, count(association_id) as value2 | eval label="Elastic IPs" ' \
                                    '| eval value = value2 + "<br />(unused: "+value1+")" ' \
                                    '| append [ search '\
                                    'index="client-{0}" source="ec2_instances" earliest=@d latest=now() | dedup instance_id | stats count(eval(state="running")) as value1a, count(eval(state="stopped")) as value1b, count(eval(state="terminated")) as value1c, count(state) as value2 | eval label="Instances" ' \
                                    '| eval value=value2 + "<br />(run: " + value1a + ", stop: "+ value1b +", term: " + value1c + ")" | eval order=2 ] '\
                                    '| append [ search ' \
                                    'index="client-{0}" source="ec2_snapshots" earliest=@d latest=now() | dedup snapshot_id | stats count(eval(status="error")) as value1, count(snapshot_id) as value2 | eval label="No of EC2 snapshots" '\
                                    '| eval value=value2 + "<br />(error: " + value1 + ")" | eval order=3 ] ' \
                                    '| append [ search '\
                                    'index="client-{0}" source="ec2_snapshots" earliest=@d latest=now() | dedup snapshot_id | eval error_size=if(status="error", volume_size, 0) | stats sum(error_size) as value1, sum(volume_size) as value2 | eval label="Size of EC2 snapshots" ' \
                                    '| eval suffix = "GB" '\
                                    '| eval value=value2 + "<br />(error: " + value1 + ")" | eval order=4 ] ' \
                                    '| append [ search '\
                                    'index="client-{0}" source="ec2_volumes" earliest=@d latest=now() | dedup volume_id | stats count(eval(status="in-use")) as value1a, count(eval(status="available")) as value1b, count(eval(status="error")) as value1c, count(volume_id) as value2 | eval label="No of volumes" ' \
                                    '| eval value = value2 + "<br />(avail: " + value1b + ", use: " + value1a + ", err: " +value1c + ")" | eval order=5 ] '\
                                    '| append [ search ' \
                                    'index="client-{0}" source="ec2_volumes" earliest=@d latest=now() | dedup volume_id | eval size_in_use=if(status="in-use", size, 0) | eval size_avail=if(status="available", size, 0) | eval size_error=if(status="error", size, 0) | stats sum(size_in_use) as value1a, sum(size_avail) as value1b, sum(size_error) as value1c, sum(size) as value2 | eval label="Volumes Size" '\
                                    '| eval suffix = "GB" ' \
                                    '| eval value = value2 + "<br />(avail: " + value1b + ", use: " + value1a + ", err: " + value1c + ")"  | eval order =6 ] '\
                                    '| join type=left label [search index="client-{0}-si" report="diff" earliest=-1d@d latest=@d | dedup label | sort order | eval label=if(label="elastic ip", "Elastic IPs", label) | table label, value_1d, value_7d, value_30d  ] ' \
                                    '| table label, value, value2, value_1d, value_7d, value_30d '\
                                    '| rename label as "Item", value as "Today", value_1d as "-1d (diff)", value_7d as "-7d (diff)", value_30d as "-30d (diff)"'.format(index_name)
            green_table_results = self.splunky.search(search=green_table_search)
            green_table_header = self.splunky.get_header(green_table_search)

            blue_table_search = 'search index="client-{0}" source="ec2_instances" earliest=@d latest=now | dedup instance_id |  stats count(instance_id) as value_0d by instance_type | eval label=instance_type' \
'| join type=left instance_type [ search  index="client-{0}" source="ec2_instances" earliest=-1d@d latest=@d | dedup instance_id | stats count(instance_id) as value_1d by instance_type ] ' \
'| join type=left instance_type [ search  index="client-{0}" source="ec2_instances" earliest=-7d@d latest=-6d@d | dedup instance_id | stats count(instance_id) as value_7d by instance_type ] '\
'| join type=left instance_type [ search  index="client-{0}" source="ec2_instances" earliest=-30d@d latest=-29d@d | dedup instance_id | stats count(instance_id) as value_30d by instance_type ] '\
'| eval value_1d = if(value_1d > 0, value_1d, 0) | eval value_7d = if(value_7d > 0, value_7d, 0) | eval value_30d = if(value_30d > 0, value_30d, 0) | eval diff_1d = value_0d - value_1d | eval diff_7d = value_0d - value_7d | eval diff_30d = value_0d - value_30d | eval value_1d = value_1d + "(" + diff_1d + ")" | eval value_7d = value_7d + "(" + diff_7d + ")" | eval value_30d = value_30d + "(" + diff_30d + ")" | table instance_type, value_0d, value_1d, value_7d, value_30d ' \
'| rename instance_type as "Instance Type", value_0d as Today, value_1d as "-1d (diff)", value_7d as "-7d (diff)", value_30d as "-30d (diff)" '.format(index_name)
            blue_table_results = self.splunky.search(search=blue_table_search)
            blue_table_header = self.splunky.get_header(blue_table_search)

            data = { 'yellow_table_header':yellow_table_header,
                     'yellow_table_rows':yellow_table_results,
                     'green_table_header':green_table_header,
                     'green_table_rows':green_table_results,
                     'blue_table_header':blue_table_header,
                     'blue_table_rows':blue_table_results}
            template = '%s/static/template_splunk_email.html' % self.home_folder
            self.LOG.debug("green_table_header:\n%s" % green_table_header)
            self.LOG.debug("green_table_search:\n%s" % green_table_search)
            self.LOG.debug("blue_table_header:\n%s" % blue_table_header)
            self.LOG.debug("blue_table_search:\n%s" % blue_table_search)


            content = self.create_report_from_template(data, template=template)
            if self.LOG.level == logging.DEBUG:
                self.LOG.debug("writing template output to the file")
                self.__log(content)
        return content
    def __formatDigit(self, digit):
        normal_spaces = digit
        rounded_digit = '%.2f' % float(digit)
        match = re.search("([\d]+)(\.[\d]+)?", rounded_digit)
        if match:
            digit = match.group(1)
            rest = match.group(2) if match.group(2) else ''
            reversed = digit[::-1]
            reversed_spaces = re.sub("(.{3})", "\\1 ", reversed)
            normal_spaces = "%s%s" % (reversed_spaces[::-1].strip(), rest)

        return normal_spaces

    def __sizeof_fmt(self, num):
        # from SO. we have only one element here becase min value for num is 1 GB
        num = float(num)
        for x in ['GB']:
            if num < 1024.0:
                return "%3.1f %s" % (num, x)
            num /= 1024.0
        return "%3.1f %s" % (num, 'TB')

    def __get_diff(self, new_value, old_value):
        difference = int(float(new_value) - float(old_value))
        sign = "-" if difference < 0 else "+" if difference > 0 else ""
        return "%s%s" % (sign, abs(difference))

    def create_report_from_template(self, data, template):
        data['cloudreach_logo'] = 'https://cr-splunk-1.cloudreach.co.uk:8000/en-US/static/app/cloudreach-modules/cloudreach-logo-smaller-transparent.png'


        ### modify yellow table
        sum_yellow_table = 0
        previous_sum_yellow_table = 0
        fields = ['Costs', '-30d', 'Estimation', 'Est diff']
        locale.setlocale( locale.LC_MONETARY, 'en_US.UTF-8')
        for row in data['yellow_table_rows']:
            sum_yellow_table += float(row['Costs'])
            previous_sum_yellow_table += float(row['-30d'])
            for f in fields:
                try:
                    row[f] = locale.currency(float(row[f]), grouping=True)
                except (ValueError, KeyError):
                    pass

        data['yellow_table_format'] =  {
            'AWS Account' : { 'align' : 'left', 'style': 'padding-left: 2%'},
            'Costs' : { 'align' : 'right', 'style': 'padding-right: 2%'},
            'Date' : { 'align' : 'left', 'style': 'padding-left: 5%'},
            '-30d' : { 'align' : 'right', 'style': 'padding-right: 2%'},
            'Estimation' : { 'align' : 'right', 'style': 'padding-right: 2%'},
            'Est diff' : { 'align' : 'right', 'style': 'padding-right: 2%'},
        }
        diff_string = ''
        if previous_sum_yellow_table > 0:
            diff_in_sum = sum_yellow_table - previous_sum_yellow_table
            if diff_in_sum != 0:
                sign = '+' if diff_in_sum > 0 else '-'
                diff_string = '( %s%s )' % ( sign, self.__formatDigit(diff_in_sum) )
        data['sum_yellow_table'] = '$%s' % sum_yellow_table
        data['diff_sum_yellow_table'] = diff_string

        ### modify green table
        data['green_table_header'].remove('value2')
        fields_to_modify = ['-1d (diff)', '-7d (diff)', '-30d (diff)']
        def replace_in_string(match):
            return self.__sizeof_fmt(match.group(0))

        for row in data['green_table_rows']:
            m = re.findall(r"\bsize\b", row['Item'], re.IGNORECASE)

            for field in fields_to_modify:
                get_number = re.search(r"^([0-9.]+)", row.get(field, ''))

                if get_number:
                    number = get_number.group(0)
                    row[field] = "%s<br/>(%s)" % (row[field], self.__get_diff(row['value2'], number))

            if m:
                row['Today'] = re.sub(r'([0-9]+)', replace_in_string, row['Today'])
                for f in fields_to_modify:
                    #row[f] = self.__sizeof_fmt(row[f])
                    row[f] = re.sub(r'([0-9]+)', replace_in_string, row[f])

            # add diff to values




        fr=open(template,'r')
        inputSource = fr.read()
        template = Template(inputSource).render(data)
        return template

    def send_email(self, to=None, BCC=None, html_body=None, title=None):
#        message = Message(From=self.mailer_config['from'],To=to, BCC=BCC, charset='utf-8' )
        message = Message(From=self.mailer_config['from'],To=to, BCC=BCC )
        message.Subject = title if title is not None else 'A Daily Report'
        message.Html = html_body

        mailer_url_data = self.mailer_config['mailserver'].split(':')

        sender = Mailer(host=mailer_url_data[0],
                        port=mailer_url_data[1],
                        use_tls=True if self.mailer_config['use_tls'] == '1' else False,
                        usr=self.mailer_config['auth_username'],
                        pwd=self.mailer_config['auth_password'])
        try:
            sender.send(message)
        except SMTPDataError as e:
            print "%s - %s" % (to, e)

    def do_daily_report(self, filter_name=None):
        if self.splunky:
            if filter_name:
                print "Filter apps to: [%s]" % filter_name
            apps = self.get_apps(filter_name=filter_name)
            for app in apps:
                print "Found app: %s" % app
                self.__get_daily_report_for_app(app)

        else:
            print "Not connected to splunk."











