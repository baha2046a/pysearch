import asyncio
import re
import time
from multiprocessing import Pool
from typing import Callable

from PySide6.QtCore import Signal, QThread, QSize

from myparser.MovieCache import MovieCacheLite
from myparser.MovieNameFix import movie_name_fix
from myparser.movie import SearchType, mgstage, duga, eiten, javbus
from myparser.movie.fanza import search_movie
from myparser.movie.javbus import get_javbus_series, async_get_javbus_series
from myqt.QtImage import MyImageSource
from myqt.MyQtWorker import MyThread, MyThreadPool


class MovieParser(object):
    end_count = 0

    @staticmethod
    def parse(path: str, keyword: str, output: Signal, stype: SearchType = SearchType.ALL, single_mode=False,
              signal_out_start: Callable[[], None] = None, signal_out_end: Callable[[], None] = None) -> None:
        thread = MyThread("get_movie_data")

        if stype == SearchType.FANZA:
            thread.set_run(MovieParser.search_fanza, path, keyword, output, single_mode=single_mode)
        elif stype == SearchType.JAVBUS:
            thread.set_run(MovieParser.search, javbus.search_movie, path, keyword, output)
        elif stype == SearchType.MGS:
            thread.set_run(MovieParser.search, mgstage.search_movie, path, keyword, output)
        elif stype == SearchType.DUGA:
            thread.set_run(MovieParser.search, duga.search_movie, path, keyword, output)
        elif stype == SearchType.EITEN:
            thread.set_run(MovieParser.search, eiten.search_movie, path, keyword, output)
        elif stype == SearchType.ALL:
            thread.set_run(MovieParser.search_all, path, keyword, output, single_mode=single_mode)

        if signal_out_start:
            signal_out_start()
            thread.on_finish(on_result=signal_out_end)
        thread.start()

    @staticmethod
    def search_all(path, keyword, output: Signal, thread: QThread, single_mode=False):
        print("search_all")
        result = MovieParser.search_fanza(path, keyword, output, thread, single_mode=single_mode)
        if not result:
            result = MovieParser.search(javbus.search_movie, path, keyword, output, thread)
        if not result:
            result = MovieParser.search(eiten.search_movie, path, keyword, output, thread)
        if not result:
            result = MovieParser.search(duga.search_movie, path, keyword, output, thread)
        if not result:
            MovieParser.search(mgstage.search_movie, path, keyword, output, thread)
        print("search_all_end")
        return result

    @staticmethod
    def search_fanza(path, keyword, output: Signal, thread: QThread, single_mode=False) -> bool:
        m = re.compile(r"(^[A-Z]+?)-?(\d+)").match(keyword)
        if m:
            modify_keyword = f"{m.groups()[0]}-{int(m.groups()[1]):05d}"
            out = search_movie(path, modify_keyword, thread, single_mode)
            out.extend(search_movie(path, keyword, thread, single_mode))
        else:
            out = search_movie(path, keyword, thread, single_mode)

        MovieParser.process_search_result(out, keyword, output, thread)
        return len(out) > 0

    @staticmethod
    def search(call: Callable, path, keyword, output: Signal, thread: QThread):
        out = call(path, keyword)

        MovieParser.process_search_result(out, keyword, output, thread)
        return len(out) > 0

    @staticmethod
    def process_search_result(out, keyword, output: Signal, thread: QThread) -> None:
        if thread.isInterruptionRequested():
            return

        if len(out):
            hits = []
            for m in out:
                if m.movie_id == keyword:
                    hits.append(m)
            if hits:
                for m in hits:
                    f = None
                    b = None
                    if m.front_img_url:
                        f = MyImageSource(m.front_img_url, QSize(147, 200), q_pix=False)
                        if f.data is None:
                            m.front_img_url = None
                            f = None
                    if m.back_img_url:
                        b = MyImageSource(m.back_img_url, q_pix=False)
                        if b.data is None:
                            m.back_img_url = None
                            b = None
                    output.emit((m, f, b))
                    if thread.isInterruptionRequested():
                        break
            else:
                for idx, m in enumerate(out):
                    f = None
                    b = None
                    if m.front_img_url:
                        f = MyImageSource(m.front_img_url, QSize(147, 200), q_pix=False)
                        if f.data is None:
                            m.front_img_url = None
                            f = None
                    if m.back_img_url:
                        b = MyImageSource(m.back_img_url, q_pix=False)
                        if b.data is None:
                            m.back_img_url = None
                            b = None
                    output.emit((m, f, b))
                    if idx > 10 or thread.isInterruptionRequested():
                        break

    @staticmethod
    async def async_batch_get_movie_lite(loop, mid_list, thread, out_signal, exist):
        MovieParser.end_count = 0

        job_list = []
        for mid in mid_list:
            job_list.append(MovieParser.process_parse_single_lite(loop, thread, out_signal, exist, mid))

        return await MyThreadPool.gather(*job_list)

    @staticmethod
    async def process_parse_single_lite(loop, thread, out_signal, exist, mid):
        if thread.isInterruptionRequested():
            raise Exception("End")

        try:
            result = await async_get_javbus_series(loop, *mid)
        except RuntimeError:
            return

        if result:
            m = result[0]
            MovieParser.end_count = 0
            if not result[1]:
                m['title'] = movie_name_fix(m['title'])
                MovieCacheLite.put(m)
            if m['mid'][-3:] in exist.keys():
                out_signal.emit(m, result[2], exist[m['mid'][-3:]])
            else:
                out_signal.emit(m, result[2], "")
        else:
            print("EC", MovieParser.end_count)
            MovieParser.end_count += 1
            if MovieParser.end_count > 25:
                raise Exception("End")

    @staticmethod
    def batch_get_movie_lite(mid_list, thread, out_signal, exist=None):
        if exist is None:
            exist = {}
        with Pool() as pool:
            results = pool.imap(get_javbus_series, mid_list)
            pool.close()
            end_count = 0
            first = True
            for result in results:
                if thread.isInterruptionRequested():
                    pool.terminate()
                    break

                if result:
                    m = result[0]
                    end_count = 0
                    first = False
                    if not result[1]:
                        m['title'] = movie_name_fix(m['title'])
                        MovieCacheLite.put(m)
                    if m['mid'][-3:] in exist.keys():
                        out_signal.emit(m, result[2], exist[m['mid'][-3:]])
                    else:
                        out_signal.emit(m, result[2], "")
                    time.sleep(0.001)
                else:
                    if not first:
                        end_count += 1
                        if end_count > 55:
                            pool.terminate()
                            break
            pool.join()
            time.sleep(0.1)
