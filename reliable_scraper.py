import csv
import os
import sys

from bs4 import BeautifulSoup
from selenium import webdriver
from datetime import date, datetime

'''So now, instead of passing an entire list of symbols directly to the scraper,
want to have an outer function that will loop once for each symbol. That way,
can have it refresh when it's encountering the value errors that mean that
the page hasn't loaded. It shows up on the page as u\u2014 when it's missing a
value.'''

DRIVER = webdriver.PhantomJS(executable_path='C:\phantomjs\phantomjs-1.9.8-windows\phantomjs.exe')

class BlankPullError(Exception):
    '''Want an exception class that we can throw if we "pull data" but it's a blank.'''
    pass


def main():

    ticker_symbols_etf = ['IVV', 'IJS', 'TIP', 'ITOT', 'OEF']
    etf_dict = scrape_etf_pages(ticker_symbols_etf)
    
    print "My etf dict is currently..." 
    print etf_dict
    
    ticker_symbols_mf = ['NOIEX', 'TWVLX', 'STVTX', 'BVEFX', 'TGIGX', 'BPAVX', 'FVDFX', 'FLVEX', 'SSHFX', 'BWLIX', 'FSTKX', 'FSTRX', 'FVDFX', 'FLVEX']
    mf_dict = scrape_mf_pages(ticker_symbols_mf)
    
    print "My mf dict is currently..." 
    print mf_dict

    curr_time = datetime.now().strftime('%I_%M_%S')
    out_uri = '.\compiled_sec_info_' + curr_time + '.csv'
    
    create_output_files(out_uri, etf_dict, mf_dict)
    
def nav_to_url(url):
    global DRIVER
    DRIVER.get(url)
    html = DRIVER.page_source
    return BeautifulSoup(html)

    
def create_output_files(uri, etf_dict, mf_dict):

    #Want to make sure that all of the same type are grouped together.
    #The outer key will be the type. The inner will be a list of the lines.
    grouped_lines = {}

    with open(uri, 'wb') as x_file:
        x_writer = csv.writer(x_file)

        x_writer.writerow(['Symbol', 'Name', 'Class', 'MStar Rating', '1 Year', '3 Year', '5 Year', '10 Year', '2009', '2010', '2011', '2012', '2013', 'Beta', 'Sharpe Ratio'])

        #Adding everything into a single dictionary.
        cat_dict = dict(etf_dict, **mf_dict)
        for symbol in cat_dict:

            curr = cat_dict[symbol]

            line = []
            line.append(symbol)
            line.append(curr['name'])
            line.append(curr['type'])
            line.append(curr['rating'])
            #The performances
            line.append(curr['performances'][1])
            line.append(curr['performances'][3])
            line.append(curr['performances'][5])
            line.append(curr['performances'][10])
            #Decile rankings
            curr_year = date.today().year
            past_5_yrs = range(curr_year-5, curr_year)
            temp_list = []
            for year in past_5_yrs:
                line.append(curr['decile_rank'][year])
            line.append(curr['beta'])
            line.append(curr['sharpe_ratio'])

            trigger = None

            words = ['large', 'small', 'mid', 'bond']
            for w in words:
                if w in curr['type'].lower():
                    trigger = w
                    break
            
            if trigger is not None:
                if trigger in grouped_lines.keys():
                    grouped_lines[trigger].append(line)
                else:
                    grouped_lines[trigger] = [line]
            else:
                if curr['type'] in grouped_lines.keys():
                    grouped_lines[curr['type']].append(line)
                else:
                    grouped_lines[curr['type']] = [line]

        #Now we have groups of lines by type.
        #Want to print them into the CSV
        for group_list in grouped_lines.values():
            #Now that we have a grouping, print all in there.
            for line in group_list:
                x_writer.writerow(line)

            x_writer.writerow([])

