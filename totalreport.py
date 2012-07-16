import os
import subprocess
import re
import ConfigParser
import threading
from MyFormat import MyFormat
from jinja2.environment import Template
from mailer.mailer import Message, Mailer
from reportextractor import ReportExtractor
from splunky import Splunky, SplunkyCannotConnect

__author__ = 'jakub.zygmunt'

class TotalReport(object):

    def __init__(self, home_folder=None, splunk_home=None, host=None, port=None, config=None, username='', password=''):
        '''
        home_folder - base folder of the script, used to find HTML templates
        splunk_home - base splunk folder
        host, port, username, password - credentials needed to connect to splunk backend
        '''
        self.home_folder = home_folder if home_folder is not None else self.__get_home_folder()
        self.splunk_home = '.' if splunk_home is None else splunk_home
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

    def __get_total_report(self):
        email = self.mailer_config['to']
        email_title = self.mailer_config['title']
        if len(email) > 0:
            content = self.get_report()
            print "sending report to email: %s" % email
            self.send_email(to=email, html_body=content, title=email_title)


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

    def get_report(self):
        # use splunky
        content = ''
        if self.splunky:
            yellow_table_search = 'search index="client-*" sourcetype="cloudability" earliest=@d latest=now ' \
                                  '| eval date = strftime(_time, "%B") ' \
                                  '| stats max(total) as total by aws_account_number, aws_account_name, date, index ' \
                                  '| eval total=if(total>0, total, 0.00) ' \
                                  '| stats sum(total) as total_per_client by index, date ' \
                                  '| join type=left  index [ search index="client-*" sourcetype="cloudability" earliest=-mon@d-1d latest=-mon@d ' \
                                  '| dedup aws_account_number | stats sum(total) as total_2 by index | table index, total_2  ] ' \
                                  '| table index, total_per_client, date, total_2 | eval total_2=if(total_2>=0, total_2, 0.00) ' \
                                  '| sort index ' \
                                  '| rename index as "Client", total_per_client as "Costs", date as Date, total_2 as "Month Ago" '
            yellow_table_header = self.splunky.get_header(yellow_table_search)
            yellow_table_results = self.splunky.search(search=yellow_table_search)

            green_table_search =    'search index="client-*" source="ec2_elastic" earliest=@d latest=now() ' \
                                    '| dedup public_ip | stats count(eval(association_id!="None")) as value1, count(association_id) as value2 ' \
                                    '| eval label="Elastic IPs" | eval value = value2 + " (unused: "+value1+")" ' \
                                    '| append [ search index="client-*" source="ec2_instances" earliest=@d latest=now() | dedup instance_id ' \
                                        '| stats count(eval(state="running")) as value1a, count(eval(state="stopped")) as value1b, count(eval(state="terminated")) as value1c, count(state) as value2 ' \
                                        '| eval label="Instances" | eval value=value2 + " (running: " + value1a + ", stopped: "+ value1b +", terminated: " + value1c + ")" ' \
                                        '| eval order=2 ] ' \
                                    '| append [ search index="client-*" source="ec2_snapshots" earliest=@d latest=now() | dedup snapshot_id ' \
                                        '| stats count(eval(status="error")) as value1, count(snapshot_id) as value2 ' \
                                        '| eval label="No of EC2 snapshots" | eval value=value2 + " (error: " + value1 + ")" ' \
                                        '| eval order=3 ] ' \
                                    '| append [ search index="client-*" source="ec2_snapshots" earliest=@d latest=now() | dedup snapshot_id ' \
                                        '| eval error_size=if(status="error", volume_size, 0) | stats sum(error_size) as value1, sum(volume_size) as value2 ' \
                                        '| eval label="Size of EC2 snapshots" | eval suffix = "GB" | eval value=value2 + " (error: " + value1 + ")" ' \
                                        '| eval order=4 ] ' \
                                    '| append [ search index="client-*" source="ec2_volumes" earliest=@d latest=now() | dedup volume_id ' \
                                        '| stats count(eval(status="in-use")) as value1a, count(eval(status="available")) as value1b, count(eval(status="error")) as value1c, count(volume_id) as value2 ' \
                                        '| eval label="No of volumes" | eval value = value2 + " (available: " + value1b + ", in-use: " + value1a + ", error: " +value1c + ")" ' \
                                        '| eval order=5 ] ' \
                                    '| append [ search index="client-*" source="ec2_volumes" earliest=@d latest=now() | dedup volume_id ' \
                                        '| eval size_in_use=if(status="in-use", size, 0) | eval size_avail=if(status="available", size, 0) ' \
                                        '| eval size_error=if(status="error", size, 0) ' \
                                        '| stats sum(size_in_use) as value1a, sum(size_avail) as value1b, sum(size_error) as value1c, sum(size) as value2 ' \
                                        '| eval label="Volumes Size" | eval suffix = "GB" ' \
                                        '| eval value = value2 + " (available: " + value1b + ", in-use: " + value1a + ", error: " + value1c + ")" ' \
                                        '| eval order =6 ] ' \
                                    '| join type=left label [search index="client-*-si" report="diff" earliest=-1d@d latest=@d ' \
                                        '| stats sum(value_1d) as value_1d, sum(value_7d) as value_7d, sum(value_30d) as value_30d by label ' \
                                        '| eval label=if(label="elastic ip", "Elastic IPs", label) ' \
                                        '| table label, value_1d, value_7d, value_30d ] ' \
                                    '| eval diff_1d = value2-value_1d | eval diff_7d = value2-value_7d ' \
                                    '| eval diff_30d = value2-value_30d | eval suffix=if(order=4 OR order=6, "GB", "") ' \
                                    '| diffformat fields="value,value_1d,value_7d,value_30d,diff_1d,diff_7d,diff_30d" signs="False,False,False,False" ' \
                                    '| eval ndiff_1d = value_1d + " (" + diff_1d + ")" | eval ndiff_7d = value_7d + " (" + diff_7d + ")" | eval ndiff_30d = value_30d + " (" + diff_30d + ")" ' \
                                    '| table label, value, ndiff_1d, ndiff_7d, ndiff_30d | rename label as "Item", value as "Today", ndiff_1d as "Yesterday (diff)", ndiff_7d as "Week Ago (diff)", ndiff_30d as "Month Ago (diff)"'
            green_table_results = self.splunky.search(search=green_table_search)
            green_table_header = self.splunky.get_header(green_table_search)

            blue_table_search = 'search index="client-*" source="ec2_instances" earliest=@d latest=now | dedup instance_id |  stats count(instance_id) as value_0d by instance_type | eval label=instance_type' \
