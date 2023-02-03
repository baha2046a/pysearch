from enum import Enum
from typing import Optional
from urllib.parse import urlparse

import bs4


class SearchType(Enum):
    ALL = 1
    FANZA = 2
    JAVBUS = 3
    MGS = 4
    DUGA = 5
    EITEN = 6


def select_one_text(element: bs4.element.Tag, selector: str) -> Optional[str]:
    """Select a tag and get Text.

    :param element: bs4 element.
    :param selector: A CSS selector.
    :return: Text
    """

    t = element.select_one(selector)
    if t:
        return t.text
    return None


def select_one_attr(element: bs4.element.Tag, selector: str, attr: str) -> Optional[str]:
    """Select a tag and get Attrib.

    :param element: bs4 element.
    :param selector: A CSS selector.
    :param attr: Attribute
    :return: Text
    """

    t = element.select_one(selector)
    if t:
        return t.attrs[attr]
    return None


def find_span_as_pair(element: bs4.element.Tag, text: str, p_name: str):
    """Select Span by text and get [a]

    :param element: bs4 element.
    :param text: Match by Text
    :param p_name: Parser Name
    :return: Text, Url
    :rtype: tuple[str, dict]
    """

    e = element.find("span", text=text)
    if e:
        a = e.parent.find("a")
        if a:
            return a.text, {p_name: url_to_id(a.attrs['href'])}
    return None, {}


def url_to_id(url) -> str:
    try:
        p = urlparse(url)
        return str(p.path.rsplit("/", 1)[-1])
    except Exception as e:
        print(e)
    return ""
