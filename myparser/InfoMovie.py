import json
import os
import os.path
import re
import shutil
from typing import Optional, AnyStr, Tuple
from urllib.parse import urlparse

from PySide6.QtCore import Signal

from FileCopyProgress import CopyProgress
from MyCommon import download, valid_folder_name, join_path
from TextOut import TextOut
from myparser import get_soup
from myparser.InfoMovieItem import InfoMovieItem
from myparser.MovieNameFix import movie_name_fix


def fix_format(d: dict) -> dict:
    if "javbus" in d.keys():
        if d["javbus"].startswith("http"):
            p = urlparse(d["javbus"])
            d["javbus"] = str(p.path.rsplit("/", 1)[-1])
    return d


class InfoMaker(InfoMovieItem):
    data = {}
    mod_dir = {}
    path = ""
    path_d = ""
    FILE = "py_maker.txt"
    FILE_D = "py_maker_dir.txt"

    @staticmethod
    def load(path) -> None:
        InfoMaker.path = join_path(path, InfoMaker.FILE)
        InfoMaker.data = InfoMovieItem._load(InfoMaker.path)
        InfoMaker.path_d = join_path(path, InfoMaker.FILE_D)
        InfoMaker.mod_dir = InfoMovieItem._load(InfoMaker.path_d)

    @staticmethod
    def save() -> None:
        InfoMovieItem._save(InfoMaker.path, InfoMaker.data)
        InfoMovieItem._save(InfoMaker.path_d, InfoMaker.mod_dir)

    @staticmethod
    def dir(name: AnyStr) -> AnyStr:
        if name in InfoMaker.mod_dir:
            return InfoMaker.mod_dir[name]
        return name

    @staticmethod
    def add(name: AnyStr, urls=None) -> AnyStr:
        return InfoMovieItem._add(InfoMaker.data, name, urls)

    @staticmethod
    def get(name: AnyStr, urls=None) -> Optional[tuple[AnyStr, dict]]:
        return InfoMovieItem._get(InfoMaker.data, name, urls)


class InfoLabel(InfoMovieItem):
    data = {}
    modify = {}
    path = ""
    path_m = ""
    FILE = "py_label.txt"
    FILE_M = "py_label_m.txt"

    @staticmethod
    def load(path) -> None:
        InfoLabel.path = join_path(path, InfoLabel.FILE)
        InfoLabel.data = InfoMovieItem._load(InfoLabel.path)
        InfoLabel.path_m = join_path(path, InfoLabel.FILE_M)
        InfoLabel.modify = InfoMovieItem._load(InfoLabel.path_m)

    @staticmethod
    def save() -> None:
        InfoMovieItem._save(InfoLabel.path, InfoLabel.data)
        InfoMovieItem._save(InfoLabel.path_m, InfoLabel.modify)

    @staticmethod
    def add(name: AnyStr, urls=None) -> AnyStr:
        if name in InfoLabel.modify:
            name = InfoLabel.modify[name]
        return InfoMovieItem._add(InfoLabel.data, name, urls)

    @staticmethod
    def get(name: AnyStr, urls=None) -> Optional[tuple[AnyStr, dict]]:
        if name in InfoLabel.modify:
            name = InfoLabel.modify[name]
        return InfoMovieItem._get(InfoLabel.data, name, urls)


class InfoDirector(InfoMovieItem):
    data = {}
    path = ""
    FILE = "py_director.txt"

    @staticmethod
    def load(path) -> None:
        InfoDirector.path = join_path(path, InfoDirector.FILE)
        InfoDirector.data = InfoMovieItem._load(InfoDirector.path)

    @staticmethod
    def save() -> None:
        InfoMovieItem._save(InfoDirector.path, InfoDirector.data)

    @staticmethod
    def add(name: AnyStr, urls=None) -> AnyStr:
        return InfoMovieItem._add(InfoDirector.data, name, urls)

    @staticmethod
    def get(name: AnyStr, urls=None) -> Optional[tuple[AnyStr, dict]]:
        return InfoMovieItem._get(InfoDirector.data, name, urls)


class InfoSeries(InfoMovieItem):
    data = {}
    path = ""
    FILE = "py_series.txt"

    @staticmethod
    def load(path) -> None:
        InfoSeries.path = join_path(path, InfoSeries.FILE)
        InfoSeries.data = InfoMovieItem._load(InfoSeries.path)

    @staticmethod
    def save() -> None:
        InfoMovieItem._save(InfoSeries.path, InfoSeries.data)

    @staticmethod
    def add(name: AnyStr, urls=None) -> AnyStr:
        return InfoMovieItem._add(InfoSeries.data, name, urls)

    @staticmethod
    def get(name: AnyStr, urls=None) -> Optional[tuple[AnyStr, dict]]:
        return InfoMovieItem._get(InfoSeries.data, name, urls)


