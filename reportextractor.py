from BeautifulSoup import BeautifulSoup

__author__ = 'jakub.zygmunt'
class ReportExtractor(object):

    def __init__(self, html):
        self.soup = BeautifulSoup(html)


    def __extractDataFromTable(self, table_id):
        table = []
        html_table = self.soup.find('div', {'id': table_id} )
        ths = [ str(t.findAll('span', {'class':'sortLabel'}).pop().contents[0]) for t in html_table.findAll('th') ]
        table.append(ths)
        for row in html_table.findAll('tr'):
            tds = row.findAll('td')
            if len(tds) > 0:
                table.append([ str(t.contents[0]) for t in tds ])

        return table

    def extract(self):

        singleValueHolder =  self.soup.find('div', {'id':'SingleValue_0_2_1'})
        total_amount = singleValueHolder.find('span').contents[0]
        yellow_table = self.__extractDataFromTable('CSimpleResultsTable_0_2_1')
        green_table = self.__extractDataFromTable('CSimpleResultsTable_1_1_1')
        blue_table = self.__extractDataFromTable('CSimpleResultsTable_2_1_1')

        return {'total_value':total_amount, 'yellow_table':yellow_table, 'green_table':green_table, 'blue_table':blue_table}







