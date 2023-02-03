import datetime
import json
import os
import os.path
import re
import shutil
import time
from datetime import date
from typing import Optional, AnyStr
from urllib.parse import urlparse

import aiofiles
from PySide6.QtCore import Signal

from FileCopyProgress import CopyProgress
from MyCommon import download, valid_folder_name, join_path, list_dir, load_json, save_json, async_save_json
from TextOut import TextOut
from myparser import get_soup
from myparser.InfoMovieItem import InfoMovieItem
from myparser.MovieNameFix import movie_name_fix
from myparser.movie import select_one_text
from myqt.QtVideo import QtVideoDialog


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
    movie_base = ""

    @staticmethod
    def load(path) -> None:
        InfoMaker.movie_base = path
        InfoMaker.path = join_path(path, InfoMaker.FILE)
        InfoMaker.data = InfoMovieItem._load(InfoMaker.path)
        InfoMaker.path_d = join_path(path, InfoMaker.FILE_D)
        InfoMaker.mod_dir = InfoMovieItem._load(InfoMaker.path_d)

    @staticmethod
    def save() -> None:
        InfoMovieItem._save(InfoMaker.path, InfoMaker.data)
        InfoMovieItem._save(InfoMaker.path_d, InfoMaker.mod_dir)

    @staticmethod
    async def async_save():
        await InfoMovieItem._async_save(InfoMaker.path, InfoMaker.data)
        await InfoMovieItem._async_save(InfoMaker.path_d, InfoMaker.mod_dir)

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
    async def async_save():
        await InfoMovieItem._async_save(InfoLabel.path, InfoLabel.data)
        await InfoMovieItem._async_save(InfoLabel.path_m, InfoLabel.modify)

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
    async def async_save():
        await InfoMovieItem._async_save(InfoDirector.path, InfoDirector.data)

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
    async def async_save():
        await InfoMovieItem._async_save(InfoSeries.path, InfoSeries.data)

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
    FILTER_FILE = "py_keyword_filter.txt"
    FILTER = ["ハイビジョン", "単体作品", "独占配信", "サンプル動画"]

    @staticmethod
    def load(path) -> None:
        f = join_path(path, InfoKeyword.FILTER_FILE)
        data = load_json(f)
        if data:
            InfoKeyword.FILTER = data
        InfoKeyword.path = join_path(path, InfoKeyword.FILE)
        InfoKeyword.data = InfoMovieItem._load(InfoKeyword.path)

    @staticmethod
    def save() -> None:
        InfoMovieItem._save(InfoKeyword.path, InfoKeyword.data)
        f = join_path(os.path.dirname(InfoKeyword.path), InfoKeyword.FILTER_FILE)
        save_json(f, InfoKeyword.FILTER)

    @staticmethod
    async def async_save():
        await InfoMovieItem._async_save(InfoKeyword.path, InfoKeyword.data)
        f = join_path(os.path.dirname(InfoKeyword.path), InfoKeyword.FILTER_FILE)
        await async_save_json(f, InfoKeyword.FILTER)

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
    def to_list(thread=None) -> list[list]:
        result = []
        check_date = date.today()
        for k, v in InfoActor.data.items():
            age = None
            link = ""
            ruby = ""
            other = ""
            tall = None

            if 'birth' in v:
                try:
                    birthdate = datetime.datetime.strptime(v['birth'], "%Y-%m-%d").date()
                    one_or_zero = ((check_date.month, check_date.day) < (birthdate.month, birthdate.day))
                    year_difference = check_date.year - birthdate.year
                    age = int(year_difference - one_or_zero)
                except Exception as e:
                    v.pop('birth')
                    print(k, v, e)
            if 'ruby' in v:
                ruby = v['ruby']
            if 'profile' in v:
                img, pro = v['profile']

                if "身長＆スリーサイズ" in pro:
                    d = pro["身長＆スリーサイズ"]
                    if d[3:5] == "cm":
                        tall = int(d[:3])
            if "other" in v:
                other = ", ".join(v["other"])

            result.append([k, ruby, other, age, tall])

        return result

    @staticmethod
    def age(name: AnyStr, check_date=None) -> Optional[int]:
        if 'birth' in InfoActor.data[name]:
            try:
                birthdate = datetime.datetime.strptime(InfoActor.data[name]['birth'], "%Y-%m-%d").date()

                if check_date is None:
                    check_date = date.today()

                one_or_zero = ((check_date.month, check_date.day) < (birthdate.month, birthdate.day))

                year_difference = check_date.year - birthdate.year
                age = year_difference - one_or_zero

                return age
            except Exception as e:
                InfoActor.data[name].pop('birth')
                print(e)

        return None

    @staticmethod
    def load(path) -> None:
        InfoActor.path = join_path(path, InfoActor.FILE)
        InfoActor.data = InfoMovieItem._load(InfoActor.path)

    @staticmethod
    def save() -> None:
        InfoMovieItem._save(InfoActor.path, InfoActor.data)

    @staticmethod
    async def async_save():
        await InfoMovieItem._async_save(InfoActor.path, InfoActor.data)

    @staticmethod
    def link(name: AnyStr, new_name: AnyStr) -> AnyStr:
        if 'link' in InfoActor.data[new_name] and InfoActor.data[new_name]['link'] == name:
            InfoActor.remove_link(new_name)
        InfoActor.remove_link(name)

        if new_name == "" or new_name is None:
            return name
        else:
            InfoActor.add_link(name, new_name)
            return new_name

    @staticmethod
    def add_link(link_from, link_to):
        InfoActor.data[link_from]['link'] = link_to
        InfoActor.add(link_to)
        if "other" not in InfoActor.data[link_to]:
            InfoActor.data[link_to]["other"] = [link_from]
        else:
            InfoActor.data[link_to]["other"].append(link_from)

    @staticmethod
    def remove_link(remove_link_from):
        name = InfoActor.data[remove_link_from].pop("link", None)
        if name in InfoActor.data:
            InfoActor.data[name]["other"].remove(remove_link_from)

    @staticmethod
    def get_link(name: AnyStr) -> AnyStr:
        if name in InfoActor.data:
            while 'link' in InfoActor.data[name]:
                name = InfoActor.data[name]['link']
        else:
            InfoActor.data[name] = {}
        return name

    @staticmethod
    def add(name: AnyStr, urls=None) -> AnyStr:
        if urls and "fanza" in urls:
            if name in InfoActor.data and "fanza" in InfoActor.data[name]:
                if InfoActor.data[name]["fanza"] != urls["fanza"]:
                    name = f"{name}_f{urls['fanza']}"

        return InfoMovieItem._add(InfoActor.data, name, urls)

    @staticmethod
    def get(name: AnyStr, urls=None) -> Optional[tuple[AnyStr, dict]]:
        return InfoMovieItem._get(InfoActor.data, name, urls)

    @staticmethod
    def guess_name(name: AnyStr) -> list:

        return [k for k, v in InfoActor.data.items()
                if "profile" in v and "別名" in v["profile"][1] and name in v["profile"][1]["別名"]]

    @staticmethod
    def update_profile(name: AnyStr, thread=None) -> list:
        url = f"https://nakiny.com/av-search?actress={name}"
        print(url)

        soup = get_soup(url)

        photo = soup.select_one('div[class=av_serch_img_profile_left_wrap]')
        if photo:
            photo = photo.select_one("img")
            if photo:
                photo = photo.attrs["src"]
                print(photo)
        profile_element = soup.select_one('div[class=av_serch_img_profile_right_wrap]')
        profile = {}
        if profile_element:
            key = profile_element.select("span[class=name]")
            val = profile_element.select("span[class=text]")
            if key and val:
                for i, k in enumerate(key):
                    k = k.text.replace("：", "")
                    if k == "生年月日":
                        profile[k] = val[i].text.split("(", 1)[0]
                    elif k == "身長＆スリーサイズ":
                        d = val[i].text.replace("カップ", "").replace("()", "")
                        if d.startswith("T"):
                            d = d[1:]
                        profile[k] = d
                    else:
                        profile[k] = val[i].text
                print(profile)

        if profile:
            return [photo, profile]
        return []

    @staticmethod
    def update_profile2(name: AnyStr, thread=None) -> list:
        url = f"http://erodougazo.com/actress/av/{name.split('（', 1)[0].strip()}/"
        print(url)

        profile = {}
        soup = get_soup(url, timeout=(20.0, 30.0))

        if soup:
            data = soup.select_one('div[class*=ActressProfile]')

            if data:
                name_e = data.select_one("p[class=APname]")

                tag = name_e.select_one("a")
                if tag:
                    tag = tag.attrs["title"]
                    if tag:
                        tag = tag.split(" ", 2)
                        if not name.startswith(tag[0]):
                            profile["name"] = tag[0]
                        if len(tag) > 1:
                            profile["ruby"] = tag[1]
                        if len(tag) > 2:
                            profile["別名"] = tag[2]

                prof = data.select_one("div[class*=ActressProfileP]")

                tall = prof.find("i", text="身長：")
                if tall:
                    tall = select_one_text(tall.parent, "span")

                size = prof.find("i", text="スリーサイズ：")
                if size:
                    cup = prof.find("i", text="おっぱい：")
                    if cup:
                        cup = cup.parent.select_one("a")
                        if cup:
                            cup = cup.text
                            if cup:
                                cup = f'({cup.replace("カップ", "")})'

                    size = select_one_text(size.parent, "span")
                    if size:
                        size = size.replace("/ ", "").split(" ")
                        if len(size) == 3:
                            if cup:
                                size[0] = size[0] + cup
                            if tall:
                                tall = f"{tall} {size[0]} {size[1]} {size[2]}"

                if tall:
                    profile["身長＆スリーサイズ"] = tall

                birth = prof.find("i", text="生年月日：")
                if birth:
                    birth = select_one_text(birth.parent, "span")
                    if birth:
                        if birth != "----年--月--日" and not birth.endswith("頃"):
                            profile["生年月日"] = birth

                fun = prof.find("i", text="趣味：")
                if fun:
                    fun = select_one_text(fun.parent, "span")
                    if fun:
                        profile["趣味"] = fun

                print(profile)

        if profile:
            return [None, profile]
        return []


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
                 version: int = 0,
                 custom1: int = 0,
                 custom2: int = 0):
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
        self.custom1 = custom1
        self.custom2 = custom2

    def rename(self, thread=None) -> AnyStr:
        base = os.path.dirname(self.path)
        name = os.path.basename(self.path)

        prefer_path = self.path
        prefer_name = self.get_prefer_folder_name()
        if len(prefer_name) > 80:
            prefer_name = prefer_name[:79].strip() + "…"
        if not self.has_movie():
            prefer_name = prefer_name + " V"

        if name != prefer_name:
            prefer_path = join_path(base, prefer_name)
            self.move(prefer_path)
        return prefer_path

    def has_movie(self) -> bool:
        return QtVideoDialog.has_movie(self.path)

    def move(self, prefer_path, txt_out: Signal = None, **kwargs) -> None:
        print("Move")

        sub = 1
        try_path = prefer_path
        old_path = self.path
        while os.path.exists(try_path):
            try_path = f"{prefer_path} ({sub})"
            sub += 1

        same_fs = os.stat(os.path.dirname(try_path)).st_dev == os.stat(self.path).st_dev

        if not same_fs and txt_out:
            CopyProgress(old_path, try_path, txt_out)
        else:
            os.makedirs(try_path, exist_ok=True)
            content = list_dir(old_path)
            for item in content:
                out = join_path(try_path, os.path.basename(item))
                shutil.move(item, out)

        time.sleep(0.5)
        self.set_local_path(try_path)
        try:
            time.sleep(0.5)
            shutil.rmtree(old_path)
        except Exception as e:
            print(e)

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


async def load_info(path: AnyStr) -> Optional[InfoMovie]:
    info_path = join_path(path, InfoMovie.FILE)
    try:
        async with aiofiles.open(info_path, encoding="utf-8") as f:
            contents = await f.read()
        data = json.loads(contents)
        if data:
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
    InfoActor.update_profile2("伊東める")