def scrape_mf_pages(symbols):
    
    info_dict = {}
    perf_prefix = 'http://performance.morningstar.com/fund/performance-return.action?ops=p&p=total_returns_page&t='
    risk_prefix = 'http://performance.morningstar.com/fund/ratings-risk.action?t='
    
    for symbol in symbols:
        info_dict[symbol] = {}
        print("Currently on: " + str(symbol))
        perf_url = perf_prefix + symbol
        risk_url = risk_prefix + symbol
        
        while True:
            try:
                #running the three parts, wait for it to break, reload the corresponding url
                get_mf_perf_values(perf_url, info_dict, symbol)
                get_mf_risk_values(risk_url, info_dict, symbol)
                break
                
            except (ValueError, BlankPullError, IndexError):
                print "Looping for " + str(symbol)
                continue
                
    return info_dict

def get_mf_risk_values(url, info_dict, symbol):
    
    soup = nav_to_url(url)
    
    #Get Beta
    beta_ele = soup.find("div", {"id":"div_mpt_stats"}).find_all("tr")[5].find_all("td")[2]
    beta = beta_ele.string

    #Getting sharpe ratio
    sharpe_ele = soup.find("div", {"id":"div_volatility"}).find_all("tr")[3].find_all("td")[2]
    sharpe = sharpe_ele.text
    
    for name, ele in [('beta', beta), ('sharpe_ratio', sharpe)]:
        if ele != u'u\2014':
            try:
                info_dict[symbol][name] = float(ele)
            except ValueError:
                info_dict[symbol][name] = '-'
        else:
            raise BlankPullError
    
def get_mf_perf_values(url, info_dict, symbol):
    
    soup = nav_to_url(url)
    
    #Full name
    name = soup.find("div", {"class": "r_title"}).find("h1").text
    info_dict[symbol]['name'] = name

    #Type, will give most recent type (YTD)
    mf_type_set = soup.find_all("span", {"class":"databox"})
    final_type = mf_type_set[len(mf_type_set)-1]['name']
    info_dict[symbol]['type'] = final_type
    
    #MStars
    star_label = soup.find("span", {"id": "star_span"})['class'][0]
    rating = star_label[len(star_label)-1]
    info_dict[symbol]['rating'] = rating
    
    #Get the decile rank in category of the last 5 years.
    #Know that we want the second to last row, and don't want the newlines
    info_dict[symbol]['decile_rank'] = {}
    first_table_rows = soup.find("table").find_all("tr")
    decile_row = first_table_rows[len(first_table_rows)-2].find_all("td")
    decile_row = list(decile_row)
    ranks = map(lambda ele: ele.string, decile_row)
    ranks = ranks[len(ranks)-6:len(ranks)-1]

    curr_year = date.today().year
    for i, year in enumerate(range(curr_year-5, curr_year)):
        try:
            info_dict[symbol]['decile_rank'][year] = float(ranks[i])
        except ValueError:
            info_dict[symbol]['decile_rank'][year] = '-'
    
    
    
    #Want the performances for 1 year, 3 year, 5 year, and 10 year.
    perf_row = soup.find_all("table")[1].find_all("tr")[1].find_all("td")
    year_perfs_any = map(lambda l: l.string, perf_row[len(perf_row)-5:len(perf_row)-1])
    year_perfs = []
    for perf in year_perfs_any:
        try:
            year_perfs.append(float(perf))
        except ValueError:
            year_perfs.append('-')
    perf_years = [1, 3, 5, 10]
    
    info_dict[symbol]['performances'] = dict(zip(perf_years, year_perfs))
    
def scrape_etf_pages(symbols):

    info_dict = {}
    perf_prefix = 'http://performance.morningstar.com/funds/etf/total-returns.action?t='
    risk_prefix = 'http://performance.morningstar.com/funds/etf/ratings-risk.action?t='
    quote_prefix = 'http://etfs.morningstar.com/quote?t='
    portfolio_prefix = 'http://portfolios.morningstar.com/fund/summary?t='

    for symbol in symbols:
        info_dict[symbol] = {} 
        print("Currently on: " + str(symbol))
        perf_url = perf_prefix + symbol
        risk_url = risk_prefix + symbol
        quote_url = quote_prefix + symbol
        portfolio_url = portfolio_prefix + symbol

        while True:
            try:
                #running the three parts, wait for it to break, reload the corresponding url
                get_type(quote_url, info_dict, symbol)
                get_e_risk_values(risk_url, info_dict, symbol)
                get_e_perf_values(perf_url, info_dict, symbol)
                get_e_port_values(portfolio_url, info_dict, symbol)
                break
                
            except (ValueError, BlankPullError, IndexError):
                print "Looping for " + str(symbol)
                continue

    return info_dict

