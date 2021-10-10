import os

from myparser.InfoMovieItem import InfoMovieItem


class MovieCache(InfoMovieItem):
    data = {}
    path = ""
    FILE = "py_m_lite.txt"

    @staticmethod
    def load(path):
        MovieCache.path = os.path.join(path, MovieCache.FILE)
        MovieCache.data = InfoMovieItem._load(MovieCache.path)

    @staticmethod
    def save():
        InfoMovieItem._save(MovieCache.path, MovieCache.data)

    @staticmethod
    def put(m: dict):
        print(m['mid'])
        MovieCache.data[m['mid']] = m

    @staticmethod
    def get(mid):
        if mid in MovieCache.data:
            return MovieCache.data[mid]
        return None
