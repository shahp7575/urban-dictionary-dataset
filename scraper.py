import os
import csv
import bs4
import time
import urllib
import concurrent.futures
from urllib.request import Request
from tqdm.auto import tqdm

# GLOBAL
SITE_URL = "https://www.urbandictionary.com"
BY_LETTER_URL = SITE_URL+f"/browse.php?character="
DATA_DIR = os.path.join(os.getcwd(), 'data')
MAX_THREADS = 50

# https://stackoverflow.com/questions/7001144/range-over-character-in-python
def char_range(c1, c2):
  """Generates the characters from `c1` to `c2`, inclusive."""
  for c in range(ord(c1), ord(c2)+1):
      yield chr(c)

def urllib_request(url, try_count=0):
  """Makes urllib requests with try and catch, if it throws a ConnectionResetError.
  If error thrown, it will try 3 more times every minute before it exits the function.
  Args:
  -----
  url: str
    Site URL
  Returns:
  --------
  html: Request object
  """

  try:
    html = urllib.request.urlopen(Request(url, headers={'User-Agent': 'Mozilla'}))
    time.sleep(0.25)
    return html
  except urllib.error.URLError or ConnectionResetError:
    print(f"Trying again... \n{try_count+1} times.")
    time.sleep(60)
    try_count += 1
    if try_count == 3:
      print("Ended after many tries.")
      exit
    else:
      urllib_request(url, try_count=try_count)

def get_char_pages_url(ch):
  """Get all URLs for given character from the web page.
  Args:
  -----
  ch: str
    Single alphabetic character (uppercase)
  Returns:
  --------
  all_char_urls: list
    List of all URLs for the given character
  """
  if ch.islower():
    ch = ch.upper()
  
  first_page_url = BY_LETTER_URL + ch
  html = urllib_request(first_page_url, try_count=0).read()
  raw = bs4.BeautifulSoup(html, 'lxml')
  results = raw.find('div', {'class': 'pagination-centered'}).find_all('a')[-2:]
  min_page = int(results[0].get('href').split('=')[-1])
  max_page = int(results[1].get('href').split('=')[-1])
  all_char_urls = [first_page_url]+[first_page_url+f'&page={page}' for page in range(min_page, max_page+1)]

  return all_char_urls

def get_word_urls(char_url):
  """Get the URLs for each word page.
  Args:
  -----
  char_urls: str
    Browsing page URL
  Returns:
  --------
  all_word_urls: list
    Word page URLs
  """
  html = urllib_request(char_url, try_count=0).read()
  raw = bs4.BeautifulSoup(html, 'lxml')
  results = raw.find('div', {'id': 'columnist'}).find_all('a')
  all_word_urls = [SITE_URL+r.get('href') for r in results]

  return all_word_urls

def get_word_data(word_url):
  """Get the word, meaning and sentence from a given word URL
  Args:
  -----
  word_url: str
    Word page URL
  Returns:
  --------
  word: str
    Word from the page
  definition: str
    Word's meaning from the page
  sentence: str
    Sentence example from the page
  """
  html = urllib_request(word_url, try_count=0).read()
  raw = bs4.BeautifulSoup(html, 'lxml')
  word = raw.find('div', {'class': 'def-header'}).text.strip()
  definition = ' '.join(raw.find('div', {'class': 'meaning'}).get_text('\n').split('\n'))
  sentence = ' '.join(raw.find('div', {'class': 'example'}).get_text('\n').split('\n'))

  return word_url, word, definition, sentence

def write_to_file(c, urban_data):

  data_path = os.path.join(DATA_DIR, f'character_{c}')
  data_file_path = os.path.join(data_path, f'urban_data_{c}.csv')
  if not os.path.exists(data_path):
    os.makedirs(data_path)

  with open(data_file_path, 'a') as data_file:
    for line in urban_data:
      writer = csv.writer(data_file, delimiter=',')
      writer.writerow(line)

def scraper(c, ch_url_idx):
  """Main function of this script that gets all the data.
  Args:
  -----
  c: str
    Character between A to Z. (uppercase)
  Returns:
  --------
  urban_data: list
    all word data and metadata in list.
  """
  print("-"*50)
  char_pages_urls = get_char_pages_url(c)
  print(f"This character {c} has {len(char_pages_urls)} pages.")
  if ch_url_idx:
    char_pages_urls = char_pages_urls[ch_url_idx-1:]
  print(f"Starting scraping with URL {char_pages_urls[0]}")
  for ch_idx, ch_url in enumerate(tqdm(char_pages_urls)):
    word_urls = get_word_urls(ch_url)
    urban_data = []

    threads = min(MAX_THREADS, len(word_urls))
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
      res = executor.map(get_word_data, word_urls)

    for r in res:
      urban_data.append([c, ch_url, *r])

    write_to_file(c, urban_data)
    time.sleep(1.5)
  print(f"Success! Character {c} complete.")
  print("-"*50)

  
if __name__ == "__main__":

  for c in char_range('O', 'O'):

    scraper(c, None)

