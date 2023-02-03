import json
import os.path
import re
import urllib.parse

from PySide6.QtCore import QThread, Signal

from TextOut import TextOut
from myparser.InfoMovie import InfoKeyword, InfoSeries, InfoMaker, InfoLabel, InfoActor, InfoMovie, InfoDirector, \
    load_info
from myparser.MovieCache import MovieCache
from myparser.MovieNameFix import movie_name_fix
from myparser.ParserCommon import get_html
from myqt.MyQtWorker import MyThreadPool
from myqt.QtImage import MyImageSource

api_id = "cKLxQzpehtWUh0bpBvTZ"
affiliate_id = "joyusexy-990"
service = ["mono", "digital", "rental"]


def get_all_fanza(paths, progress_reset_signal, progress_signal,
                  thread: QThread = None, force=False):
    MyThreadPool.asyncio(get_all_fanza_run, [paths, progress_reset_signal, progress_signal, thread, force])


async def get_all_fanza_run(loop, paths, progress_reset_signal, progress_signal,
                            thread: QThread = None, force=False):
    progress_reset_signal.emit(len(paths))
    progress = 0
    for p in paths:
        progress += 1
        progress_signal.emit(progress)
        if not force and os.path.exists(os.path.join(p, InfoMovie.FILE)):
            m = await load_info(p)
            if m:
                MovieCache.put(m)
                if m.actors:
                    for a in m.actors:
                        InfoActor.add(a)
                if m.keywords:
                    for g in m.keywords:
                        InfoKeyword.add(g)
                if m.director:
                    InfoDirector.add(m.director)
                if m.maker:
                    InfoMaker.add(m.maker)
                if m.label:
                    InfoLabel.add(m.label)
                if m.series:
                    InfoSeries.add(m.series)

            continue
        key = file_name_to_movie_id(p)
        if key:
            TextOut.out(f"Search For {key}...")
            print(p)
            try:
                m = get_fanza_result(p, key, thread, single_mode=True)
                if len(m):
                    TextOut.out(f"Save: {p} : {m[0][0].title}")
                    m[0][0].save()
            except Exception as e:
                TextOut.out(str(e))


def get_fanza_result(path, keyword, thread, single_mode=False) -> list:
    m = re.compile(r"(^[A-Z]+?)-?(\d+)").match(keyword)
    if m:
        modify_keyword = f"{m.groups()[0]}-{int(m.groups()[1]):05d}"
        out = search_movie(path, modify_keyword, thread, single_mode)
        out.extend(search_movie(path, keyword, thread, single_mode))
    else:
        out = search_movie(path, keyword, thread, single_mode)

    if thread.isInterruptionRequested():
        return []

    if len(out):
        hits = []
        result = []
        for m in out:
            if m.movie_id == keyword:
                hits.append(m)
        if hits:
            for m in hits:
                f = None
                b = None
                if m.front_img_url:
                    f = MyImageSource(m.front_img_url, q_pix=False)
                    if f.data is None:
                        m.front_img_url = None
                        f = None
                if m.back_img_url:
                    b = MyImageSource(m.back_img_url, q_pix=False)
                    if b.data is None:
                        m.back_img_url = None
                        b = None
                result.append((m, f, b))
        else:
            for m in out:
                f = None
                b = None
                if m.front_img_url:
                    f = MyImageSource(m.front_img_url, q_pix=False)
                    if f.data is None:
                        m.front_img_url = None
                        f = None
                if m.back_img_url:
                    b = MyImageSource(m.back_img_url, q_pix=False)
                    if b.data is None:
                        m.back_img_url = None
                        b = None
                result.append((m, f, b))
        return result
    return []


def search_movie(path, keyword, thread: QThread, single_mode=False) -> list[InfoMovie]:
    movie_result = []
    param = {"api_id": api_id,
             "affiliate_id": affiliate_id,
             "site": "FANZA",
             "service": "",
             "hits": "50",
             "sort": "match",
             "keyword": keyword,
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
                print(pid, mid, keyword)

                if single_mode:
                    if mid != keyword:
                        continue

                title = movie_name_fix(item['title'])

                if single_mode:
                    if 'DOD' in title or 'ベストヒッツ' in title or 'アウトレット' in title:
                        continue

                if "volume" in item:
                    try:
                        length = int(item['volume'])
                    except Exception as e:
                        length = 0
                        print(e)
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

                if thread.isInterruptionRequested():
                    return []

                if single_mode:
                    return [movie]
                else:
                    movie_result.append(movie)
    return movie_result  # list(map(MovieWidget, movie_result))


def file_name_to_movie_id(path):
    os_p: str = os.path.basename(path)
    ws = os_p.split()
    for w in ws:
        if w.startswith("[") and w.endswith("]"):
            print(w[1:-1])
            return w[1:-1]
    # m = re.compile(r".*\[(.*)].*").search(os.path.basename(path))
    # if m:
    # return m.groups()[0].upper()
    return None
