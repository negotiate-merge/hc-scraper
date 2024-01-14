from bs4 import BeautifulSoup, Comment
import http.cookiejar
import json
from convert import makeHTML
import mechanize
import os
import re
import timers


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
    br.form['password'] = str(os.getenv('HCPWD'))               # Gets password from environment variable
    # br.form['password'] = ''                                  # Set your password manually
    br.form.find_control('tos', nr=1).get('1').selected = True  # Fill Terms of service checkbox
    br.submit()

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

''' Search for user posts, put all found urls in to list and save to file 'links.txt' '''
def find_posts(year: int):
    month = 12                                          # For iteration through months
    tonight = timers.today(tonight=True)                         # Today in unix time
    year_start_unix = timers.get_unix_time(year, 1)
    year_end_unix = timers.get_unix_time(year + 1, 1)
    
    search_to = year_end_unix if year_end_unix < tonight else tonight           # Either tonight or end of the year
    if search_to == tonight: month = timers.get_date(tonight).month             # Set the month in accordance with previous line
    search_from = timers.get_unix_time(year, month)                             # Search the current month

    ''' This is the MONTH loop '''
    while month: # Search decending by 'month' within each year
        ''' The search query expects an integer in the url after search/, the server creates a url for each search using this integer which 
            serves as aroutable endpoint for the search, changing the from and to times in this url no effect on the rendered results. 
            Removing the integer breaks the call, using an invalid integer forces the server to generate a new search. 
        '''
        dummy_digits = timers.randnum()                         # Creates an invalid integer for the URL
        search_query = f'https://hotcopper.com.au/search/{dummy_digits}/?q=%2A&t=post&o=date&c[date-from]={search_from}&c[date-to]={search_to}&c[visible]=true&c[user][0]={user_id}'
        br.open(search_query)
        url_current = br.geturl()                               # Get resolved URL
        next_page = 2

        print(f'Month {month}\nsearching from {timers.get_date(search_from)}\tto\t{timers.get_date(search_to)}')
        print(f'search from = {search_from}\tsearch_to = {search_to}')
        print(f"Returned URL:\n{url_current}\n")

        link_count = 0

        ''' Loop through all pages in table. There can only be 8 pages in a table, I was getting the url after the query to check for redirection 
            back to the final page however when geturl is called on page 7 it returns '\mhttps://hotcopper.com.au/search/' so I have limited the
            pages returned by breaking the search into months as above.
        '''
        while next_page < 9:                # Based on the 8 page max regardless
            ''' Get links from each page's table '''
            soup = BeautifulSoup(br.response().read(), features='html5lib')
            all_results = soup.find('table', {'class':'table is-fullwidth'})
            try:
                all_titles = all_results.find_all('td', {'class':['title-td no-overflow has-text-weight-semibold', 'title-td no-overflow has-text-weight-semibold alt-tr']})
            except AttributeError:
                print(f'Month {month} search completed, {link_count} links found on {next_page - 2} pages\n')
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
            timers.human_delay(3, 6)

        month -= 1
        if month:
            search_from = timers.get_unix_time(year, month)    # Decrement by each month
            search_to = timers.get_unix_time(year, month + 1) if month != 12 else year_end_unix

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
            timers.human_delay(2, 4)

        # Added for debugging
        print(user_posts)

        ''' Output json, format between posts/threads accordingly ''' 
        output =  json.dumps(user_posts, ensure_ascii=False, indent=2)
        f.write(output + ('\n' if last else ',\n'))


login()


# find_posts(2024)


''' Run the scraper, we know this users first post was in 2009 '''
for year in range(2024, 2022, -1): find_posts(year)     # 2008


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
            timers.human_delay(3, 6)
            get_user_posts(user, domain + l, last=False)

        print(f'getting posts for {current_year} from link {loop_list.index(loop_list[-1]) + 1} of {len(loop_list)} {links[-1]}')
        get_user_posts(user, domain + loop_list[-1], last=True)

        f = open('output/output.json', 'a')
        f.write(']')
        f.close()
        makeHTML()
    current_year -= 1
