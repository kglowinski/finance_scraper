import requests
import csv

from datetime import datetime, date
from bs4 import BeautifulSoup as bs
from multiprocessing import Pool, freeze_support

class CorruptPullError(Exception):
    '''Want an exception class that we can throw if we "pull data" but it's a blank.'''
    pass

def get_stats():
    
    symbols = create_input_list('.\\combined_in.csv')
    
    pool = Pool(4)
    results = pool.map(return_sec_info, symbols)
    '''results = []
    for symbol in symbols:
        results.append(return_sec_info(symbol))
    '''
    print results
    curr_date_time = datetime.now().strftime('%m-%d-%y_[%H_%M_%S]')
    out_uri = '.\scraped_info_out_' + curr_date_time + '.csv'
    create_output_file(out_uri, results)
 
def create_input_list(uri):
    '''Function that should take in a CSV containing a list of ticker
    symbols, and return a python list.'''

    symbol_list = []
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
                else:
                    symbol_list.append(symbol)
                
            except StopIteration:
                break

    return symbol_list
 
def return_sec_info(symbol):

    print symbol

    while True:
        try: 
            if 3 <= len(symbol) < 5:
                info_dict = scrape_etf_info(symbol)
            else:
                info_dict = scrape_mf_info(symbol) 
            return info_dict

        except CorruptPullError:
            #These will only happen on the summary MS pages. Should only need to raise
            #corrupt exceptions for those. Elsewhere where looking @ text pages, blanks
            #are legit.
            print "Looping for " + str(symbol)
            continue
            
def get_soup(url, symbol):

    a = {'ops':'clear', 't':symbol}
    response = requests.get(url, params=a)
    
    return bs(response.text)
    
def scrape_etf_info(symbol):
    
    info_dict = {'symbol': symbol}
    
    quote_url = 'http://etfs.morningstar.com/quote'
    category_url = 'http://etfs.morningstar.com/quote-banner'
    historical_url = 'http://performance.morningstar.com/Performance/cef/trailing-total-returns.action?'
    decile_url = 'http://performance.morningstar.com/Performance/cef/performance-history.action?'
    port_url = 'http://portfolios.morningstar.com/fund/summary?'
    beta_url = 'http://performance.morningstar.com/RatingRisk/fund/mpt-statistics.action?'
    sharpe_url = 'http://performance.morningstar.com/RatingRisk/fund/volatility-measurements.action?'
    
    name, rating = get_m_star_rating(quote_url, symbol)
    info_dict['m_star'], info_dict['name'] = rating, name
    
    category = get_category(category_url, symbol, "id")
    info_dict['category'] = category
    
    hist_dict = get_historical_info(historical_url, symbol)
    info_dict['performance'] = hist_dict
    
    decile_dict = get_decile_ranks(decile_url, symbol, 7)
    info_dict['ranks'] = decile_dict
    
    beta = get_beta(beta_url, symbol)
    sharpe = get_sharpe(sharpe_url, symbol)
    info_dict['beta'], info_dict['sharpe'] = beta, sharpe
    
    #Bonds don't have a price/earnings or price/book
    if "bond" in category.lower():
        info_dict['p2e'], info_dict['p2b'] = '-', '-'
    else:
        #Going to return a tuple here, since we just have the two things.
        pe_and_p2b = get_earnings_and_book(port_url, symbol)
        info_dict['p2e'], info_dict['p2b'] = pe_and_p2b
    
    return info_dict

def scrape_mf_info(symbol):   
    
    info_dict = {'symbol': symbol}
    
    quote_url = 'http://quotes.morningstar.com/fund/f?'
    category_url = 'http://quotes.morningstar.com/fund/c-header?'
    historical_url = 'http://performance.morningstar.com/Performance/fund/trailing-total-returns.action?'
    decile_url = 'http://performance.morningstar.com/Performance/fund/performance-history-1.action?'
    port_url = 'http://portfolios.morningstar.com/fund/summary?'
    beta_url = 'http://performance.morningstar.com/RatingRisk/fund/mpt-statistics.action?'
    sharpe_url = 'http://performance.morningstar.com/RatingRisk/fund/volatility-measurements.action?'
    
    name, rating = get_m_star_rating(quote_url, symbol)
    info_dict['m_star'], info_dict['name'] = rating, name
    
    category = get_category(category_url, symbol, "vkey")
    info_dict['category'] = category
    
    hist_dict = get_historical_info(historical_url, symbol)
    info_dict['performance'] = hist_dict
    
    decile_dict = get_decile_ranks(decile_url, symbol, 6)
    info_dict['ranks'] = decile_dict
    
    beta = get_beta(beta_url, symbol)
    sharpe = get_sharpe(sharpe_url, symbol)
    info_dict['beta'], info_dict['sharpe'] = beta, sharpe
    
    #Bonds don't have a price/earnings or price/book
    if "bond" in category.lower():
        info_dict['p2e'], info_dict['p2b'] = '-', '-'
    else:
        #Going to return a tuple here, since we just have the two things.
        pe_and_p2b = get_earnings_and_book(port_url, symbol)
        info_dict['p2e'], info_dict['p2b'] = pe_and_p2b
    
    return info_dict
    
