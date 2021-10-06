import json
import os
import os.path
import re
import shutil

from MyCommon import download
from myparser.MovieNameFix import movie_name_fix


class InfoMovieItem:
    @staticmethod
    def _add(data, name, urls=None):
        if name:
            if name in data:
                if urls:
                    data[name].update(urls)
            else:
                if urls:
                    data[name] = urls
                else:
                    data[name] = {}
        return name

    @staticmethod
    def _get(data, name, urls=None):
        if name:
            if name in data:
                if urls:
                    data[name].update(urls)
            else:
                if urls:
                    data[name] = urls
                else:
                    data[name] = {}
            return name, data[name]
        return None, {}

    @staticmethod
    def _load(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(e)
            return {}

    @staticmethod
    def _save(path, data):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(e)
        finally:
            f.close()


class InfoMaker(InfoMovieItem):
    data = {}
    path = ""
    FILE = "py_maker.txt"

    @staticmethod
    def load(path):
        InfoMaker.path = os.path.join(path, InfoMaker.FILE)
        InfoMaker.data = InfoMovieItem._load(InfoMaker.path)

    @staticmethod
    def save():
        InfoMovieItem._save(InfoMaker.path, InfoMaker.data)

    @staticmethod
    def add(name, urls=None):
        return InfoMovieItem._add(InfoMaker.data, name, urls)

    @staticmethod
    def get(name, urls=None):
        return InfoMovieItem._get(InfoMaker.data, name, urls)


class InfoLabel(InfoMovieItem):
    data = {}
    modify = {"MARXBrothersco.": "MARX Brothers co."}
    path = ""
    FILE = "py_label.txt"

    @staticmethod
    def load(path):
        InfoLabel.path = os.path.join(path, InfoLabel.FILE)
        InfoLabel.data = InfoMovieItem._load(InfoLabel.path)

    @staticmethod
    def save():
        InfoMovieItem._save(InfoLabel.path, InfoLabel.data)

    @staticmethod
    def add(name, urls=None):
        if name in InfoLabel.modify:
            name = InfoLabel.modify[name]
        return InfoMovieItem._add(InfoLabel.data, name, urls)

    @staticmethod
    def get(name, urls=None):
        if name in InfoLabel.modify:
            name = InfoLabel.modify[name]
        return InfoMovieItem._get(InfoLabel.data, name, urls)


class InfoDirector(InfoMovieItem):
    data = {}
    path = ""
    FILE = "py_director.txt"

    @staticmethod
    def load(path):
        InfoDirector.path = os.path.join(path, InfoDirector.FILE)
        InfoDirector.data = InfoMovieItem._load(InfoDirector.path)

    @staticmethod
    def save():
        InfoMovieItem._save(InfoDirector.path, InfoDirector.data)

    @staticmethod
    def add(name, urls=None):
        return InfoMovieItem._add(InfoDirector.data, name, urls)

    @staticmethod
    def get(name, urls=None):
        return InfoMovieItem._get(InfoDirector.data, name, urls)


class InfoSeries(InfoMovieItem):
    data = {}
    path = ""
    FILE = "py_series.txt"

    @staticmethod
    def load(path):
        InfoSeries.path = os.path.join(path, InfoSeries.FILE)
        InfoSeries.data = InfoMovieItem._load(InfoSeries.path)

    @staticmethod
    def save():
        InfoMovieItem._save(InfoSeries.path, InfoSeries.data)

    @staticmethod
    def add(name, urls=None):
        return InfoMovieItem._add(InfoSeries.data, name, urls)

    @staticmethod
    def get(name, urls=None):
        return InfoMovieItem._get(InfoSeries.data, name, urls)


class InfoKeyword(InfoMovieItem):
    data = {}
    path = ""
    FILE = "py_keyword.txt"
    FILTER = ["ハイビジョン", "単体作品", "独占配信", "サンプル動画"]

    @staticmethod
    def load(path):
        InfoKeyword.path = os.path.join(path, InfoKeyword.FILE)
        InfoKeyword.data = InfoMovieItem._load(InfoKeyword.path)

    @staticmethod
    def save():
        InfoMovieItem._save(InfoKeyword.path, InfoKeyword.data)

    @staticmethod
    def add(name, urls=None):
        return InfoMovieItem._add(InfoKeyword.data, name, urls)

    @staticmethod
    def get(name, urls=None):
        return InfoMovieItem._get(InfoKeyword.data, name, urls)


class InfoActor(InfoMovieItem):
    data = {}
    path = ""
    FILE = "py_actor.txt"

    @staticmethod
    def load(path):
        InfoActor.path = os.path.join(path, InfoActor.FILE)
        InfoActor.data = InfoMovieItem._load(InfoActor.path)

    @staticmethod
    def save():
        InfoMovieItem._save(InfoActor.path, InfoActor.data)

    @staticmethod
    def add(name, urls=None):
        return InfoMovieItem._add(InfoActor.data, name, urls)

    @staticmethod
    def get(name, urls=None):
        return InfoMovieItem._get(InfoActor.data, name, urls)


class InfoMovie:
    FILE = "info.txt"
    FRONT_IMG = "front.jpg"
    BACK_IMG = "back.jpg"
    LATEST = 4

    def __init__(self,
                 movie_id: str,
                 path: str,
                 back_img_url: str,
                 front_img_url: str,
                 title: str,
                 maker,
                 label,
                 date,
                 series,
                 length,
                 desc,
                 director,
                 actors,
                 keywords,
                 movie_files,
                 back_img_path: str = "",
                 front_img_path: str = "",
                 link: str = "",
                 version: int = 0):
        self.version = version

        self.movie_id = movie_id.upper()
        m = re.compile(r"(^[0-9A-Z]+?)-?(\d+)").match(self.movie_id)
        if m:
            self.movie_id = f"{m.groups()[0]}-{int(m.groups()[1]):03d}"
            if self.movie_id.startswith("1"):
                self.movie_id = self.movie_id[1:]

        self.path = path
        self.back_img_url = back_img_url
        self.back_img_path = back_img_path
        self.front_img_url = front_img_url
        self.front_img_path = front_img_path
        self.title = movie_name_fix(title)
        self.maker = maker
        self.label = label
        self.date = date
        self.series = series
        self.length = length
        self.desc = desc
        self.director = director
        self.actors = actors
        self.keywords = keywords
        self.movie_files = movie_files
        self.link = link

    def rename(self):
        base = os.path.dirname(self.path)
        name = os.path.basename(self.path)

        prefer_name = self.get_prefer_folder_name()
        if name != prefer_name:
            prefer_path = os.path.join(base, prefer_name).replace("\\", "/")
            sub = 1
            try_path = prefer_path
            while os.path.exists(try_path):
                try_path = f"{prefer_path} ({sub})"

            shutil.move(self.path, try_path)
            self.path = try_path
            self.back_img_path = self.get_back_img_path()
            self.front_img_path = self.get_front_img_path()
            save_info(self.path, self)

    def save(self, is_retry=False):
        try:
            if self.back_img_url and not self.back_img_path:
                back_img_path = self.get_back_img_path()
                download(self.back_img_url, None, back_img_path)
                self.back_img_path = back_img_path
            if self.front_img_url and not self.front_img_path:
                front_img_path = self.get_front_img_path()
                download(self.front_img_url, None, front_img_path)
                self.front_img_path = front_img_path
            save_info(self.path, self)
            print("Saved", self.back_img_path)
        except Exception as e:
            print(e)
            if not is_retry:
                self.save(is_retry=True)

    def delete(self):
        info_path = os.path.join(self.path, InfoMovie.FILE)
        os.remove(info_path)
        os.remove(self.back_img_path)
        os.remove(self.front_img_path)
        self.back_img_path = None
        self.front_img_path = None

    def get_back_img_path(self):
        return os.path.join(self.path, InfoMovie.BACK_IMG).replace("\\", "/")

    def get_front_img_path(self):
        return os.path.join(self.path, InfoMovie.FRONT_IMG).replace("\\", "/")

    def get_prefer_folder_name(self):
        title = self.title.replace("...", "").replace("/", "／") \
            .replace("?", "？").replace("!", "！").replace(">", "＞") \
            .replace("<", "＜").replace(":", "：").replace(".", "").replace("+", "＋")
        return f"{self.date} [{self.movie_id}] {title}"


def load_movie_db(movie_path: str):
    InfoDirector.load(movie_path)
    InfoLabel.load(movie_path)
    InfoMaker.load(movie_path)
    InfoSeries.load(movie_path)
    InfoKeyword.load(movie_path)
    InfoActor.load(movie_path)


def save_movie_db():
    InfoDirector.save()
    InfoLabel.save()
    InfoMaker.save()
    InfoSeries.save()
    InfoKeyword.save()
    InfoActor.save()


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
