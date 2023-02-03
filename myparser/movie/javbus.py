import threading
from typing import Optional

import bs4

from myparser import get_soup
from myparser.InfoMovie import InfoMovie, InfoMaker, InfoLabel, InfoDirector, InfoActor, InfoKeyword, InfoSeries
from myparser.ParserCommon import get_soup_async
from myparser.movie import find_span_as_pair, select_one_attr
from myqt.QtImage import MyImageSource

root = "https://www.javbus.com"
p_name = "javbus"


def as_javbus_mid(movie_id: str) -> str:
    mid = movie_id.split("-")
    if len(mid) > 1:
        if len(mid[1]) == 2:
            return f"{mid[0]}-0{mid[1]}"
        if len(mid[1]) == 1:
            return f"{mid[0]}-00{mid[1]}"
    return movie_id


def get_javbus_series(args) -> list:
    movie_id = args[0]
    data = args[1]

    if movie_id in data:
        return [data[movie_id], True, MyImageSource(data[movie_id]["cover"], q_pix=False)]

    s_url = f"https://www.javbus.com/ja/search/{movie_id}"
    soup = get_soup(s_url)
    print(movie_id, threading.current_thread().ident)
    if soup:
        elements = soup.select("a[class=movie-box]")
        for e in elements:
            if f"/{movie_id.upper()}" in e.attrs['href']:
                mid, url, title, img = search_single_simple(e)
                return [{"mid": str(mid), "title": str(title), "url": str(url), "cover": str(img)},
                        False, MyImageSource(str(img), q_pix=False)]
    return []


async def async_get_javbus_series(loop, movie_id, data) -> list:
    if movie_id in data:
        return [data[movie_id], True, MyImageSource(data[movie_id]["cover"], q_pix=False)]

    s_url = f"https://www.javbus.com/ja/search/{movie_id}"
    soup = await get_soup_async(loop, s_url)

    if soup:
        elements = soup.select("a[class=movie-box]")
        for e in elements:
            if f"/{movie_id.upper()}" in e.attrs['href']:
                mid, url, title, img = search_single_simple(e)
                print(mid, title)
                return [{"mid": str(mid), "title": str(title), "url": str(url), "cover": str(img)},
                        False, MyImageSource(str(img), q_pix=False)]
    return []


def search_movie(path: str, movie_id: str) -> list[InfoMovie]:
    if not movie_id:
        return []

    movie_id = as_javbus_mid(movie_id)

    s_url = f"https://www.javbus.com/ja/search/{movie_id}"
    f_url = f"https://www.javbus.com/ja/{movie_id}"

    print(s_url)
    # print(get_html(s_url))
    result = []

    soup = get_soup(s_url)
    if soup:
        elements = soup.select("a[class=movie-box]")
        for e in elements:
            print(e.attrs['href'])
            # if f"/{movie_id.upper()}" in e.attrs['href']:
            movie = search_single(path, movie_id, e)
            if movie:
                result.append(movie)

    return result


def search_single_simple(element):
    mid = element.select_one("div[class=photo-info] span date")
    if mid:
        mid = mid.contents[0]
    if mid:
        if mid.endswith("R"):
            mid = mid[:-1]

        url = element.attrs['href']
        tag = element.select_one("div[class=photo-frame] img")
        if tag:
            front = tag.attrs["src"]
            if front:
                if not front.startswith("http"):
                    front = root + front

            title = tag.attrs["title"].strip()

            return mid, url, title, front

    return None, None, None, None


def search_single(path, keyword, element: bs4.element.Tag) -> Optional[InfoMovie]:
    mid, url, title, front = search_single_simple(element)

    if mid:
        soup = get_soup(url)

        if soup:
            director = InfoDirector.add(*find_span_as_pair(soup, "監督:", p_name))
            maker = InfoMaker.add(*find_span_as_pair(soup, "メーカー:", p_name))
            label = InfoLabel.add(*find_span_as_pair(soup, "レーベル:", p_name))
            series = InfoSeries.add(*find_span_as_pair(soup, "シリーズ:", p_name))

            date = soup.find("span", text="発売日:")
            if date:
                date = date.parent.text.replace("発売日:", "").strip()

            length = soup.find("span", text="収録時間:")
            if length:
                length = int(length.parent.text.replace("収録時間:", "").replace("分", "").strip())

            key_list = []
            actor_list = []

            genre_e = soup.select("span.genre > label")
            actor_e = soup.select("div.star-name a")

            for g in genre_e:
                a = g.find("a")
                if a:
                    key_list.append(InfoKeyword.add(a.text, {"javbus": a.attrs['href']}))
                    # genre.append((a.text, a.attrs['href']))

            for a in actor_e:
                actor_list.append(InfoActor.add(a.text, {"javbus": a.attrs['href']}))
                # actor.append((a.text, a.attrs['href']))

            back = select_one_attr(soup, "a.bigImage", "href")
            if back:
                if not back.startswith("http"):
                    back = root + back

            print(title, date, mid, series, maker, label, actor_list, key_list, back, front, director, length)

            return InfoMovie(mid, path, back, front, title, maker, label,
                             date, series, length, None, director, actor_list, key_list, None,
                             link=url, version=InfoMovie.LATEST)
    return None


