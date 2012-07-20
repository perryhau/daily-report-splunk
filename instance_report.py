import logging
import ConfigParser
from jinja2.environment import Template
from mailer.mailer import Message, Mailer
from splunky import SplunkyCannotConnect, Splunky
from validators import Validators

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

    def create_search_string(self, index, tags):
        tag_names_string = ', '.join(tags.keys())
        search_string = 'search index="client-{0}" source="ec2_instances" earliest=@d latest=now |'\
                        ' dedup instance_id |'\
                        ' table instance_id, aws_account_name, placement, instance_type, {1}'.format(index, tag_names_string)
        return search_string

    def do_search(self, index, tags):
        search_string = self.create_search_string(index, tags)
        instance_table_header = self.splunky.get_header(search_string)
        instance_table_results = self.splunky.search(search=search_string)
        self.logger.debug(search_string)

        return instance_table_header, instance_table_results


    def load_app_config(self, app_folder):
        config_file = "%s/local/dailyreport.conf" % app_folder
        config = self.__load_config(config_file=config_file, section='dailyreport')

        # required field
        config['tags'] = ''

        #override global config
        for k,v in  self.__load_config(config_file=config_file, section='instance_alert').items():
            config[k] = v

        emails = config['emails'].split(' ')
        tags = config['tags'].replace(' ', '').split(',')

        # tag_Name: validator
        tags_map = {}
        for tag in tags:
            tags_map['tag_%s' % tag] = Validators.default_validator

        return config['index_name'], config['title'], emails, tags_map

    def is_valid(self, row, tags_map):
        error = None
        for tag,validator in tags_map.items():
            value = row.get(tag, None)
            passed = validator(value)
            if not passed:
                return False, error
        # it passed all validations
        return True, error


    def filter_results(self, search_results, tags_map):
        results = []
        for row in search_results:
            is_valid, error = self.is_valid(row, tags_map)
            if not is_valid:
                results.append(row)

        return results

    def fix_utf8(self, list):
        new_list = []
        for element in list:
            try:
                new_map = {k:v.decode("ascii", "ignore") for k,v in element.iteritems()}
            except UnicodeDecodeError:
                print element
                raise Exception
            new_list.append(new_map)
        return new_list

    def get_report(self, app_folder):
        if self.splunky:
            index, title, emails, tags_map = self.load_app_config(app_folder=app_folder)
            if len(emails):
                header, instances = self.do_search(index=index, tags=tags_map)
                invalid_instances = self.filter_results(search_results=instances, tags_map=tags_map)
                invalid_instances = self.fix_utf8(list=invalid_instances)
                self.logger.debug(invalid_instances)
                report_html = self.create_report_from_template(header, invalid_instances, 'static/template_instance_alerts.html')
                self.send_emails(emails, title, report_html)
                self.__log(report_html)
            else:
                self.logger.error("No target emails defined")
        else:
            self.logger.error('Not connected to splunk')

    def create_report_from_template(self, header, rows, template):
        data = {
            'cloudreach_logo' : 'https://cr-splunk-1.cloudreach.co.uk:8000/en-US/static/app/cloudreach-modules/cloudreach-logo-smaller-transparent.png',
            'green_table_header' : header,
            'green_table_rows' : rows,
            }

        fr=open(template,'r')
        inputSource = fr.read()
        template = Template(inputSource).render(data)
        return template

    def __log(self, msg):
        with open( "instance_report.html", "w" ) as f:
            f.write( msg + "\n")

    def send_emails(self, emails, title, content):
        for email in emails:
            self.__send_email(to=email, title=title, html_body=content)

    def __send_email(self, to=None, BCC=None, html_body=None, title=None):
        message = Message(From=self.mailer_config['from'],To=to, BCC=BCC )
        message.Subject = title if title is not None else 'EC2 Instance Alert'
        message.Html = html_body

        mailer_url_data = self.mailer_config['mailserver'].split(':')

        sender = Mailer(host=mailer_url_data[0],
            port=mailer_url_data[1],
            use_tls=True if self.mailer_config['use_tls'] == '1' else False,
            usr=self.mailer_config['auth_username'],
            pwd=self.mailer_config['auth_password'])

        sender.send(message)