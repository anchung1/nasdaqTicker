import urllib2
from bs4 import BeautifulSoup
import re
import pickle
import sys
import argparse


class Nyse:
    def __init__(self):
        self.soup = None
        self.urls = []
        self.files = []
        self.mode = None
        self.current_index = 0
        self.max_pages = 0
        self.companies = None
        self.dict_file_name = 'nyse.txt'
        self.sym_lookup_url = 'http://www.nasdaq.com/symbol/'
        self.nyse_csv = 'nyse.csv'

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

    def make_company_dict_csv(self):
        f = open(self.nyse_csv, 'r')
        key = []
        value = []
        self.companies = []
        for line in f:
            if len(key) is 0:
                key = line.strip().replace('\"', '').split(',')
                key.pop()
                continue
            else:
                # corner case "Zweig Total Return Fund, Inc. (The)",
                # separating on comma only also separates Fund and Inc
                value = line.strip().split('",')
                value.pop()
                value = map(lambda elem: elem.replace('\"', '').strip(), value)

            self.companies.append(dict(zip(key, value)))
        # print self.companies[-1]

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
            print 'No company data.  Bail'
            return None

        # print 'company',company

        if date is not None:
            try:
                check_date = filter(lambda elem: elem['date'] == date, company['data'])
                if len(check_date) > 0:
                    print 'have data'
                    return company['data']
            except KeyError:
                # print 'KeyError.'
                pass

        try:
            urlfh = urllib2.urlopen(self.sym_lookup_url+symbol, timeout=10)
            page = urlfh.read()
            urlfh.close()
        except urllib2.URLError:
            print 'URLError.  Bail'
            return None

        # print page
        soup = BeautifulSoup(page, 'html.parser')

        # print 'collecting data for symbol', symbol
        my_dict = {}
        try:
            price = soup.select('#qwidget_lastsale').pop().text.strip()
            my_dict['price'] = price
            # print 'price', price

            prefix = ''
            div = soup.select('#qwidget-arrow .arrow-green')
            if len(div) > 0:
                prefix = '+'

            div = soup.select('#qwidget-arrow .arrow-red')
            if len(div) > 0:
                prefix = '-'

            netchange = prefix + soup.select('#qwidget_netchange').pop().text.strip()
            percent = prefix + soup.select('#qwidget_percent').pop().text.strip()

            my_dict['net_change'] = netchange
            my_dict['percent_change'] = percent
            # print netchange, percent

            date = soup.select('#qwidget_markettime').pop().text.strip()
            my_dict['date'] = date
            #print 'date', date

            volume = soup.select('#'+symbol.upper().strip()+'_Volume').pop().text.strip()
            avg_volume = soup.select('#shares-traded table tr:nth-of-type(2) td > span').pop().text.strip()

            my_dict['volume'] = volume
            my_dict['avg_volume'] = avg_volume
            # print 'volume', volume
            # print 'avg_volume', avg_volume

            prev_close = soup.select('#shares-traded > div:nth-of-type(2) table tr td:nth-of-type(2)').pop().text.strip()
            my_dict['prev_close'] = prev_close
            #print 'prev_close', prev_close

            target = soup.select('#shares-traded > div:nth-of-type(2) table tr:nth-of-type(2) td:nth-of-type(2)').pop().text.strip()
            my_dict['target'] = target
            # print 'target', target

            market_cap = soup.select('#shares-traded > div:nth-of-type(2) table tr:nth-of-type(3) td:nth-of-type(2)').pop().text.strip()
            my_dict['market_cap'] = market_cap
            # print 'market_cap', market_cap

            # high = soup.select('.infoTable .trading-activitiy table tr:nth-of-type(2) td')
            high = soup.select('.row .infoTable table .color-green td')
            # print high
            high_today = high.pop(0).text.strip()
            high_year = high.pop().text.strip()

            my_dict['high_today'] = high_today
            my_dict['high_year'] = high_year
            # print 'high_today', high_today
            # print 'high_year', high_year

            low = soup.select('.row .infoTable table .color-red td')
            low_today = low.pop(0).text.strip()
            low_year = low.pop().text.strip()

            my_dict['low_today'] = low_today
            my_dict['low_year'] = low_year
            # print 'low_today', low_today
            # print 'low_year', low_year

        except IndexError:
            print 'INDEX ERROR'
            return None

        # print my_dict

        try:
            date_item = filter(lambda item: item['date'] == my_dict['date'],
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
        print today

        for i, elem in enumerate(self.companies):
            print ('%s/%s' % (i, len(self.companies)), elem['Symbol'])
            self.find_company_symbol(elem['Symbol'], today)
            if i > 0 and (i % 100) == 0:
                self.save_dict_file()
                # break

        self.save_dict_file()

    def save_dict_file(self):
        print ('save_dict_file')
        with open(self.dict_file_name, 'wb') as handle:
            pickle.dump(self.companies, handle)

    def read_dict_file(self):
        with open(self.dict_file_name, 'rb') as handle:
            self.companies = pickle.loads(handle.read())
        print len(self.companies)
        # print self.companies[-1]

    def get_today(self, symbol):
        data = self.find_company_symbol(symbol)[-1]
        # print data
        return data['date']

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
    market = Nyse()
    print sys.argv

    parser = argparse.ArgumentParser()
    parser.add_argument('-type', default='nyse')
    parser.add_argument('-dict', default='None')
    parser.add_argument('-collect', default='None')

    args = parser.parse_args()

    if args.type == 'nasdaq':
        market.nyse_csv = 'nasdaq.csv'
        market.dict_file_name = 'nasdaq.txt'
        sample_symbol = 'MSFT'
    else:
        market.nyse_csv = 'nyse.csv'
        market.dict_file_name = 'nyse.txt'
        sample_symbol = 'DDD'

    if args.dict == 'yes':
        market.make_company_dict_csv()
        market.save_dict_file()

    if args.collect == 'yes':
        market.read_dict_file()
        today = market.get_today(sample_symbol)
        market.collect_closing(today)


    # market.read_dict_file()

    # print args.type
    # print args.mode

    # use this to start database
    # nyse.make_company_dict_csv()
    # nyse.save_dict_file()


    # read back created data
    # nyse.read_dict_file()
    # today = nyse.get_today('DDD')
    # nyse.collect_closing(today)

    # print nyse.find_company_symbol('FCCY')
    # print nyse.find_company_symbol('MSFT')
    # data = nyse.find_company_symbol('ZSAN')
    # print data.pop()
    # nyse.save_dict_file()


    # nyse.find_company_symbol('BPTH')


    # nyse.use_file('page')

    #nyse.use_url('http://www.nyse.com/screening/companies-by-industry.aspx?pagesize=200&exchange=nyse', save=True)

    # nyse.print_soup()

    # my_dict = nyse.get_company_dict()
    # nyse.print_ticker(my_dict)

    # nyse.page_links()