def get_type(url, info_dict, symbol):
    '''Get the type and star rating.'''

    soup = nav_to_url(url)

    #Type
    sec_type = soup.find("span", {"id":"MorningstarCategory"}).text.strip()
    if sec_type != u'u\2014':
        info_dict[symbol]['type'] = sec_type.strip()
    else:
        raise BlankPullError
    
    #MStars
    star_label = soup.find("span", {"id":"star_span"})['class'][0]
    rating = star_label[len(star_label)-1]
    info_dict[symbol]['rating'] = rating

def get_e_risk_values(url, info_dict, symbol):
    '''This should give beta and the sharpe ratio.''' 
    
    soup = nav_to_url(url)

    #Getting beta. But I'm getting lazy so it's now all in 1 line.
    #Removing the index error, and adding to conds to relaod the whole thing.
    beta_ele = soup.find("div", {"id":"div_mpt_stats"}).find_all("tr")[5].find_all("td")[2]
    beta = beta_ele.string
    
    #Getting sharpe ratio
    sharpe_ele = soup.find("div", {"id":"div_volatility"}).find_all("tr")[3].find_all("td")[2]
    sharpe = sharpe_ele.text
    info_dict[symbol]['sharpe_ratio'] = sharpe 

    for name, ele in [('beta', beta), ('sharpe_ratio', sharpe)]:
        if ele != u'u\2014':
            try:
                info_dict[symbol][name] = float(ele)
            except ValueError:
                info_dict[symbol][name] = '-'
        else:
            raise BlankPullError
def get_e_perf_values(url, info_dict, symbol):
    
    soup = nav_to_url(url)
    
    #Full name
    name = soup.find("div", {"class": "r_title"}).find("h1").text
    info_dict[symbol]['name'] = name
    
    #Get the price ranking
    info_dict[symbol]['decile_rank'] = {}

    table = soup.find("tbody").find_all("tr")
    row_data = map(lambda l: l.text, table[len(table)-2].find_all("td"))
    rel_rank_data = row_data[len(row_data)-6:len(row_data)-1]
   
    temp_list = []
    curr_year = date.today().year
    for i, year in enumerate(range(curr_year-5, curr_year)):
        try:
            temp_list.append((year, rel_rank_data[i]))
            info_dict[symbol]['decile_rank'][year] = float(rel_rank_data[i])
        except ValueError:
            info_dict[symbol]['decile_rank'][year] = '-'

    print("%s : %s" % (symbol, temp_list))

    #Get the 1, 3, 5, 10 year performances
    perf_ele = soup.find_all("table")[1].find_all("tr")[1].find_all("td")
    year_perfs_any = map(lambda l: l.text, perf_ele)[len(perf_ele)-5:len(perf_ele)-1]
    
    year_perfs = []
    for perf in year_perfs_any:
        print perf
    
        try:
            year_perfs.append(float(perf))
        except ValueError:
            year_perfs.append('-')
    perf_years = [1, 3, 5, 10]

    info_dict[symbol]['performances'] = dict(zip(perf_years, year_perfs))

def get_e_port_values(url, info_dict, symbol):

    soup = nav_to_url(url)

    #Price/Book Value.
    metric_table = soup.find_all("table", {"class": "r_table1 text2"})[2].find("tbody")
    pb_value = metric_table.find_all("tr")[3].find("td").text
    
    #Price/Earnings Value
    pe_value = metric_table.find_all("tr")[1].find("td").text
    
    for name, metric in [("price_to_book", pb_value), ("price_to_earn", pe_value)]:
        if metric != u'u\2014':
            try:
                info_dict[symbol][name] = float(metric)
            except ValueError:
                info_dict[symbol][name] = '-'
        else:
            raise BlankPullError 
    
main()
