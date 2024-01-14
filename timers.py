import datetime
import random
import time

def get_date(unix_time):
    return datetime.date.fromtimestamp(unix_time)

def get_unix_time(year, month, day=1):
    ''' Return unix time of the first of any given year, month. '''
    epoch = datetime.datetime(year, month, day, 0, 0, 0).strftime('%s')
    return int(epoch)

def human_delay(low, high):
    ''' Used to generate random dealys to imitate typical human usage. '''
    delay = random.uniform(low, high)
    time.sleep(round(delay, 1))

def randnum():
    return random.randint(100, 10000)

def today(tonight=False):
    ''' Returns unix time of today, or tommorrow. '''
    if tonight: today = str(datetime.date.today() + datetime.timedelta(1))
    else: today = str(datetime.date.today())
    ymd = today.split('-')
    today = get_unix_time(int(ymd[0]), int(ymd[1]), int(ymd[2]))
    return int(today)

def year_start(year):
    ''' Returns max second from given year. '''
    return datetime.datetime(year, 12, 31, 23, 59, 59, 999999)
    
