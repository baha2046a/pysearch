import threading
from typing import Optional

from myparser import get_soup
from myparser.InfoMovie import InfoMovie, InfoMaker, InfoLabel, InfoDirector, InfoActor, InfoKeyword
from urllib.parse import urlparse
from myqt.MyQtImage import MyImageSource

root = "https://www.javbus.com"


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
                m_id, url, title, img = parse_cell(e)
                return [{"mid": str(m_id), "title": str(title), "url": str(url), "cover": str(img)},
                        False, MyImageSource(str(img), q_pix=False)]
    return []


def parse_javbus_movie(path: str, movie_id: str) -> list[InfoMovie]:
    if not movie_id:
        return []

    movie_id = as_javbus_mid(movie_id)

    s_url = f"https://www.javbus.com/ja/search/{movie_id}"
    f_url = f"https://www.javbus.com/ja/{movie_id}"

    print(s_url)
    # print(get_html(s_url))
    e_list = []
    soup = get_soup(s_url)
    if soup:
        elements = soup.select("a[class=movie-box]")
        for e in elements:
            print(e.attrs['href'])
            if f"/{movie_id.upper()}" in e.attrs['href']:
                grid = parse_cell(e)
                if grid:
                    m = parse_detail(grid)
                    if m:
                        m.path = path
                        e_list.append(m)
    return e_list


def parse_cell(element):
    try:
        m_id: str = element.select("div[class=photo-info] span date")[0].contents[0]

        if not m_id:
            return None

        if m_id.endswith("R"):
            m_id = m_id[:-1]

        url = element.attrs['href']
        img_e = element.select("div[class=photo-frame] img")[0]
        title = img_e.attrs["title"].strip()
        img = img_e.attrs['src']
        if not img.startswith("http"):
            img = root + img
        return m_id, url, title, img
    except Exception as e:
        print(e)
        return None


def javbus_url_to_id(url) -> str:
    try:
        p = urlparse(url)
        return str(p.path.rsplit("/", 1)[-1])
    except Exception as e:
        print(e)
        return ""


def parse_detail(result) -> Optional[InfoMovie]:
    m_id, url, title, front = result
    soup = get_soup(url)
    if soup:

        director = InfoDirector.add(*find_span_get_pair(soup, "監督:"))
        maker = InfoMaker.add(*find_span_get_pair(soup, "メーカー:"))
        label = InfoLabel.add(*find_span_get_pair(soup, "レーベル:"))
        series, s_link = find_span_get_pair(soup, "シリーズ:")

        date_e = soup.find("span", text="発売日:")
        if date_e:
            date = date_e.parent.text.replace("発売日:", "").strip()
        else:
            date = None

        length_e = soup.find("span", text="収録時間:")
        if length_e:
            length = int(length_e.parent.text.replace("収録時間:", "").replace("分", "").strip())
        else:
            length = None

        genre = []
        actor = []

        genre_e = soup.select("span.genre > label")

        actor_e = soup.select("div.star-name a")

        for g in genre_e:
            a = g.find("a")
            if a:
                genre.append(InfoKeyword.add(a.text, {"javbus": a.attrs['href']}))
                # genre.append((a.text, a.attrs['href']))

        for a in actor_e:
            actor.append(InfoActor.add(a.text, {"javbus": a.attrs['href']}))
            # actor.append((a.text, a.attrs['href']))

        # for e in soup.select("span"):
        #    print(e)

        back_e = soup.select_one("a.bigImage")
        if back_e:
            back = root + back_e.attrs["href"]
        else:
            back = None

        """
        print(director)
        print(maker)
        print(label)
        print(series)
        print(date)
        print(length)
        print(genre)
        print(actor)
        print(back)
        """

        return InfoMovie(m_id, "", back, front,
                         title, maker, label, date, series, length,
                         "", director, actor, genre, None,
                         link=url,
                         version=InfoMovie.LATEST)
    return None


def find_span_get_pair(element, text):
    e = element.find("span", text=text)
    if e:
        a = e.parent.find("a")
        if a:
            return a.text, {"javbus": javbus_url_to_id(a.attrs['href'])}
    return None, {}
