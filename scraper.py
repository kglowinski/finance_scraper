'''This will take in a CSV list of ticker symbols, and should create a correctly
formatted table of information about each one.'''

import csv
import os
import sys

from bs4 import BeautifulSoup
from selenium import webdriver
from datetime import date

class ImproperSymbolException(Exception):
    '''Exception class which should occur if one of the symbols in the list is
    not of the expected format (right now, 5 characters only).'''
    pass

def main():
   
    tickers_uri = './test_files/combined_sec_list_jan_2014.csv'
    ticker_symbols_mf, ticker_symbols_etf = read_csv_list(tickers_uri)

    print(ticker_symbols_etf)
    print(len(ticker_symbols_etf))

    perf_url_mf = 'http://performance.morningstar.com/fund/performance-return.action?ops=p&p=total_returns_page&t='
    risk_url_mf = 'http://performance.morningstar.com/fund/ratings-risk.action?t='

    perf_url_etf = 'http://performance.morningstar.com/funds/etf/total-returns.action?t='
    risk_url_etf = 'http://performance.morningstar.com/funds/etf/ratings-risk.action?t='
    quote_url_etf = 'http://etfs.morningstar.com/quote?t='

    mf_dict = scrape_mf_pages(perf_url_mf, risk_url_mf, ticker_symbols_mf)
    etf_dict = scrape_etf_pages(quote_url_etf, perf_url_etf, risk_url_etf, ticker_symbols_etf)

    out_uri = './output_chart_combined.csv'
    print_to_csv(mf_dict, etf_dict, out_uri)

def scrape_etf_pages(quote_url_start, perf_url_start, risk_url_start, ticker_symbols):

    info_dict = {}

    driver = webdriver.PhantomJS()

    for symbol in ticker_symbols:
        
        print("Currently on: " + str(symbol))
        info_dict[symbol] = {}

        quote_url = quote_url_start + str(symbol)
        driver.get(quote_url)
        html = driver.page_source
        soup = BeautifulSoup(html)

        #Type
        etf_type = soup.find("span", {"id":"MorningstarCategory"}).text
        info_dict[symbol]['type'] = etf_type.strip()

        perf_url = perf_url_start + symbol
        driver.get(perf_url)
        html = driver.page_source
        soup = BeautifulSoup(html)

        #Full name
        name = soup.find("div", {"class": "r_title"}).find("h1").text
        info_dict[symbol]['name'] = name
        
        #Number of stars is the morningstar rating. Always in a span labeled the same way.
        star_label = soup.find("span", {"id": "star_span"})['class'][0]
        rating = star_label[len(star_label)-1]
        info_dict[symbol]['rating'] = rating
        
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
            try:
                year_perfs.append(float(perf))
            except ValueError:
                year_perfs.append('-')
        perf_years = [1, 3, 5, 10]

        info_dict[symbol]['performances'] = dict(zip(perf_years, year_perfs))
    
        #Now, need the risk data.
        risk_url = risk_url_start + symbol
        print("Currently looking at: " + risk_url)
        driver.get(risk_url)
        html = driver.page_source
        soup = BeautifulSoup(html)
        
        #Getting beta. But I'm getting lazy so it's now all in 1 line.
        while True:
            try:
                beta_ele = soup.find("div", {"id":"div_mpt_stats"}).find_all("tr")[5].find_all("td")[2]
            except IndexError:
                print "Trapped in loop ETF."
                driver.refresh()
                html = driver.page_source
                soup = BeautifulSoup(html)
                continue
            else:
                break
        beta = beta_ele.string
        
        #Getting sharpe ratio
        sharpe_ele = soup.find("div", {"id":"div_volatility"}).find_all("tr")[3].find_all("td")[2]
        sharpe = sharpe_ele.text
        info_dict[symbol]['sharpe_ratio'] = sharpe 

        for name, ele in [('beta', beta), ('sharpe_ratio', sharpe)]:
            try:
                info_dict[symbol][name] = float(ele)
            except ValueError:
                info_dict[symbol][name] = '-'

    return info_dict

