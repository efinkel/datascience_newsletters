from urllib.request import urlopen
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import time
import random
from tqdm import tqdm
import numpy as np


class newsletter_crawler:

    def __init__(self, newsletter_name, archive_url, archive_front_page):
        self.archive_url = archive_url
        self.archive_front_page = archive_front_page
        self.issue_args = ['h1']
        self.date_args = ['time', {'class': 'published'}]
        self.category_args = ['section', {'class':re.compile("(category cc).")}]
        self.category_title_args = ['span', {'class':'category__title__text'}]
        self.item_title_args = ['h3', {'class':'item__title'}]
        self.item_link_args = ['h3', {'class':'item__title'}]
        self.item_summary_args = ['span', {'class':'item__summary'}]
        self.issue_data = set([])

        self.session = requests.session()
        self.headers = {'User-Agent': 'Chrome66.0'}

    def extract_child(self, find_func, tag, attribs, regex = '[^(A-Za-z0-9.,>!?\s+)]+'):
        '''
        general function that finds children elements that are defined by {tag, {attribs} and returns cleaned up corresponding text
        
        parameters:
        find_func: find or find_all function of a parent element. e.g. category.find
        tag: element tag to find. e.g. 'h2'
        attribs: element attributes to find e.g. 'class: text
    
        '''
        
        children = find_func(tag, attribs)
        if regex is not None:
            children = [re.sub(regex, '', child.get_text()) for child in children]

        return children
    
    def parse_category_data(self, category):
        '''
        extracts category title, list item title, and list item summary in a dataelixir newsletter
        '''

        cat_title = self.extract_child(category.find_all, *self.category_title_args)

        titles = self.extract_child(category.find_all, *self.item_title_args)

        links = self.extract_child(category.find, *self.item_link_args, regex = None)
        if links.a is not None:
            links = links.a.attrs['href']
        else:
            links = [np.nan]*len(titles)

        summaries = self.extract_child(category.find_all, *self.item_summary_args)


        category_data = {'category_title':cat_title[0], 'item_title': titles, 'item_summary':summaries, 'link':links}
        return pd.DataFrame(category_data)
    
    def get_latest_issue(self):
        '''
        extracts the latest issue number
        '''
        
        session = requests.session()
        headers = {'User-Agent': 'Chrome66.0'}
        url = self.archive_front_page
        req = session.get(url, headers=headers)
        bs = BeautifulSoup(req.text, 'lxml')
        issue_headers = bs.find_all('h2', {'class': 'item__heading'})
        latest_issue = next(issue_headers[0].children)
        latest_issue_num = int(latest_issue[-3:])
        
        return latest_issue_num
        
    def get_issue_data(self, bs):
        '''gets issue number and date'''
        
        if self.issue_args is not None:
            issue = bs.find(*self.issue_args).children
            issue_num = re.sub('[^A-Za-z0-9]+', '',next(issue))
        else:
            issue_num = np.nan

        if self.date_args is not None:
        	date = bs.find(self.date_args).get_text()
        	date = re.sub('[^A-Za-z0-9]+', '',date)
        else:
        	date = np.nan

        issue_data = {name:data for name, data in zip(['issue_num', 'date'], [issue_num, date])}
        self.issue_data.add(issue_num)
        return issue_data
    
    def scrape_issue(self, url):

        '''takes in url of a newsletter issue and returns a dataframe containing info about the issue number,date, as well as
        newsletter categories,titles,links, and summaries'''

        headers = {'User-Agent': 'Chrome66.0'}
        req = self.session.get(url, headers=headers)
        bs = BeautifulSoup(req.text, 'lxml')
    
        #### need to decide how to deal with categories########
        # categories = self.extract_child(bs.find_all, *self.category_title_args, regex = None)
        categories = bs.find_all(*self.category_args)
        issue_df = pd.concat([self.parse_category_data(category = category) for category in categories]).reset_index(drop=True)
      
        issue_data = self.get_issue_data(bs)
        issue_df['date'] = issue_data['date']
        issue_df['issue_num'] = issue_data['issue_num']
        issue_df = issue_df[['issue_num', 'date', 'category_title', 'item_title', 'item_summary', 'link']]
        return issue_df

    def crawl_archive(self, issue_suffixes = None):
        '''crawls through each issue in a newsletter archive and extracts the relevant data pertaining to each issue'''

        newsletter_df = pd.DataFrame()
        if issue_suffixes is None:
            latest_issue_num = self.get_latest_issue()
            issue_suffixes = [str(num) for num in range(1,latest_issue_num,1)]
        urls = [self.archive_url+suffix for suffix in issue_suffixes]
        for url in tqdm(urls):
            newsletter_df = pd.concat([newsletter_df, self.scrape_issue(url)]).reset_index(drop = True)
            r = random.uniform(0.5,2)
            time.sleep(r)

        return newsletter_df