class InfoKeyword(InfoMovieItem):
    data = {}
    path = ""
    FILE = "py_keyword.txt"
    FILTER = ["ハイビジョン", "単体作品", "独占配信", "サンプル動画"]

    @staticmethod
    def load(path) -> None:
        InfoKeyword.path = join_path(path, InfoKeyword.FILE)
        InfoKeyword.data = InfoMovieItem._load(InfoKeyword.path)

    @staticmethod
    def save() -> None:
        InfoMovieItem._save(InfoKeyword.path, InfoKeyword.data)

    @staticmethod
    def add(name: AnyStr, urls=None) -> AnyStr:
        return InfoMovieItem._add(InfoKeyword.data, name, urls)

    @staticmethod
    def get(name: AnyStr, urls=None) -> Optional[tuple[AnyStr, dict]]:
        return InfoMovieItem._get(InfoKeyword.data, name, urls)


class InfoActor(InfoMovieItem):
    data = {}
    path = ""
    FILE = "py_actor.txt"

    @staticmethod
    def load(path) -> None:
        InfoActor.path = join_path(path, InfoActor.FILE)
        InfoActor.data = InfoMovieItem._load(InfoActor.path)

    @staticmethod
    def save() -> None:
        InfoMovieItem._save(InfoActor.path, InfoActor.data)

    @staticmethod
    def add(name: AnyStr, urls=None) -> AnyStr:
        return InfoMovieItem._add(InfoActor.data, name, urls)

    @staticmethod
    def get(name: AnyStr, urls=None) -> Optional[tuple[AnyStr, dict]]:
        return InfoMovieItem._get(InfoActor.data, name, urls)

    @staticmethod
    def update_profile(name: AnyStr, thread=None) -> Optional[tuple[AnyStr, dict]]:
        url = f"https://nakiny.com/av-search?actress={name}"
        soup = get_soup(url)
        photo_element = soup.select_one('div[class=av_serch_img_profile_left_wrap]')
        photo = None
        if photo_element:
            photo = photo_element.select_one("img").attrs["src"]
            print(photo)
        profile_element = soup.select_one('div[class=av_serch_img_profile_right_wrap]')
        profile = {}
        if profile_element:
            key = profile_element.select("span[class=name]")
            val = profile_element.select("span[class=text]")
            for i, k in enumerate(key):
                profile[k.text.replace("：", "")] = val[i].text
            print(profile)

        if profile:
            return InfoActor.get(name, {"profile": [photo, profile]})
        return InfoActor.get(name)



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

        self.movie_id = movie_id.upper().lstrip("0123456789")
        m = re.compile(r"(^[0-9A-Z]+?)-?(\d+)").match(self.movie_id)
        print(m)
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

    def rename(self) -> AnyStr:
        base = os.path.dirname(self.path)
        name = os.path.basename(self.path)

        prefer_path = None
        prefer_name = self.get_prefer_folder_name()

        if name != prefer_name:
            prefer_path = join_path(base, prefer_name)
            self.move(prefer_path)
        return prefer_path

    def move(self, prefer_path, txt_out: Signal = None, **kwargs) -> None:
        print("Move")
        sub = 1
        try_path = prefer_path
        while os.path.exists(try_path):
            try_path = f"{prefer_path} ({sub})"
            sub += 1

        same_fs = os.stat(os.path.dirname(try_path)).st_dev == os.stat(self.path).st_dev

        if not same_fs and txt_out:
            CopyProgress(self.path, try_path, txt_out)
            shutil.rmtree(self.path)
        else:
            shutil.move(self.path, try_path)
        self.set_local_path(try_path)

    def set_local_path(self, new_folder: AnyStr) -> None:
        if new_folder != self.path:
            self.path = new_folder
            if self.back_img_path:
                self.back_img_path = self.get_back_img_path()
            if self.front_img_path:
                self.front_img_path = self.get_front_img_path()
            save_info(self.path, self)

    def save(self, is_retry=False) -> None:
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

    def delete(self) -> None:
        info_path = join_path(self.path, InfoMovie.FILE)
        try:
            os.remove(info_path)
            os.remove(self.back_img_path)
            os.remove(self.front_img_path)
        except Exception as e:
            print(e)

        self.back_img_path = None
        self.front_img_path = None

    def get_back_img_path(self) -> AnyStr:
        return join_path(self.path, InfoMovie.BACK_IMG)

    def get_front_img_path(self) -> AnyStr:
        return join_path(self.path, InfoMovie.FRONT_IMG)

    def get_prefer_folder_name(self) -> str:
        title = valid_folder_name(self.title.replace("...", ""))
        return f"{self.date} [{self.movie_id}] {title}"


def load_info(path: AnyStr) -> Optional[InfoMovie]:
    info_path = os.path.join(path, InfoMovie.FILE)
    try:
        with open(info_path, encoding="utf-8") as f:
            data = json.load(f)
            return InfoMovie(**data)
    except Exception as e:
        print(e)
        return None


def save_info(path: AnyStr, data: InfoMovie) -> None:
    if data is not None:
        print(path)
        info_path = join_path(path, InfoMovie.FILE)
        try:
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(data.__dict__, f, ensure_ascii=False, indent=4)
            TextOut.out(f"Save File: {info_path}")
        except Exception as e:
            print(e)
        finally:
            f.close()


if __name__ == '__main__':
    InfoActor.update_profile("伊東める")
