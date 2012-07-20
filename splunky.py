import ConfigParser
import re
import csv
import splunklib
from splunklib import client, results, testlib

__author__ = 'jakub.zygmunt'
class Splunky(object):
    def __init__(self, username=None, password=None, host=None, port=None, config_file=None, app=None):
        self.service = None
        if config_file:
            config = self.__load_from_config(config_file=config_file)
        else:
            config = { 'username': username, 'password': password, 'host': host, 'port': port}

        if app is not None:
            config['app'] = app

        try:
            self.service = client.connect(**config)
        except Exception, e:
            raise SplunkyCannotConnect(message=e)



    def __load_from_config(self, config_file):
        parser = ConfigParser.SafeConfigParser()
        try:
            parser.read(config_file)
            config_dict = {x[0]:x[1] for x in parser.items('splunk')}
        except (TypeError, ConfigParser.NoSectionError, ConfigParser.MissingSectionHeaderError):
            config_dict = dict()
        return config_dict

    def search(self, search=None, saved_search=None):
        jobs = self.service.jobs
        job = None
        results = []
        try:
            if search is not None:
                job = jobs.create(search, exec_mode="blocking", max_count=50000)
            if saved_search is not None:
                job = saved_search.dispatch()
            if job:
                results = self.get_results(job)
        except splunklib.binding.HTTPError:
            # wrong search ?
            pass
        return results

    def get_results(self, job):
        testlib.wait(job, lambda job: bool(int(job['isDone'])))
        reader = splunklib.results.ResultsReader(job.results(count=0))
        output = []
        for kind, result in reader:
            if 'preview' not in result.keys():
                if '$offset' in result.keys():
                    del result['$offset']
                output.append(result)
        return output

    def output_to_csv(self, search, csv_file):
        results = self.search(search=search)
        header = self.get_header(search=search)
        self.__list_dict_to_file(results=results, header=header, outfile=csv_file)

    def __list_dict_to_file(self, results, header, outfile):
        csv_writer = csv.writer(open(outfile, 'w'), delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        csv_writer.writerow(header)
        for dict_row in results:
            csv_row = []
            for key in header:
                try:
                    csv_row.append(dict_row[key])
                except KeyError:
                    csv_row.append('')
            csv_writer.writerow(csv_row)

    @staticmethod
    def get_table_fields(search):
        header = []
        match = re.search(r'.*\| ?table ([a-zA-Z_0-9, ]+)', search)
        if match:
            str = match.group(1)
            fields = re.findall('([a-zA-Z_0-9]+)+', str)
            for f in fields:
                header.append(f)
        return header

    @staticmethod
    def get_renames(search):
        renames = {}
        match = re.search(r'.*\| ?rename ([a-zA-Z0-9_, "()\-]+)', search)
        if match:
            str = match.group(1)
            fields = re.findall('([a-zA-Z0-9_]+) as (?:"([^"]+)"|([a-zA-Z0-9_]+))', str)
            for f in fields:
                key = f[0]
                value = f[1] if f[1] != '' else f[2]
                renames[key] = value
        return renames


    @staticmethod
    def get_header(search):
        header = Splunky.get_table_fields(search)
        if len(header) > 0:

            renames = Splunky.get_renames(search)
            keys_renames = renames.keys()
            if len(keys_renames) > 0:
                new_header = []
                for col in header:
                    new_column = renames[col] if col in keys_renames else col
                    new_header.append(new_column)
                header = new_header

        return header



class SplunkyCannotConnect(Exception):
    def __init__(self, message):
        self.message=message
