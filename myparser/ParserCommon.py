import requests
from bs4 import BeautifulSoup


def get_html(url):
    return requests.get(url).text


def get_soup_from_text(text):
    return BeautifulSoup(text, "html.parser")


def get_soup(url):
    return get_soup_from_text(get_html(url))
