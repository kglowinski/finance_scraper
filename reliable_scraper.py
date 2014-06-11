import csv
import os
import sys

from bs4 import BeautifulSoup
from selenium import webdriver
from datetime import date

'''So now, instead of passing an entire list of symbols directly to the scraper,
want to have an outer function that will loop once for each symbol. That way,
can have it refresh when it's encountering the value errors that mean that
the page hasn't loaded. It shows up on the page as u\u2014 when it's missing a
value.'''

DRIVER = webdriver.PhantomJS()

class BlankPullError(Exception):
    '''Want an exception class that we can throw if we "pull data" but it's a blank.'''
    pass

def main():

    ticker_symbols_etf = ['IVV']

    etf_dict = scrape_etf_pages(ticker_symbols_etf)

    print "My etf dict is currently..." 
    print etf_dict

def scrape_etf_pages(symbols):

    info_dict = {}
    perf_prefix = 'http://performance.morningstar.com/funds/etf/total-returns.action?t='
    risk_prefix = 'http://performance.morningstar.com/funds/etf/ratings-risk.action?t='
    quote_prefix = 'http://etfs.morningstar.com/quote?t='

    for symbol in symbols:
        info_dict[symbol] = {} 
        print("Currently on: " + str(symbol))
        perf_url = perf_prefix + symbol
        risk_url = risk_prefix + symbol
        quote_url = quote_prefix + symbol

        while True:
            try:
                #running the three parts, wait for it to break, reload the corresponding
                #url
                get_type(quote_url, info_dict, symbol)
                get_e_risk_values(risk_url, info_dict)
                #get_e_quote_values(quote_url, info_dict)

                break
            except (ValueError, BlankPullError):
                print "Looping for " + str(symbol)
                continue

    return info_dict

def get_type(url, info_dict, symbol):
    '''Get the type and star rating.'''

    DRIVER.get(url)
    html = DRIVER.page_source
    soup = BeautifulSoup(html)

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


main()
