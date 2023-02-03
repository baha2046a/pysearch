import asyncio
from typing import Optional

import chardet as chardet
from requests import Response
# requests-html
from requests_html import HTMLSession
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlsplit

from cffi.backend_ctypes import unicode

from MyCommon import get_cookie, get_agent
from TextOut import TextOut

"""
jar.set("csrftoken", "41nDB6kf4Wg04Yq2mwDXKmElDpdTHOj1LQhUHZuD0DJCyadR8klQCXjsL5ZHLVNd", domain='nhentai.net', path='/')
jar.set("cf_clearance", "bdZK433_5pM2nUhs0o.3Di777zoFjcSEL1KWcyRGwKo-1660162586-0-150", domain='.nhentai.net', path='/')
jar.set("cf_chl_2", "45d0d707114b28e", domain='.nhentai.net', path='/')
jar.set("cf_chl_prog", "x16", domain='.nhentai.net', path='/')
jar.set("cf_chl_rc_ni", "2", domain='.nhentai.net', path='/')
jar.set("ts_uid", "2e6b2b11-31ca-417f-90de-b41288d8f174", domain='.tsyndicate.com', path='/')
"""


def get_html_js(url):
    TextOut.out(f"Load Html: {url}")
    session = HTMLSession()
    r = session.get(url)
    r.html.render()
    print(r.html.html)


def get_html(url, timeout=None):
    out = f"Load Html: {url}"
    if len(out) > 150:
        out = out[:150]
    TextOut.out(out)
    base_url = "{0.scheme}://{0.netloc}/".format(urlsplit(url))
    headers = {
        'Referer': base_url,
        'User-Agent': get_agent()
    }
    if timeout is None:
        timeout = (6.0, 12.0)
    return requests.get(url, headers=headers, cookies=get_cookie(url), timeout=timeout, verify=False).content


async def get_html_async(loop, url, timeout=None):
    result = await loop.run_in_executor(None, lambda: get_html(url, timeout))
    return result


def get_soup_from_text(text, encode=None) -> BeautifulSoup:
    if encode:
        return BeautifulSoup(text, "lxml", from_encoding=encode)
    return BeautifulSoup(text, "lxml")


async def get_soup_async(loop, url, encode=None):
    result = await loop.run_in_executor(None, lambda: get_soup(url, encode))
    return result


def get_soup(url, encode=None, timeout=None):
    try:
        content = get_html(url, timeout)
    except Exception as e:
        print(e)
        return None
    return get_soup_from_text(content, encode)


def toUnicode(s):
    if type(s) is unicode:
        return s
    elif type(s) is str:
        d = chardet.detect(s)
        (cs, conf) = (d['encoding'], d['confidence'])
        if conf > 0.80:
            try:
                return s.decode(cs, errors='replace')
            except Exception as ex:
                print(ex)
                # force and return only ascii subset
    return unicode(''.join([i if ord(i) < 128 else ' ' for i in s]))
