from bs4 import BeautifulSoup, Comment
import datetime
import http.cookiejar
import json
from convert import makeHTML
import mechanize
import os
import random
import re
import time
# import urllib3

'''
The site relys on the use of the users ID when carrying out search querys. To obtain the id for the user you which to find posts for
navigate to 'https://hotcopper.com.au/search/' and enter the username in the Author section, then click search. The resulting URL
contains the user ID in the form of an integer at the end of the string.
EG) 'https://hotcopper.com.au/search/2244852/?q=%2A&t=post&o=date&c[visible]=true&c[user][0]=54321'

In this case 54321 is the user ID, populate the user and user_id fields below accordingly.
'''

user = 'boysy1'
user_id = 58380

''' Set up browser '''
cj = http.cookiejar.CookieJar()     # Cookie handling object
br = mechanize.Browser()            # Create a browser object
br.set_handle_robots(False)         # Ignore robots.txt constraints
# Add valid browser headers in accordance with my own machine
br.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')]
br.set_cookiejar(cj)                # Set cookie handler in browser object
# print resp.info()                 # Show headers
# print resp.read()                 # Show content

''' Login '''
def login():
    br.open("https://hotcopper.com.au/login/")
    # f = br.forms()                    # Returns list of forms on the page
    # print(f[2])
    br.select_form(nr=2)
    br.form['login'] = 'negotiateMerge'
    br.form['password'] = str(os.getenv('HCPWD'))
    br.form.find_control('tos', nr=1).get('1').selected = True  # Fill Terms of service checkbox
    br.submit()


def get_unix_time(year, month):
    ''' Return unix time of the first of any given year, month '''
    epoch = datetime.datetime(year, month, 1, 0, 0, 0).strftime('%s')
    return epoch


def human_delay(low, high):
    ''' Used to generate random dealys to imitate typical human usage '''
    delay = random.uniform(low, high)
    time.sleep(round(delay, 1))


# Globals
links = []
domain = 'https://hotcopper.com.au'

# Load link list from previous runs if file exists
if os.path.exists('output/links.txt'):
    with open('output/links.txt', 'r') as fp:
        raw_links = [list(map(str, l.split(' '))) for l in fp]

    for i in raw_links: links.append((i[0], int(i[1])))
        # print(i[0], int(i[1]))
        # print(links)

''' Search for user posts and put urls in to list '''
def find_posts(year):
    year_from = year                                    # Lower limit of search
    year_to = year + 1                                  # Upper limit of search
    month = 12

    while year_to != year_from:
        # Divide year in to 12 even chunks, irrespective of month bounds
        year_base = int(get_unix_time(year_to - 1, 1))
        search_to = int(get_unix_time(year_to, 1))             
        month_secs = int((search_to - year_base) / 12)      
        search_from = search_to - month_secs + 1

        while search_from > year_base: # Search decending by 'month' within each year
            ''' The query expects an integer in the url after search/, The server creates a url for each search using this integer, changing the from 
                and to times has no effect on the rendered results. Removing the integer breaks the call, using an invalid integer forces the server to 
                generate a new search. 
            '''
            dummy_digits = random.randint(100, 10000)

            # Search query, the final element is the user ID 'c[user][0]=58380' You will need to search for a users posts to obtain this.
            search_query = f'https://hotcopper.com.au/search/{dummy_digits}/?q=%2A&t=post&o=date&c[date-from]={search_from}&c[date-to]={search_to}&c[visible]=true&c[user][0]={user_id}'
            search_to -= month_secs
            search_from -= month_secs
            br.open(search_query)
            url_current = br.geturl()                           # Get destination URL
            next_page = 2

            print(f'searching {month - 1}/{year_to - 1} - {month}/{year_to - 1}')
            month -= 1
            print(f"Returned URL:\n{url_current}\n")

            link_count = 0

            ''' Loop through all pages in table. There can only be 8 pages in a table, I was getting the url after the query to check for redirection 
                back to the final page however when geturl is called on page 7 it returns '\mhttps://hotcopper.com.au/search/' so I have limited the
                pages returned breaking the search into months as above. '''
            while next_page < 9:                # Based on the 8 page max regardless
                ''' Get links from each page's table '''
                soup = BeautifulSoup(br.response().read(), features='html5lib')
                all_results = soup.find('table', {'class':'table is-fullwidth'})
                try:
                    all_titles = all_results.find_all('td', {'class':['title-td no-overflow has-text-weight-semibold', 'title-td no-overflow has-text-weight-semibold alt-tr']})
                except AttributeError:
                    print(f'Month {month + 1} search completed, {link_count} links on {next_page - 2} pages\n')
                    break
                
                for row in all_titles:
                    link = row.find('a', href=True)['href']
                    ''' The links extracted are to a single post, cutting the url from the final / takes us to the whole thread. '''
                    link = link[:link.rfind('/')+1]                 # Removes chars following the last '/'
                    link_count += 1
                    if link not in [lnk[0] for lnk in links]:
                        links.append((link, year))
                        with open('output/links.txt', 'a') as fp:
                            fp.write('{} {}\n'.format(link, year))

                ''' Construct url to next search page results '''
                parts = re.split("\?page=\d+&", url_current)            # split at page specifier
                if len(parts) < 2: parts = url_current.split('?', 1)    # Split url at the ? (this is the first page)
                parts.insert(1, f'?page={next_page}&')                  # Insert page number component
                urlnext = ''.join(parts)                                # Reconstruct url
                        
                br.open(urlnext)
                next_page += 1
                human_delay(3, 6)
        year_to -= 1
    print(f'Search returned {len(links)} links')


