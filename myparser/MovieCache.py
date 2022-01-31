import multiprocessing
import os
from typing import Optional

import jsons
from PySide6.QtCore import QCoreApplication

from myparser.InfoMovie import InfoDirector, InfoLabel, InfoMaker, InfoSeries, InfoKeyword, InfoActor, InfoMovie
from myparser.InfoMovieItem import InfoMovieItem


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
    data: dict[InfoMovie] = {}
    path = ""
    FILE = "py_movie.txt"

    @staticmethod
    def load(path):
        MovieCache.path = os.path.join(path, MovieCache.FILE)
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


def save_movie_db():
    InfoDirector.save()
    QCoreApplication.processEvents()
    InfoLabel.save()
    QCoreApplication.processEvents()
    InfoMaker.save()
    QCoreApplication.processEvents()
    InfoSeries.save()
    QCoreApplication.processEvents()
    InfoKeyword.save()
    QCoreApplication.processEvents()
    InfoActor.save()
    QCoreApplication.processEvents()
    MovieCacheLite.save()
    QCoreApplication.processEvents()
    MovieCache.save()
    QCoreApplication.processEvents()
