import urllib
from typing import Optional
from urllib.parse import urlparse

from myparser import get_soup
from myparser.InfoMovie import InfoMovie
from myparser.movie import select_one_text, select_one_attr

root = "https://duga.jp"


def search_movie(path, keyword) -> list:
    if not keyword:
        return []

    keyword = urllib.parse.quote(keyword.encode('shift_jis'))
    s_url = f"https://duga.jp/search/=/q={keyword}/"
    print(s_url)

    result = []
    soup = get_soup(s_url)
    if soup:
        elements = soup.select("div[class=contentslist]")
        for e in elements:
            movie = search_single(path, keyword, e)
            if movie:
                result.append(movie)

    return result


def search_single(path, keyword, element) -> Optional[InfoMovie]:
    detail_url = element.select_one("a")
    if detail_url:
        detail_url = "https://duga.jp" + detail_url.attrs['href']
        soup = get_soup(detail_url)

        title = select_one_text(soup, "h1[class=title]")

        date = select_one_attr(soup, "span[itemprop=releaseDate]", 'content')

        mid = soup.find("th", text="メーカー品番")
        if mid:
            mid = select_one_text(mid.parent, "span")
        else:
            mid = soup.find("th", text="作品ID")
            if mid:
                mid = select_one_text(mid.parent, "span")

        back = None
        front = None
        image = soup.select_one("div[class=imagebox]")
        if image:
            back = select_one_attr(image, "a", 'href')
            front = select_one_attr(image, "img", 'src')

        key_list = set()
        key = soup.select_one("ul[class=categorylist]")
        if key:
            key = key.select("a")
            for k in key:
                key_list.add(k.text)
        key_list = list(key_list)

        actor_list = []
        actor = soup.select_one("ul[class=performer]")
        if actor:
            actor = actor.select("a")
            for a in actor:
                actor_list.append(a.text)

        director = soup.select_one("ul[class=director]")
        if director:
            director = select_one_text(director, "a")

        length = soup.find("th", text="再生時間")
        if length:
            length = select_one_text(length.parent, "td")
            if length:
                length = length.split("分", 1)[0]

        series = soup.find("th", text="シリーズ")
        if series:
            series = select_one_text(series.parent, "a")

        label = soup.find("th", text="レーベル")
        if label:
            label = select_one_text(label.parent, "a")

        maker = soup.find("th", text="メーカー")
        if maker:
            maker = select_one_text(maker.parent, "a")

        print(title, date, mid, series, maker, label, actor_list, key_list, back, front, director, length)

        movie = InfoMovie(mid, path, back, front, title, maker, label,
                          date, series, length, None, director, actor_list, key_list, None,
                          link=detail_url, version=InfoMovie.LATEST)

        return movie

    return None


if __name__ == '__main__':
    search_movie("", "VRXS-135")