'| join type=left instance_type [ search  index="client-*" source="ec2_instances" earliest=-1d@d latest=@d | dedup instance_id | stats count(instance_id) as value_1d by instance_type ] ' \
'| join type=left instance_type [ search  index="client-*" source="ec2_instances" earliest=-7d@d latest=-6d@d | dedup instance_id | stats count(instance_id) as value_7d by instance_type ] '\
'| join type=left instance_type [ search  index="client-*" source="ec2_instances" earliest=-30d@d latest=-29d@d | dedup instance_id | stats count(instance_id) as value_30d by instance_type ] '\
'| eval value_1d = if(value_1d > 0, value_1d, 0) | eval value_7d = if(value_7d > 0, value_7d, 0) | eval value_30d = if(value_30d > 0, value_30d, 0) | eval diff_1d = value_0d - value_1d | eval diff_7d = value_0d - value_7d | eval diff_30d = value_0d - value_30d | eval value_1d = value_1d + "(" + diff_1d + ")" | eval value_7d = value_7d + "(" + diff_7d + ")" | eval value_30d = value_30d + "(" + diff_30d + ")" | table instance_type, value_0d, value_1d, value_7d, value_30d | rename instance_type as "Instance Type", value_0d as Today, value_1d as "Yesterday (diff)", value_7d as "Week Ago (diff)", value_30d as "Month Ago (diff)" '
            blue_table_results = self.splunky.search(search=blue_table_search)
            blue_table_header = self.splunky.get_header(blue_table_search)

            data = { 'yellow_table_header':yellow_table_header,
                     'yellow_table_rows':yellow_table_results,
                     'green_table_header':green_table_header,
                     'green_table_rows':green_table_results,
                     'blue_table_header':blue_table_header,
                     'blue_table_rows':blue_table_results}

            print blue_table_search
            template = '%s/static/template_splunk_email.html' % self.home_folder


            content = self.create_report_from_template(data, template=template)
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


    def create_report_from_template(self, data, template):
        data['cloudreach_logo'] = 'https://cr-splunk-1.cloudreach.co.uk:8000/en-US/static/app/cloudreach-modules/cloudreach-logo-smaller-transparent.png'

        sum_yellow_table = 0
        previous_sum_yellow_table = 0
        for row in data['yellow_table_rows']:
            sum_yellow_table += float(row['Costs'])
            previous_sum_yellow_table += float(row['Month Ago'])
            row['Costs'] = '$%s' % row['Costs']
            row['Month Ago'] = '$%s' % row['Month Ago']

        diff_string = ''
        if previous_sum_yellow_table > 0:
            diff_in_sum = sum_yellow_table - previous_sum_yellow_table
            if diff_in_sum != 0:
                sign = '+' if diff_in_sum > 0 else '-'
                diff_string = '( %s%s )' % ( sign, self.__formatDigit(diff_in_sum) )
        data['sum_yellow_table'] = '$%s' % sum_yellow_table
        data['diff_sum_yellow_table'] = diff_string

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

        sender.send(message)

    def do_total_report(self):
        if self.splunky:
            self.__get_total_report()

        else:
            print "Not connected to splunk."











