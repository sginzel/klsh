# %%
# stuff which really should be default
import re
import time
import sys
import json
import os
import argparse
import datetime

# Selenium section
import selenium
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

# for storing stuff
import pickle
import redis

def init_browser():
    opts = Options()
    opts.set_headless()
    assert opts.headless  # Operating in headless mode
    browser = Firefox(options=opts)
    return (browser)


def goto(browser, url):
    browser.get(url)
    delay = 10  # seconds
    try:
        myElem = WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
        print("Page loaded: " + url)
    except TimeoutException:
        print("Loading took too much time! - " + url)


def query_year(browser, year):
    print("Year " + str(year) + " querying...")
    year_box = browser.find_element_by_name('tx_kasongs_songs[searchRequest][published]')
    year_box.send_keys(year)
    search_form = browser.find_element_by_name('searchRequest')
    search_form.submit()
    delay = 10  # seconds
    try:
        myElem = WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#songs')))
        print("Year " + str(year) + " loaded!")
    except TimeoutException:
        print("Loading took too much time!")


def collect_songs(browser):
    songs = []
    while True:
        # collect current songlist
        curr_songs = collect_current_songs(browser)
        if len(curr_songs) == 0:
            break
        songs.append(curr_songs)
        # find next button and goto next page unless it is disabled
        next_button = browser.find_element_by_id("songs_next")
        if "disabled" in next_button.get_attribute("class"):
            break
        else:
            browser.execute_script("arguments[0].click();", next_button)
    songs = [val for sublist in songs for val in sublist]
    print("Collected " + str(len(songs)) + " songs")
    return songs


def collect_current_songs(browser):
    songs = []
    try:
        table = browser.find_element_by_id("songs")
        links = table.find_elements_by_css_selector("a")
        for link in links:
            url = link.get_attribute("href")
            if (re.match(r'.*\/song.*', url)):
                songs.append(url)
    except selenium.common.exceptions.NoSuchElementException:
        print("Songs not found.")
    return songs

def get_yearstore(year):
    return "data/songs/urls_" + str(year) + ".json"

def get_lyricsstore(year):
    return "data/songs/lyrics_" + str(year) + ".json"

def store_songs(year, songs):
    fout = get_yearstore(year)
    with open(fout, 'w+') as outfile:
        json.dump(songs, outfile)
    print("Year %s was stored at %s" % (year, fout))

def load_songs(year):
    fin = get_yearstore(year)
    with open(fin, 'r') as infile:
        songs = json.load(infile)
    return songs

# 1950-2020
# 1900-1917
# 1917-1950 <<- fehlt noch

def collect_years(start, end):
    for yeari in range(int(start), int(end)):
        if not os.path.exists(get_yearstore(yeari)):
            browser = init_browser()
            goto(browser, 'https://www.koelsch-akademie.de/de/liedersammlung/songs/')
            year = str(yeari)
            query_year(browser, year)
            all_songs = collect_songs(browser)
            store_songs(year, all_songs)
            browser.close()
            time.sleep(10) # wait before next iteration
        else:
            print("Year %s already exsits at %s" % (yeari, get_yearstore(yeari)))

def collect_lyrics(start, end):
    for yeari in range(int(start), int(end)):
        if not os.path.exists(get_lyricsstore(yeari)):
            store_year_songs(yeari)
        else:
            print("Year %s already exsits at %s" % (yeari, get_lyricsstore(yeari)))


# not working for https://www.koelsch-akademie.de/de/liedersammlung/song/aachterbahn-puetzchensmaat-1/
# from 1982
def store_year_songs(yeari):
    rds = redis.Redis()
    # open transaction
    with rds.pipeline() as pipe:
        # load resource
        lyrics = {}
        for url in load_songs(yeari):
            browser = init_browser()
            goto(browser, url)
            # load meta data from table
            meta = {}
            for line in browser.find_elements_by_css_selector("table tr"):
                k, v = line.find_elements_by_css_selector("td")
                meta[k.text] = v.text
            # load song texts as selenium object
            org, klsh, ger = browser.find_elements_by_class_name("m-ls-lyrics__item")
            # add processed song texts
            meta["original_html"] = org.get_attribute("innerHTML")
            meta["klsh_html"] = klsh.get_attribute("innerHTML")
            meta["german_html"] = ger.get_attribute("innerHTML")
            meta["original_text"] = org.text
            meta["klsh_text"] = klsh.text
            meta["german_text"] = ger.text
            # store it to redis and global dict
            lyrics[url] = meta.copy()
            rds.hset("lyrics", url, json.dumps(meta))
            browser.close()
            time.sleep(3)

        pipe.execute()
        # commit transaction on redis and file store
        with open(get_lyricsstore(yeari), 'w+') as outfile:
            outfile.write(json.dumps(lyrics))
        print("Lyrics of Year %s was stored at %s" % (str(yeari), get_lyricsstore(yeari)))


if __name__ == "__main__":
    # initiate the parser
    parser = argparse.ArgumentParser()

    # add long and short argument
    parser.add_argument("--begin", "-b", help="beginning year", default="1900")
    parser.add_argument("--until", "-u", help="until year",     default=str(datetime.datetime.today().year))

    # read arguments from the command line
    args = parser.parse_args()

    collect_years(args.begin, args.until)
    collect_lyrics(args.begin, args.until)