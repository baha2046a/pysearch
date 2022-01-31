import requests
from bs4 import BeautifulSoup
from urllib.parse import urlsplit


def get_html(url):
    base_url = "{0.scheme}://{0.netloc}/".format(urlsplit(url))
    headers = {
        'Referer': base_url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/74.0.3729.169 Safari/537.36 '
    }
    return requests.get(url, headers=headers).text


def get_soup_from_text(text):
    return BeautifulSoup(text, "html.parser")


def get_soup(url):
    return get_soup_from_text(get_html(url))