def get_user_posts(user, url, last):
    ''' Get all user posts from a given thread url. '''
    br.open(url)
    url_current = br.geturl()
    url_previous = ''
    next_page = 2

    user_posts = {
        'title': '',
        'thread_url' : f'{url}',
        'user': f'{user}',
        'posts': []
    }

    with open('output/output.json', 'a') as f:
        ''' Accessing a page out of bounds redirects to the previous page, we use this as the loop condition. '''
        while url_current != url_previous:
            url_previous = url_current
            soup = BeautifulSoup(br.response().read(), features='html5lib')
            posts = soup.find_all('div', {'class':'message-columns'})
            write_thread_title = 0
            
            ''' Process and append each valid thread post to user_posts['posts'] '''
            for p in posts:
                try:
                    name_div = p.find('div', {'class':'user-username'})
                    name = name_div.find('a').text          # Get username of poster
                except AttributeError:
                    # Don't know why this is occuring, perhaps the user is no longer current and therefore no link is present
                    print(f'{name_div} has no find attribute when trying to retreive username')
                if name != user: continue
                elif write_thread_title < 1:        # Write thread title once only
                    user_posts['title'] = url_current.split('/')[-2].split('.')[-2].replace('-', ' ')
                    write_thread_title = 1
                
                try:
                    # Only a post from a user (not the host) will contain this div
                    foot = p.find('div', {'class':'message-user-metadata message-user-metadata-sentiment'})
                    footSpans = foot.find_all('span')
                    date = p.find('div', {'class':'post-metadata-date'}).text
                    time =  p.find('div', {'class':'post-metadata-time'}).text
                    post = p.find('blockquote', {'class':'message-text ugc baseHtml'})
                    print(post.text)
                    try:
                        # Only a reply to a previous post will contain this element we need to delete it
                        post.find('div', {'class':'bbCodeBlock bbCodeQuote'}).decompose()
                    except AttributeError:
                        pass        # Proceed if element not present
                    for element in post(text=lambda text: isinstance(text, Comment)):
                        element.extract()

                    stock = foot.find('a').text
                    price = footSpans[1].text.lstrip().replace('\n                        ', ' ').rstrip()
                    sentiment = footSpans[2].text.lstrip()
                    disclosure = footSpans[3].text.lstrip()

                    post = {
                        'date': date,
                        'time': time,
                        'post': post.text.lstrip().rstrip(),
                        'stock': stock,
                        'price': price,
                        'sentiment': sentiment,
                        'disclosure': disclosure,
                    }
                except AttributeError:
                    pass            # The footer element was not found, skip
                user_posts['posts'].append(post)

            ''' Construct url for proceeding pages '''
            if 'page' in url_current: url_current = url_current[:url_current.rfind('page')]
            br.open(url_current + f'page-{next_page}')
            url_current = br.geturl()
            if 'page' in url_current: print(f'getting page {next_page}')
            next_page += 1
            human_delay(2, 4)

        # Added for debugging
        print(user_posts)

        ''' Output json, format between posts/threads accordingly ''' 
        output =  json.dumps(user_posts, ensure_ascii=False, indent=2)
        f.write(output + ('\n' if last else ',\n'))


login()
''' Run the scraper, we know this users first post was in 2009 '''
for year in range(2024, 2008, -1): find_posts(year)
# find_posts(2023)

### Use this to run on a single thread
# get_user_posts(user, "https://hotcopper.com.au/threads/ann-steel-tube-rights-offer-reminder-to-shareholders.4386896/", last=False)

current_year = links[0][1]            # When starting from fresh use this
start_year = 2018                     # Start from a specific year
final_year = links[-1][1]
tlinks = len(links)
x = 0

while current_year > final_year - 1:
    # Write to json file json
    f = open('output/output.json', 'w')
    f.write('[\n')
    f.close()
    loop_list = []
    for c in range(x, tlinks):
        if links[c][1] == current_year: loop_list.append(links[c][0])
        else:
            x = c
            break
    
    if current_year <= start_year:
        for l in loop_list[:-1]:
            print(f'getting posts for {current_year} from link {loop_list.index(l) + 1} of {len(loop_list)} {l}')
            human_delay(3, 6)
            get_user_posts(user, domain + l, last=False)

        print(f'getting posts for {current_year} from link {loop_list.index(loop_list[-1]) + 1} of {len(loop_list)} {links[-1]}')
        get_user_posts(user, domain + loop_list[-1], last=True)

        f = open('output/output.json', 'a')
        f.write(']')
        f.close()
        makeHTML()
    current_year -= 1
