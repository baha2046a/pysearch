import json
import os

from myparser import get_soup
from myparser.InfoMovie import InfoMovie

root = "https://www.javbus.com"


def load_info(path):
    info_path = os.path.join(path, InfoMovie.FILE)
    try:
        with open(info_path, encoding="utf-8") as f:
            data = json.load(f)
            return InfoMovie(**data)
    except Exception as e:
        print(e)
        return None


def save_info(path, data: InfoMovie):
    if data is not None:
        info_path = os.path.join(path, InfoMovie.FILE)
        try:
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(data.__dict__, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(e)
        finally:
            f.close()


def parse_movie(movie_id: str):
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
                    e_list.append(parse_detail(grid))
    return e_list


def parse_cell(element):
    try:
        m_id = element.select("div[class=photo-info] span date")[0].contents[0]

        if not m_id:
            return None

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


def parse_detail(result):
    m_id, url, title, front = result
    soup = get_soup(url)
    if soup:
        director, d_link = find_span_get_pair(soup, "監督:")
        maker, m_link = find_span_get_pair(soup, "メーカー:")
        label, l_link = find_span_get_pair(soup, "レーベル:")
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
                genre.append(a.text)
                # genre.append((a.text, a.attrs['href']))

        for a in actor_e:
            actor.append(a.text)
            # actor.append((a.text, a.attrs['href']))

        # for e in soup.select("span"):
        #    print(e)

        back_e = soup.select_one("a.bigImage")
        if back_e:
            back = root + back_e.attrs["href"]
        else:
            back = None

        print(director)
        print(maker)
        print(label)
        print(series)
        print(date)
        print(length)
        print(genre)
        print(actor)
        print(back)
        return InfoMovie(m_id, "", back, front,
                         title, maker, label, date, series, length,
                         "", director, actor, genre, None)


def find_span_get_pair(element, text):
    e = element.find("span", text=text)
    if e:
        a = e.parent.find("a")
        if a:
            return a.text, a.attrs['href']
    return None, None
