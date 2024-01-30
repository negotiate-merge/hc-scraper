from bs4 import BeautifulSoup, Comment
import csv
import http.cookiejar
import json
import logging
from convert import makeHTML
import mechanize
import os
import re
import sys
import timers

# Configure logging
logging.basicConfig(filename='scraper.log', encoding='utf-8', level=logging.DEBUG, \
                    format='%(asctime)s %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

''' Load credentials for logged in user, user to be searched.
    The site relys on the use of the users ID when carrying out search querys. To obtain the id for the user you wish to find posts for
    navigate to 'https://hotcopper.com.au/search/' and enter the username in the Author section, then click search. The resulting URL
    contains the user ID in the form of an integer at the end of the string.
EG) 'https://hotcopper.com.au/search/2244852/?q=%2A&t=post&o=date&c[visible]=true&c[user][0]=54321'

    In this case 54321 is the user ID.

    You will need to create a file named creds.csv in the working directory that is structured as follows: 

    your-user-account,your-password,user-you-are-searching,searched-user-id
Eg) username,password,bigTimeTrader,98765
'''
try:
    with open('creds.csv') as creds:
        reader = csv.reader(creds, delimiter=',')
        row = next(reader)
        login_user = row[0]
        login_pwd = row[1]
        user = row[2]
        user_id = row[3]
except FileNotFoundError:
    print("creds.csv file not found")
    logging.ERROR('creds.csv not found in working directory')
    sys.exit(1)

''' Set up browser '''
cj = http.cookiejar.CookieJar()     # Cookie handling object
br = mechanize.Browser()            # Create a browser object
br.set_handle_robots(False)         # Ignore robots.txt constraints
# Add valid browser headers
br.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')]
br.set_cookiejar(cj)                # Set cookie handler in browser object

''' Login '''
def login():
    br.open("https://hotcopper.com.au/login/")
    # f = br.forms()                                            # Returns list of forms on the page
    # print(f[2])
    br.select_form(nr=2)
    br.form['login'] = login_user
    br.form['password'] = login_pwd
    br.form.find_control('tos', nr=1).get('1').selected = True  # Fill Terms of service checkbox
    br.submit()

    # Verify login procedure, log accordingly
    if cj._cookies['.hotcopper.com.au']['/']['xf_user']:
        logging.info('Login successful')
    else:
        logging.error('Login failed')
        print('Login failed, ensure your credentials are accurate')
        sys.exit(1)


def load_links():
    ''' Load link list from previous runs if file exists '''
    if os.path.exists('links.txt'):
        with open('links.txt', 'r') as fp:
            raw_links = [list(map(str, l.split(' '))) for l in fp]

        for i in raw_links: links.append((i[0], int(i[1])))
            # print(i[0], int(i[1]))
            # print(links)
        logging.info('loaded %s links from file', len(links))
    else:
        logging.info('links.txt file not found')


''' Search for user posts, put all found urls in to list and save to file 'links.txt' '''
def find_posts(year: int):
    month = 12                                                      # Month counter
    tonight = timers.today(tonight=True)                            # Today in unix time
    year_end_unix = timers.get_unix_time(year + 1, 1)
    
    search_to = year_end_unix if year_end_unix < tonight else tonight           # Either tonight or end of the year (unix time)
    if search_to == tonight: month = timers.get_date(tonight).month             # Set the month in accordance with previous line
    search_from = timers.get_unix_time(year, month)                             # Search the current month

    logging.info('Crawler started')
    urls_found = 0

    ''' Loop through all months in year '''
    while month: # Search decending by 'month' within each year
        ''' The search query expects an integer in the url after search/, the server creates a url for each search using this integer which 
            serves as a routable endpoint for the search, changing the from and to times in this url not effect on the rendered results. 
            Removing the integer breaks the call, using an invalid integer forces the server to generate a new search. 
        '''
        dummy_digits = timers.randnum()                         # Creates an invalid integer for the URL
        search_query = f'https://hotcopper.com.au/search/{dummy_digits}/?q=%2A&t=post&o=date&c[date-from]={search_from}&c[date-to]={search_to}&c[visible]=true&c[user][0]={user_id}'
        br.open(search_query)
        url_current = br.geturl()                               # Get resolved URL
        next_page = 2

        print(f'Month {month}\nsearching from {timers.get_date(search_from)}\tto\t{timers.get_date(search_to)}')
        print(f'search from = {search_from}\tsearch_to = {search_to}')              # Shows unix time
        print(f"Returned URL:\n{url_current}\n")

        link_count = 0

        ''' Loop through all pages in table. There can only be 8 pages in a table, I was getting the url after the query to check for redirection 
            back to the final page however when geturl is called on page 7 it returns '\mhttps://hotcopper.com.au/search/' so I have limited the
            pages returned by breaking the search into months as above, this typically keeps the number of pages returned very low.
        '''
        while next_page < 9:                # Based on the 8 page max regardless
            ''' Get links from each page's table '''
            soup = BeautifulSoup(br.response().read(), features='html5lib')
            all_results = soup.find('table', {'class':'table is-fullwidth'})
            try:
                all_titles = all_results.find_all('td', {'class':['title-td no-overflow has-text-weight-semibold', 'title-td no-overflow has-text-weight-semibold alt-tr']})
            except AttributeError:
                print(f'Month {month} search completed, {link_count} links found on {next_page - 2} pages\n')
                # logging.info('%()s %()s returned %()s from %()s for %()s', month, year, link_count, next_page - 2, str(user))
                logging.info(f"{month} {year} returned {link_count} links from {next_page - 2} pages for {user}")
                urls_found += link_count
                break
            
            for row in all_titles:
                link = row.find('a', href=True)['href']
                ''' The links extracted are to a single post, cutting the url from the final / takes us to the whole thread. '''
                link = link[:link.rfind('/')+1]                     # Removes chars following the last '/'
                link_count += 1
                ''' Save the links for future reference to save time and not hit the server without necessity '''
                if link not in [lnk[0] for lnk in links]:
                    links.append((link, year))
                    with open('links.txt', 'a') as fp:
                        fp.write('{} {}\n'.format(link, year))

            ''' Construct url to next search page results '''
            parts = re.split("\?page=\d+&", url_current)            # split at page specifier
            if len(parts) < 2: parts = url_current.split('?', 1)    # Split url at the ? (this is the first page)
            parts.insert(1, f'?page={next_page}&')                  # Insert page number component
            urlnext = ''.join(parts)                                # Reconstruct url
                    
            br.open(urlnext)
            next_page += 1
            timers.human_delay(3, 6)

        month -= 1
        if month:
            search_from = timers.get_unix_time(year, month)         # Decrement by each month
            search_to = timers.get_unix_time(year, month + 1) if month != 12 else year_end_unix

    print(f"Found {urls_found} urls for {year}")


def get_user_posts(user, url):
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

    # with open(file_name, 'a') as f:
    ''' Accessing a page out of bounds redirects to the previous page, we use this as the loop condition. '''
    while url_current != url_previous:
        print(f'url current {url_current}')
        url_previous = url_current
        soup = BeautifulSoup(br.response().read(), features='html5lib')

        # soup = soup.text    ## Added to try to fix find_all returning only one post div
        posts = soup.find_all('div', {'class':'message-columns'})
        write_thread_title = 0

        print(f'Number of posts: {len(posts)}')
        
        ''' Process and append each valid thread post to user_posts['posts'] '''
        for p in posts:
            try:
                name_div = p.find('div', {'class':'user-username'})
                name = name_div.find('a').text          # Get username of poster
            except AttributeError:                      # Throws error if name is None
                # Don't know why this is occuring, perhaps the user is no longer current and therefore no link is present
                print(f'{name_div} has no find attribute when trying to retreive username')
                logging.warning(f'User name is None for post #{posts.index(p)} on {url_current}')

            if name == user: 
                if write_thread_title < 1:              # Write thread title once only
                    user_posts['title'] = url_current.split('/')[-2].split('.')[-2].replace('-', ' ')
                    write_thread_title = 1
            
                try:
                    # Only a post from a user (not the host) will contain this div
                    foot = p.find('div', {'class':'message-user-metadata message-user-metadata-sentiment'})
                    footSpans = foot.find_all('span')
                    date = p.find('div', {'class':'post-metadata-date'}).text
                    time =  p.find('div', {'class':'post-metadata-time'}).text
                    post = p.find('blockquote', {'class':'message-text ugc baseHtml'})
                    # print(post.text)
                    try:
                        # Only a reply to a previous post will contain this element, we need to delete it
                        post.find('div', {'class':'bbCodeBlock bbCodeQuote'}).decompose()
                    except AttributeError:
                        pass        # Proceed if element not present

                    ''' This was supposed to fix json not serializable on year 2017 post containing html comment? - did not work. 
                        Further action required. '''
                    # for element in post(text=lambda text: isinstance(text, Comment)):
                    #     element.extract()

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

        ''' Open additional pages. '''
        if 'page' not in url_current:
            # Open a second page, redirects to previous page if not found (loop condition)
            print(f'Checking for page {next_page} posts')
            br.open(url_current + f'page-{next_page}')
            url_current = br.geturl()
        else:
            url_current = url_current[:url_current.rfind('page')] # Removes from page rightwards
            br.open(url_current + f'page-{next_page}')
            url_current = br.geturl()
            print(f'Checking for page {next_page}')
        next_page += 1
        timers.human_delay(2, 4)

    try:
        return json.dumps(user_posts, ensure_ascii=False, indent=2)
    except TypeError:
        logging.exception('Error serializing JSON')
        logging.info(user_posts)
        raise TypeError('Error ouputting JSON, check logs')


# Globals
links = []
domain = 'https://hotcopper.com.au'

def main():
    global links                    # https://realpython.com/python-use-global-variable-in-function/
    logging.info('Program started')
    login()
    load_links()
    find_posts(2024)

    ''' Run the crawler, we know this users first post was in 2009. Once you have all the links from the past you will only need to run
        the crawler preiodically on the time period since your last run. Typically the last one to two years. '''
    # for year in range(2024, 2022, -1): find_posts(year)             # 2008 will set 2009 as the start year

    links = sorted(links, key=lambda x:int(x[1]), reverse=True)     # Sort list by year prior to scraping

    ''' TESTING '''
    start_year = 2024                       # Get posts from this year,
    final_year = 2024                       # To this year (can be the same as start year)
    current_year = start_year


    ''' FULL RUN ''' """
    start_year = 2024
    current_year = links[0][1]              # When starting from fresh use this
    final_year = links[-1][1]               
    """

    # Error prone URLS
    # https://hotcopper.com.au/threads/ann-steel-tube-rights-offer-reminder-to-shareholders.4386896/        JSON not serializable due to tag


    total_links = len(links)                # Sum of all links found
    x = 0
    onetime = True                           # Used for debugging a specific forum thread, amed thread url further down
    scrape = True

    if scrape:
        while current_year > final_year - 1:
            loop_list = []                      # Holds all links for the current year
            # Get the links from a given year, append to loop_list
            for c in range(x, total_links):
                if links[c][1] == current_year: loop_list.append(links[c][0])
                else:
                    x = c                       # Value of starting point for next year range
                    break                       # We have reached a new year so we break
            
            if current_year <= start_year:
                # Write each year to json
                file_name = f'json/{user}_posts_{current_year}.json'
                f = open(file_name, 'w')
                f.write('[\n')
                f.close()

                with open(file_name, 'a') as f:
                    # Do the onetime logic here
                    if onetime:
                        output = get_user_posts(user=user, url='https://hotcopper.com.au/threads/ann-2023-drilling-update.7448008/')
                        f.write(output + '\n')
                    else:
                        for l in loop_list[:-1]:        # Excludes last item, handled differently below
                            print(f'getting posts for {current_year} from link {loop_list.index(l) + 1} of {len(loop_list)} {l}')
                            timers.human_delay(3, 6)
                            output = get_user_posts(user=user, url=domain + l)
                            f.write(output + ',\n')
                            
                        print(f'getting posts for {current_year} from link {loop_list.index(loop_list[-1]) + 1} of {len(loop_list)} {loop_list[-1]}')
                        output = get_user_posts(user=user, url=domain + loop_list[-1])
                        f.write(output + '\n')

                    f.write(']')
                    f.close()
                    makeHTML(file_name)

            current_year -= 1


if __name__ == '__main__':
    main()
