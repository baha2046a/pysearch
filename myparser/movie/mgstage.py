import requests
from requests.cookies import RequestsCookieJar

from myparser import get_soup, get_soup_from_text
from myparser.InfoMovie import InfoMovie, InfoDirector, InfoSeries, InfoMaker, InfoLabel, InfoKeyword, InfoActor


def search_movie(path, keyword) -> list:
    if not keyword:
        return []

    s_url = f"https://nakiny.com/av-search?word={keyword}&mgs=1&mgs_d=1&sch=1&fYear=2002&fDate=01&lYear=2022&lDate=12" \
            f"&feti=feti_n&feti2=feti_n2&aveC=aveC_n&favC=favC_n&sort=new"

    print(s_url)

    result = []
    soup = get_soup(s_url)
    if soup:
        elements = soup.select("div[class=myfav_wrap]")
        for e in elements:
            movie = search_single(path, keyword, e)
            if movie:
                result.append(movie)

    return result


def search_single(path, keyword, element) -> InfoMovie:
    detail_url = element.select_one("a")
    if detail_url:
        detail_url = detail_url.attrs['href'].rsplit("/", 1)[0]

    front = element.select_one("img")
    if front:
        front = front.attrs['data-src']

    title = element.select_one("div[class='myfav_title mgs_prod']")
    if title:
        title = title.select_one("a").text.strip()

    date = element.select_one("div[class^=myfav_date]")
    if date:
        date = date.text.replace("配信日", "").replace("/", "-").strip()

    actor_list = []
    actors = element.select_one("div[class^=actress_right]")
    if actors:
        actors = actors.select("a")
        for a in actors:
            actor_list.append(InfoActor.add(a.text.strip()))

    key_list = []
    keywords = element.select_one("div[class^=genre_right]")
    if keywords:
        keywords = keywords.select("a")
        for k in keywords:
            key_list.append(InfoKeyword.add(k.text.strip()))

    director = element.select_one("div[class^=myfav_director]")
    if director:
        director = director.select_one("a")
        if director:
            director = InfoDirector.add(director.text)

    series = element.select_one("div[class^=myfav_series]")
    if series:
        series = series.select_one("a")
        if series:
            series = InfoSeries.add(series.text)

    maker = element.select_one("div[class='myfav myfav_maker']")
    if maker:
        maker = maker.select_one("a")
        if maker:
            maker = InfoMaker.add(maker.text)

    label = element.select_one("div[class='myfav myfav_label']")
    if label:
        label = label.select_one("a")
        if label:
            label = InfoLabel.add(label.text)

    mid = element.select_one("div[class='myfav myfav_cid']")
    if mid:
        mid = mid.select_one("a")
        if mid:
            mid = mid.text
            if mid.endswith(keyword):
                mid = keyword

    back = None
    length = None
    release_date = None
    if detail_url:
        jar = RequestsCookieJar()
        jar.set('mgs_agef', '1', domain='.mgstage.com', path='/')
        r = requests.get(detail_url, cookies=jar)
        html = r.content
        soup = get_soup_from_text(html)
        back = soup.select_one("a[class='link_magnify']")
        if back:
            back = back.attrs['href']

        length = soup.find("th", text="収録時間：")
        if length:
            length = length.parent.select_one("td")
            if length:
                try:
                    length = int(length.text.replace("min", ""))
                except Exception as e:
                    print(e)
                    length = None

        release_date = soup.find("th", text="商品発売日：")
        if release_date:
            release_date = release_date.parent.select_one("td")
            if release_date:
                release_date = release_date.text.replace("/", "-")

    if not length:
        length = 0
    if release_date:
        date = release_date

    print(detail_url, back, front, title, date, actor_list, key_list, director, series, maker, label, mid, length)
    movie = InfoMovie(mid, path, back, front, title, maker, label,
                      date, series, length, None, director, actor_list, key_list, None,
                      link=detail_url, version=InfoMovie.LATEST)

    return movie


if __name__ == '__main__':
    search_movie("", "VRXS-135")