def scrape_mf_pages(perf_url_start, risk_url_start, ticker_symbols):
    '''Main fuction which will get all relevant info, and dump it to a 2D
    dictionary- key is the symbol, maps to a dictionary where keys are info
    needed for output CSV.'''

    info_dict = {}

    driver = webdriver.PhantomJS()

    for symbol in ticker_symbols:
        
        print("Currently on: " + str(symbol))
        info_dict[symbol] = {}

        perf_url = perf_url_start + symbol
        print("Looking at URL: " + perf_url)

        driver.get(perf_url)
        html = driver.page_source
        soup = BeautifulSoup(html)

        ''' There's really only the one major table that we care about. 
        soup.find("table").find_all("tr") <- This will give us a list of
        table rows. These can then be searched through in more dept depending
        on what you're looking for.'''
        #Full name
        name = soup.find("div", {"class": "r_title"}).find("h1").text
        info_dict[symbol]['name'] = name

        #Type
        mf_type_set = soup.find_all("span", {"class":"databox"})
        final_type = mf_type_set[len(mf_type_set)-1]['name']
        info_dict[symbol]['type'] = final_type

        #Number of stars is the morningstar rating. Always in a span labeled the same way.
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

        print(year_perfs)

        info_dict[symbol]['performances'] = dict(zip(perf_years, year_perfs))

        #Now, need the risk data.
        risk_url = risk_url_start + symbol
        driver.get(risk_url)
        html = driver.page_source
        soup = BeautifulSoup(html)
        
        #Getting beta. But I'm getting lazy so it's now all in 1 line.
        #For some reason, this page doesn't always load correctly.
        while True:
            try:
                beta_ele = soup.find("div", {"id":"div_mpt_stats"}).find_all("tr")[5].find_all("td")[2]
            except IndexError:
                print("Trapped in loop MF!")
                driver.refresh()
                html = driver.page_source
                soup = BeautifulSoup(html)
                continue
            else:
                break

        beta = beta_ele.string

        #Getting sharpe ratio
        sharpe_ele = soup.find("div", {"id":"div_volatility"}).find_all("tr")[3].find_all("td")[2]
        sharpe = sharpe_ele.text

        for name, ele in [('beta', beta), ('sharpe_ratio', sharpe)]:
            try:
                info_dict[symbol][name] = float(ele)
            except ValueError:
                info_dict[symbol][name] = '-'

    return info_dict

def read_csv_list(uri):
    '''Function that should take in a CSV containing a list of 5-digit ticker
    symbols, and return a python list.'''

    symbol_list_mf = []
    symbol_list_etf = []
    count = 0

    with open(uri, 'rU') as symbol_file:

        csv_reader = csv.reader(symbol_file)
        while True:
            try:
                line = csv_reader.next()
                if line == []:
                    continue
                count += 1

                #Want to remove any whitespace that might have gotten in before
                #or after the symbol
                symbol = line[0].strip()

                #Want to make sure we have a symbol for which I know the page
                #structure.
                if len(symbol) not in range(3, 6):
                    raise ImproperSymbolException("At this time, the scraper can only \
                            deal with Mutual Funds and ETF's. As such, the ticker \
                            symbols passed in must all be 3-5 characters. The \
                            symbol %s on line %s does not qualify." % (symbol, count))

                elif len(symbol) == 5:
                    symbol_list_mf.append(symbol)
                #Note: this could be 3 or 4 characters.
                else:
                    symbol_list_etf.append(symbol)
            except StopIteration:
                break

    return symbol_list_mf, symbol_list_etf

def print_to_csv(mf_dict, etf_dict, out_uri):

    #Want to make sure that all of the same type are grouped together.
    #The outer key will be the type. The inner will be a list of the lines.
    grouped_lines = {}

    with open(out_uri, 'wb') as x_file:
        x_writer = csv.writer(x_file)

        x_writer.writerow(['Symbol', 'Name', 'Class', 'MStar Rating', '1 Year', '3 Year', '5 Year', '10 Year', '2009', '2010', '2011', '2012', '2013', 'Beta', 'Sharpe Ratio'])

        for cat_dict in [mf_dict, etf_dict]:
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

main()  