def get_m_star_rating(url, symbol):
    
    soup = get_soup(url, symbol)
    m_string = soup.find("span", {"id": "star_span"})
    #Puts the class return into a list, [0] gets the single element in that list.
    snippet = m_string.get("class")[0]
    stars = snippet[len(snippet)-1]
    
    name = soup.find("div", {"class": "r_title"}).find("h1").text
    
    return name, stars
    
def get_category(url, symbol, search_key):

    soup = get_soup(url, symbol)
    #Taking in search key since ETFs use "id" and MFs use "vkey"
    #Using strip because MF returns with newlines otherwise.
    cat = soup.find("span", {search_key: "MorningstarCategory"}).text.strip()
    
    return cat
    
def get_historical_info(url, symbol):
    
    soup = get_soup(url, symbol)
    
    perf_years = [1, 3, 5, 10]
    year_perfs = map(lambda x: x.text, soup.find_all("tr")[1].find_all("td")[5:10])
    
    perf_dict = {}
    for i, year in enumerate(perf_years):
        try:
            perf_dict[year] = float(year_perfs[i])
        except ValueError:
            perf_dict[year] = '-'
    
    return perf_dict

def get_decile_ranks(url, symbol, row):
    #Taking in a row number because etf page uses row 7, and MF uses 6
    
    soup = get_soup(url, symbol)
    headers = soup.find_all("tr")[0].find_all("th")
    years = map(lambda x: x.text, headers[len(headers)-6:len(headers)-1])
    
    #Having an issue with it not fully loading.
    try:
        ranks = soup.find_all("tr")[row].find_all("td")
    except IndexError:
        raise CorruptPullError
    deciles = map(lambda x: x.text, ranks[5:10])
    
    yearly_rank = {}
    for i, year in enumerate(years):
        try:
            yearly_rank[year] = int(deciles[i])
        except ValueError:
            yearly_rank[year] = '-'
    
    return yearly_rank

def get_earnings_and_book(url, symbol):
    soup = get_soup(url, symbol)
    
    table_rows = soup.find_all("table", {"class": "r_table1 text2"})[1].find_all("tr")
    
    #Second item is against the benchmark index. Going to use that.
    #Sometimes pulls too fast, so no data. 
    try:
        price_to_earn = float(table_rows[3].find_all("td")[1].text)
        price_to_book = float(table_rows[5].find_all("td")[1].text)
    except ValueError:
        raise CorruptPullError
    
    return (price_to_earn, price_to_book)

def get_beta(url, symbol):
    soup = get_soup(url, symbol)
    
    try:
        beta = float(soup.find_all("tr")[9].find_all("td")[2].text)
    except ValueError:
        #Because we're pulling from text page, know that blanks are legit.
        beta = '-'
    return beta
    
def get_sharpe(url, symbol):
    soup = get_soup(url, symbol)
    
    try:
        sharpe = float(soup.find_all("tr")[3].find_all("td")[2].text)
    except ValueError:
        #Because we're pulling from text page, know that blanks are legit.
        sharpe = '-'
    return sharpe
    
def create_output_file(uri, results_list):

    #Want to make sure that all of the same type are grouped together.
    #The outer key will be the type. The inner will be a list of the lines.
    grouped_lines = {}

    with open(uri, 'wb') as x_file:
        x_writer = csv.writer(x_file)

        x_writer.writerow(['Symbol', 'Name', 'Class', 'MStar Rating', '1 Year', '3 Year', '5 Year', '10 Year', '2010', '2011', '2012', '2013', '2014', 'Beta', 'Sharpe Ratio', 'P2Earn', 'P2Book'])

        for info_dict in results_list:

            line = []
            line.append(info_dict['symbol'])
            line.append(info_dict['name'])
            line.append(info_dict['category'])
            line.append(info_dict['m_star'])
            #The performances
            line.append(info_dict['performance'][1])
            line.append(info_dict['performance'][3])
            line.append(info_dict['performance'][5])
            line.append(info_dict['performance'][10])
            #Decile rankings
            curr_year = date.today().year
            past_5_yrs = range(curr_year-5, curr_year)
            temp_list = []
            for year in past_5_yrs:
                line.append(info_dict['ranks'][str(year)])
            line.append(info_dict['beta'])
            line.append(info_dict['sharpe'])
            line.append(info_dict['p2e'])
            line.append(info_dict['p2b'])
            
            trigger = None

            words = ['large', 'small', 'mid', 'bond']
            for w in words:
                if w in info_dict['category'].lower():
                    trigger = w
                    break
            
            if trigger is not None:
                if trigger in grouped_lines.keys():
                    grouped_lines[trigger].append(line)
                else:
                    grouped_lines[trigger] = [line]
            else:
                if info_dict['category'] in grouped_lines.keys():
                    grouped_lines[info_dict['category']].append(line)
                else:
                    grouped_lines[info_dict['category']] = [line]

        #Now we have groups of lines by category.
        #Want to print them into the CSV
        for group_list in grouped_lines.values():
            #Now that we have a grouping, print all in there.
            for line in group_list:
                x_writer.writerow(line)

            x_writer.writerow([])
    
if __name__ ==  '__main__':
    #Workaround for running multiprocessing on a windows system.
    freeze_support()
    get_stats()
          