import unittest
from dailyreport import DailyReport

__author__ = 'jakub.zygmunt'

class DailyReportTest(unittest.TestCase):
    def test_shouldReturnEmptyOnWrongSplunkHomePath(self):
        expectedList = []
        dr = DailyReport()
        appsWithConfig = dr.getApps()
        self.assertEquals(expectedList, appsWithConfig)


    def test_shouldReturnAppNamesWithDailyReportConfig(self):
        splunk_home = 'test_splunk'
        expectedItem = '%s/etc/apps/app1/local/dailyreport.conf' % splunk_home
        dr = DailyReport(splunk_home=splunk_home)
        appsWithConfig = dr.getApps()
        self.assertEquals(expectedItem, appsWithConfig.pop())