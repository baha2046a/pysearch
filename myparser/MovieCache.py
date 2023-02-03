import asyncio
import multiprocessing
import os
from typing import Optional

import jsons
from PySide6.QtCore import QCoreApplication

from MyCommon import join_path
from myparser.InfoMovie import InfoDirector, InfoLabel, InfoMaker, InfoSeries, InfoKeyword, InfoActor, InfoMovie
from myparser.InfoMovieItem import InfoMovieItem
from myqt.MyQtWorker import MyThreadPool


class MovieCacheLite(InfoMovieItem):
    data = {}
    path = ""
    FILE = "py_m_lite.txt"

    @staticmethod
    def load(path):
        MovieCacheLite.path = os.path.join(path, MovieCacheLite.FILE)
        MovieCacheLite.data = InfoMovieItem._load(MovieCacheLite.path)
        # print(MovieCacheLite.data)

    @staticmethod
    def save():
        InfoMovieItem._save(MovieCacheLite.path, MovieCacheLite.data)

    @staticmethod
    async def async_save():
        await InfoMovieItem._async_save(MovieCacheLite.path, MovieCacheLite.data)

    @staticmethod
    def put(m: dict):
        print("put", m['mid'])
        MovieCacheLite.data[m['mid']] = m
        # print(MovieCache.data)

    @staticmethod
    def get(mid):
        if mid in MovieCacheLite.data:
            return MovieCacheLite.data[mid]
        return None


class MovieCache(InfoMovieItem):
    data: dict[str, InfoMovie] = {}
    path = ""
    FILE = "py_movie.txt"

    @staticmethod
    def load(path):
        MovieCache.path = join_path(path, MovieCache.FILE)
        data = InfoMovieItem._load(MovieCache.path)
        for k, d in data.items():
            m: InfoMovie = InfoMovie.__new__(InfoMovie)
            m.__dict__.update(d)
            MovieCache.data[k] = m
        # print(MovieCacheLite.data)

    @staticmethod
    def save():
        InfoMovieItem._save(MovieCache.path, MovieCache.data)

    @staticmethod
    async def async_save():
        await InfoMovieItem._async_save(MovieCache.path, MovieCache.data)

    @staticmethod
    def put(m: InfoMovie):
        MovieCache.data[m.movie_id] = m
        # print(MovieCache.data)

    @staticmethod
    def remove(m: InfoMovie):
        if m.movie_id in MovieCache.data.keys():
            MovieCache.data.pop(m.movie_id)

    @staticmethod
    def get(mid) -> Optional[InfoMovie]:
        if mid in MovieCache.data.keys():
            return MovieCache.data[mid]
        return None

    @staticmethod
    def exist(mid) -> bool:
        print(mid)
        if mid in MovieCache.data.keys():
            return True
        return False

    @staticmethod
    def startswith(mid) -> dict:
        result = {}
        for k, m in MovieCache.data.items():
            if k.startswith(mid):
                result[m.movie_id] = m.title
        return result

    @staticmethod
    def count_by_actor(thread=None) -> dict:
        result = {}
        for m in MovieCache.data.values():
            for a in m.actors:
                if a in result:
                    result[a] += 1
                else:
                    result[a] = 1
        return result

    @staticmethod
    def get_by_actor(actor: str, thread=None) -> list[InfoMovie]:
        result = []
        for m in MovieCache.data.values():
            for a in m.actors:
                if a == actor:
                    result.append(m)
                    break
        return result

    @staticmethod
    def get_by_keyword(keyword: str) -> list[InfoMovie]:
        result = []
        for m in MovieCache.data.values():
            for k in m.keywords:
                if k == keyword:
                    result.append(m)
                    break
        return result


def load_movie_db(movie_path: str):
    InfoDirector.load(movie_path)
    InfoLabel.load(movie_path)
    InfoMaker.load(movie_path)
    InfoSeries.load(movie_path)
    InfoKeyword.load(movie_path)
    InfoActor.load(movie_path)

    MovieCacheLite.load(movie_path)
    MovieCache.load(movie_path)


async def save_movie_db():
    task_list = [
        asyncio.ensure_future(InfoDirector.async_save()),
        asyncio.ensure_future(InfoLabel.async_save()),
        asyncio.ensure_future(InfoMaker.async_save()),
        asyncio.ensure_future(InfoSeries.async_save()),
        asyncio.ensure_future(InfoKeyword.async_save()),
        asyncio.ensure_future(InfoActor.async_save()),
        asyncio.ensure_future(MovieCacheLite.async_save()),
        asyncio.ensure_future(MovieCache.async_save()),
    ]
    await asyncio.gather(*task_list)
