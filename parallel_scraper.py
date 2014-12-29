import requests

from bs4 import BeautifulSoup as bs
from multiprocessing import Pool

class BlankPullError(Exception):
    '''Want an exception class that we can throw if we "pull data" but it's a blank.'''
    pass

def get_stats():
    
    symbols = ['IVV', 'IJS', 'IWM', 'IBB', 'FLPSX']
    
    #pool = Pool(8)
    #results = pool.map(return_sec_info, symbols)
    results = []
    for symbol in symbols:
        results.append(return_sec_info(symbol))
    
    print results
    
def return_sec_info(symbol):

    print symbol

    if 3 <= len(symbol) < 5:
        info_dict = scrape_etf_info(symbol)
    else:
        info_dict = scrape_mf_info(symbol) 
    return info_dict
    
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
    
    rating = get_m_star_rating(quote_url, symbol)
    info_dict['M_Star'] = rating
    
    category = get_category(category_url, symbol, "id")
    info_dict['category'] = category
    
    hist_dict = get_historical_info(historical_url, symbol)
    info_dict['performance'] = hist_dict
    
    decile_dict = get_decile_ranks(decile_url, symbol, 7)
    info_dict['ranks'] = decile_dict
    
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
    
    rating = get_m_star_rating(quote_url, symbol)
    info_dict['M_Star'] = rating
    
    category = get_category(category_url, symbol, "vkey")
    info_dict['category'] = category
    
    hist_dict = get_historical_info(historical_url, symbol)
    info_dict['performance'] = hist_dict
    
    decile_dict = get_decile_ranks(decile_url, symbol, 6)
    info_dict['ranks'] = decile_dict
    
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
    
    return stars
    
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
    perf_dict = dict(zip(perf_years, year_perfs))
    
    return perf_dict

def get_decile_ranks(url, symbol, row):
    #Taking in a row number because etf page uses row 7, and MF uses 6
    
    soup = get_soup(url, symbol)
    headers = soup.find_all("tr")[0].find_all("th")
    years = map(lambda x: x.text, headers[len(headers)-6:len(headers)-1])
    
    ranks = soup.find_all("tr")[row].find_all("td")
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
    price_to_earn = table_rows[3].find_all("td")[1].text
    price_to_book = table_rows[5].find_all("td")[1].text
    
    return (price_to_earn, price_to_book)

if __name__ ==  '__main__':
    get_stats()
          