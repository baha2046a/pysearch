import json
import os.path
import re
import urllib.parse

from myparser import get_html
from myparser.InfoMovie import InfoKeyword, InfoSeries, InfoMaker, InfoLabel, InfoActor, InfoMovie, InfoDirector
from myparser.JavBusMain import parse_javbus_movie
from myparser.MovieNameFix import movie_name_fix

api_id = "cKLxQzpehtWUh0bpBvTZ"
affiliate_id = "joyusexy-990"
service = ["mono", "digital", "rental"]


def get_all_fanza(paths, out_txt, out_signal, progress_reset_signal, progress_signal, thread, force=False):
    progress_reset_signal.emit(len(paths))
    progress = 0
    for p in paths:
        progress += 1
        progress_signal.emit(progress)
        if not force and os.path.exists(os.path.join(p, InfoMovie.FILE)):
            continue
        key = file_name_to_movie_id(p)
        out_txt.emit(f"Search For {key}...")
        print(p)
        try:
            m = get_fanza_result(p, key, out_signal, thread, single_mode=True)
            if len(m):
                out_txt.emit(f"Save: {p} : {m[0].title}")
                m[0].save()
        except Exception as e:
            out_txt.emit(e)


def get_fanza_result(path, keyword, out_signal, thread, single_mode=False):
    modify_keyword = keyword
    m = re.compile(r"(^[A-Z]+?)-?(\d+)").match(keyword)
    if m:
        modify_keyword = f"{m.groups()[0]}-{int(m.groups()[1]):05d}"

    print(modify_keyword)

    movie_result = []
    param = {"api_id": api_id,
             "affiliate_id": affiliate_id,
             "site": "FANZA",
             "service": "",
             "hits": "50",
             "sort": "match",
             "keyword": modify_keyword,
             "output": "json"}
    for s in service:
        param['service'] = s
        url = f"https://api.dmm.com/affiliate/v3/ItemList?{urllib.parse.urlencode(param)}"
        result = json.loads(get_html(url))['result']
        if result['status'] == 200 and result['result_count']:
            print(result['result_count'])

            for item in result['items']:
                pid = item['product_id']

                if "maker_product" in item:
                    mid = item['maker_product']
                else:
                    mid = pid

                if single_mode:
                    if mid != keyword:
                        continue

                title = movie_name_fix(item['title'])

                if "volume" in item:
                    length = int(item['volume'])
                else:
                    length = 0

                link = item['URL']

                if "imageURL" in item:
                    back = item['imageURL']['large']
                    front = item['imageURL']['small']
                else:
                    back = None
                    front = None
                date = item['date'][:10]

                info = item['iteminfo']

                genres = []
                if "genre" in info:
                    for g in info['genre']:
                        genres.append(InfoKeyword.add(g['name'], {"fanza": g['id']}))

                actor = []
                if "actress" in info:
                    for a in info['actress']:
                        actor.append(InfoActor.add(a['name'], {"fanza": a['id'], "ruby": a['ruby']}))

                if "director" in info:
                    director = InfoDirector.add(info['director'][0]['name'], {"fanza": info['director'][0]['id']})
                else:
                    director = None

                if "series" in info:
                    series = InfoSeries.add(movie_name_fix(info['series'][0]['name']),
                                            {"fanza": info['series'][0]['id']})
                else:
                    series = None

                if "maker" in info:
                    maker = InfoMaker.add(info['maker'][0]['name'], {"fanza": info['maker'][0]['id']})
                else:
                    maker = None

                if "label" in info:
                    label = InfoLabel.add(info['label'][0]['name'], {"fanza": info['label'][0]['id']})
                else:
                    label = None

                movie = InfoMovie(mid, path, back, front, title, maker, label,
                                  date, series, length, None, director, actor, genres, None,
                                  link=link, version=InfoMovie.LATEST)

                if single_mode:
                    return [movie]
                else:
                    movie_result.append(movie)

    if not len(movie_result):
        movie_result = parse_javbus_movie(path, keyword)

    return movie_result  # list(map(MovieWidget, movie_result))


def file_name_to_movie_id(path):
    m = re.compile(r".*\[(.*)].*").match(os.path.basename(path))
    if m:
        return m.groups()[0].upper()
    return None

