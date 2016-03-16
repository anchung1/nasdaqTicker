import urllib2
from bs4 import BeautifulSoup
import re
import pickle


class Nasdaq:
    def __init__(self):
        self.soup = None
        self.urls = []
        self.files = []
        self.mode = None
        self.current_index = 0
        self.max_pages = 0
        self.companies = None
        self.dict_file_name = 'nasdaq.txt'
        self.sym_lookup_url = 'http://www.nasdaq.com/symbol/'

    def next_soup(self):
        self.current_index = min(self.max_pages-1, self.current_index+1)
        self.assign_soup()

    def prev_soup(self):
        self.current_index = min(self.current_index - 1, 0)
        self.assign_soup()

    def assign_soup(self):
        try:
            if self.mode is 'file':
                self.soup = BeautifulSoup(open(self.files[self.current_index]), 'html.parser')
            else:
                page = urllib2.urlopen(self.urls[self.current_index]).read()
                self.soup = BeautifulSoup(page, 'html.parser')
        except IndexError:
            print 'assign soup index error'
            print self.current_index

    @staticmethod
    def write_file(page_name, content):
        with open(page_name, 'w') as myfile:
            myfile.write(content)

    def use_file(self, page):
        self.soup = BeautifulSoup(open(page), 'html.parser')
        self.urls = self.get_page_links()
        self.mode = 'file'

        self.files = ['page1']
        for (i, val) in enumerate(self.urls):
            self.files.append('page'+str(i+2) )

        self.max_pages = len(self.files)

    def use_url(self, url, save=False):
        content = urllib2.urlopen(url).read()
        self.soup = BeautifulSoup(content, 'html.parser')

        self.urls = self.get_page_links()
        self.urls.insert(0, url)
        self.mode = 'url'
        self.max_pages = len(self.urls)

        if save is True:
            page_num = 1
            self.write_file('page' + str(page_num), content)
            for page in self.urls:
                print 'processing', page
                content = urllib2.urlopen(page).read()
                page_num += 1
                self.write_file('page' + str(page_num), content)

    def print_soup(self):
        assert (self.soup is not None)
        print self.soup

    def get_company_keys(self):
        assert (self.soup is not None)
        thead = self.soup.select('div.genTable table thead')[0]

        keys = []
        th = thead.tr.th
        while th is not None:
            keys.append(th.a.text)
            th = th.find_next_sibling()

        return keys

    def get_company_info(self):
        assert (self.soup is not None)

        # unfortunately tbody tag is missing
        tr = self.soup.select('div.genTable table thead')[0].find_next_sibling()
        tr_values = []
        while tr is not None:
            td = tr.td
            td_values = []
            while td is not None:
                td_values.append(td.text.strip())
                td = td.find_next_sibling()
            tr_values.append(td_values)
            tr = tr.find_next_sibling()
            tr = tr.find_next_sibling()
        return tr_values

    def make_company_dict(self):
        keys = self.get_company_keys()
        total_dict = []

        for page in range(0, self.max_pages):
            print ('processing page', page)
            values = self.get_company_info()
            my_dict = map(lambda value: dict(zip(keys, value)), values)
            self.next_soup()
            map(lambda elem: total_dict.append(elem), my_dict)

        self.companies = total_dict
        return total_dict

    def get_page_links(self):
        pages = []
        pager = self.soup.select('div#pagerContainer li a#main_content_lb_LastPage')[0]['href']
        m = re.search('(.+)\&page=', pager)
        page = m.group(0)
        if page is None:
            return pages

        num_pages = int(pager.split('=').pop())
        for num in range(2, num_pages+1):
            pages.append(page + str(num))
        return pages

    def find_company_symbol(self, symbol, date=None):
        assert (self.companies is not None)

        try:
            company = filter(lambda elem: elem['Symbol'] == symbol, self.companies).pop(0)
        except IndexError:
            return None

        if date is not None:
            try:
                check_date = filter(lambda elem: elem['Date of Close Price'] == date, company['data'])
                if len(check_date) > 0:
                    print 'have data'
                    return company['data']
            except KeyError:
                return None

        try:
            urlfh = urllib2.urlopen(self.sym_lookup_url+symbol, timeout=10)
            page = urlfh.read()
            urlfh.close()
        except urllib2.URLError:
            return None

        soup = BeautifulSoup(page, 'html.parser')
        try:
            tr = soup.select('.genTable table tbody tr')[0]
        except IndexError:
            return None

        my_dict = {}
        while tr is not None:
            td = tr.td
            key = None
            value = None

            while td is not None:
                # print td
                if td.a is not None:
                    try:
                        td.span.extract()
                    except AttributeError:
                        pass
                    key = td.a.text.strip()
                else:
                    value = td.text.strip()
                td = td.find_next_sibling()

            if key is not None and value is not None:
                my_dict[key] = value

            tr = tr.find_next_sibling()

        try:
            date_item = filter(lambda item: item['Date of Close Price'] == my_dict['Date of Close Price'],
                               company['data'])
            if len(date_item) == 0:
                company['data'].append(my_dict)
            else:
                print 'have existing'
        except KeyError:
            company['data'] = []
            company['data'].append(my_dict)

        return company['data']

    def collect_closing(self, today=None):
        for i, elem in enumerate(self.companies):
            print ('%s/%s' % (i, len(self.companies)), elem['Symbol'])
            self.find_company_symbol(elem['Symbol'], today)
            if i > 0 and (i % 100) == 0:
                self.save_dict_file()

        self.save_dict_file()

    def save_dict_file(self):
        print ('save_dict_file')
        with open(self.dict_file_name, 'wb') as handle:
            pickle.dump(self.companies, handle)

    def read_dict_file(self):
        with open(self.dict_file_name, 'rb') as handle:
            self.companies = pickle.loads(handle.read())
        # print len(self.companies)

    def get_today(self):
        data = self.find_company_symbol('MSFT')[-1]
        return data['Date of Close Price']

    @staticmethod
    def print_ticker(dict_list):

        for sym_dict in dict_list:
            print '====================='
            print sym_dict['Name']
            print sym_dict['Country']
            print sym_dict['Symbol']
            print sym_dict['Subsector']
            print sym_dict['IPO Year']
            print sym_dict['Market Cap']
            # print sym_dict['ADR TSO']
            print '=====================\n'


if __name__ == '__main__':
    nasdaq = Nasdaq()

    # use this to start database
    # nasdaq.use_url('http://www.nasdaq.com/screening/companies-by-industry.aspx?pagesize=200&exchange=NASDAQ')
    # nasdaq.use_file('page1')
    # nasdaq.make_company_dict()
    # nasdaq.save_dict_file()

    # read back created data
    nasdaq.read_dict_file()
    today = nasdaq.get_today()
    nasdaq.collect_closing(today)

    # print nasdaq.find_company_symbol('FCCY')
    # print nasdaq.find_company_symbol('MSFT')
    # data = nasdaq.find_company_symbol('ZSAN')
    # print data.pop()
    # nasdaq.save_dict_file()


    # nasdaq.find_company_symbol('BPTH')


    # nasdaq.use_file('page')

    #nasdaq.use_url('http://www.nasdaq.com/screening/companies-by-industry.aspx?pagesize=200&exchange=NASDAQ', save=True)

    # nasdaq.print_soup()

    # my_dict = nasdaq.get_company_dict()
    # nasdaq.print_ticker(my_dict)

    # nasdaq.page_links()

