import unittest
from dailyreport import DailyReport

__author__ = 'jakub.zygmunt'

class DailyReportTest(unittest.TestCase):
    def test_shouldReturnEmptyOnWrongSplunkHomePath(self):
        expectedList = []
        dr = DailyReport()
        appsWithConfig = dr.get_apps()
        self.assertEquals(expectedList, appsWithConfig)


    def test_shouldReturnAppNamesWithDailyReportConfig(self):
        splunk_home = 'test_splunk'
        expectedItem = '%s/etc/apps/app1/local/dailyreport.conf' % splunk_home
        dr = DailyReport(splunk_home=splunk_home)
        appsWithConfig = dr.get_apps()
        self.assertEquals(expectedItem, appsWithConfig.pop())

    def test_shouldReturnNoneWhenBaseUrlIsNotSet(self):
        expectedUrl = None
        dr = DailyReport()
        outputUrl = dr.get_url_to_homepage('app_folder')
        self.assertEquals(expectedUrl, outputUrl)

    def test_shouldReturnLinkToHomepage(self):
        expectedUrl = 'http://127.0.0.1:8000/en-US/app/app1/awsManagedServicesHomepage'
        splunk_home = 'test_splunk'
        inputString = '%s/etc/apps/app1/local/dailyreport.conf' % splunk_home

        dr = DailyReport(splunk_home=splunk_home, base_url='http://127.0.0.1:8000/')
        outputUrl = dr.get_url_to_homepage(inputString)
        self.assertEquals(expectedUrl, outputUrl)

