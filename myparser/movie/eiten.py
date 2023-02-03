import re
from typing import Optional

import requests

from myparser import get_soup_from_text, get_soup
from myparser.InfoMovie import InfoMovie, InfoDirector, InfoSeries, InfoMaker, InfoActor, InfoKeyword


def search_movie(path, keyword: str) -> list:
    if not keyword:
        return []

    keyword = keyword.replace("_", " ")
    response = requests.post('https://www.eiten.tv/product/product_search.php', data={'kw': keyword})

    result = []
    soup = get_soup_from_text(response.text)
    if soup:
        elements = soup.select("div[class=products]")
        for e in elements:
            url = e.select_one("a")
            if url:
                d_url = url.attrs['href']
                front = url.select_one('img')
                if front:
                    front = front.attrs['data-original']
                movie = search_single(path, front, d_url)
                if movie:
                    result.append(movie)

    print("Search End")

    return result


def search_single(path, front, detail_url) -> Optional[InfoMovie]:
    soup = get_soup(detail_url)
    # <li>■タイトル：
    title = soup.select_one('li:-soup-contains("タイトル")')
    if title:
        title = title.select_one('span')
        if title:
            title = title.text.replace("　", " ")

        mid = soup.select_one('li:-soup-contains("品　　　番")')
        if mid:
            mid = mid.select_one('span')
            if mid:
                mid = mid.text

        date = soup.select_one('li:-soup-contains("発　売　日")')
        if date:
            date = date.select_one('span')
            if date:
                date = date.text.split("日", 1)[0].replace("年", "-").replace("月", "-")

        length = soup.select_one("span[class=time]")
        if length:
            length = length.text.replace("分", "")

        director = soup.select_one("span[class=producer]")
        if director:
            director = director.select_one("a")
            if director:
                director = InfoDirector.add(director.text, {"eiten": director.attrs['href'].split("prid=", 1)[1]})

        actor_list = []
        actor = soup.select_one("span[class=actor]")
        if actor:
            actor = actor.select("a")
            for a in actor:
                actor_list.append(InfoActor.add(a.text, {"eiten": a.attrs['href'].split("acid=", 1)[1]}))

        key_list = []
        key = soup.select_one("td[class=td2]")
        if key:
            key = key.select("a")
            for k in key:
                if k.attrs['href'].startswith("https:"):
                    key_list.append(InfoKeyword.add(k.text, {"eiten": k.attrs['href'].split("ccd=", 1)[1]}))

        maker = soup.select_one("span[class=maker]")
        if maker:
            maker = maker.select_one("a")
            if maker:
                maker = InfoMaker.add(maker.text.split("(", 1)[0], {"eiten": maker.attrs['href'].split("mid=", 1)[1]})

        series = soup.select_one("span[class=series]")
        if series:
            series = series.select_one("a")
            if series:
                if series.text == "廃盤タイトル":
                    series = ""
                else:
                    series = InfoSeries.add(series.text, {"eiten": series.attrs['href'].split("sid=", 1)[1]})

        back = soup.select_one("img[id=jacket]")
        if back:
            back = back.attrs['src']

        print(title, mid, date, length, director, series, maker, actor_list, key_list, back)

        movie = InfoMovie(mid, path, back, front, title, "映天", maker,
                          date, series, length, None, director, actor_list, key_list, None,
                          link=detail_url, version=InfoMovie.LATEST)

        return movie

    return None
