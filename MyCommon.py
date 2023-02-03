import asyncio
import glob
import imghdr
import json
import os
import re
import shutil
import threading
import time

import aiofiles
from PySide6.QtCore import QObject
from cf_clearance import sync_cf_retry, sync_stealth
from datetime import date
from typing import AnyStr, Optional, Tuple, Any
from urllib.parse import urlsplit

import cv2
import numpy as np
import requests
from playwright.sync_api import sync_playwright
from requests import Timeout

from TextOut import TextOut
from ChromeCookies import parse_cookies


def every(delay, task):
    next_time = time.time() + delay
    while True:
        time.sleep(max(0, next_time - time.time()))
        try:
            task()
        except Exception as ex:
            print(ex)
            # traceback.print_exc()
            # in production code you might want to have this instead of course:
            # logger.exception("Problem while executing repetitive task.")
        # skip tasks if we are behind schedule:
        next_time += (time.time() - next_time) // delay * delay + delay


def load_json(file_path: str) -> Any:
    """Load Json File.

    :param file_path: Json Path
    :return: データ
    """
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                return data
            except Exception as e:
                print(e)
            finally:
                f.close()
    else:
        return None


def find_main_widget(parent: QObject) -> Optional[QObject]:
    while parent and not hasattr(parent, "model"):
        parent = parent.parent()
    return parent


def save_json(file_path: str, data) -> None:
    """Save Json File.

    :param file_path: 保存するJson Path
    :param data: 保存するデータ
    """

    with open(file_path, 'w', encoding='utf-8') as f:
        try:
            json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(e)
        finally:
            f.close()


async def async_save_json(file_path: str, data) -> None:
    """Save Json File.

    :param file_path: 保存するJson Path
    :param data: 保存するデータ
    """

    try:
        d = json.dumps(data, indent=2, ensure_ascii=False)
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(d)
    except Exception as e:
        print(e)


def clean_dir(path: str) -> None:
    """Remove all Files in a Folder

    :param path: Target Folder
    """
    for files in os.listdir(path):
        if files == ".gitignore":
            continue

        file_path = os.path.join(path, files)
        print("Remove File:", file_path)

        try:
            # shutil.rmtree(file_path)
            os.remove(file_path)
        except OSError as e:
            print(e)


def imread(filename, flags=cv2.IMREAD_COLOR, dtype=np.uint8):
    try:
        n = np.fromfile(filename, dtype)
        img = cv2.imdecode(n, flags)
        return img
    except Exception as e:
        print(e)
        return None


def imwrite(filename, img, params=None):
    try:
        ext = os.path.splitext(filename)[1]
        result, n = cv2.imencode(ext, img, params)

        if result:
            with open(filename, mode='w+b') as f:
                n.tofile(f)
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False


def valid_folder_name(path: AnyStr) -> AnyStr:
    return path.replace("/", "／") \
        .replace("?", "？").replace("!", "！").replace(">", "＞") \
        .replace("<", "＜").replace(":", "：").replace("+", "＋").replace("\"", "").replace("|", "")


def join_path(root: AnyStr, file: AnyStr) -> AnyStr:
    return os.path.join(root, file).replace("\\", "/")


def next_image_path(src_path: AnyStr, delta: int = 1) -> Optional[AnyStr]:
    folder = os.path.dirname(src_path)
    filename = os.path.basename(src_path)

    regex = re.compile(r'\d+')
    file_list = regex.findall(filename)
    if file_list:
        file_num = file_list[-1]
        num_len = len(file_num)
        num_val = int(file_num)
        next_str = str(num_val + delta).zfill(num_len)
        next_path = join_path(folder, next_str.join(filename.rsplit(file_num, 1)))
        return next_path
    return None


def synchronized_method(method):
    outer_lock = threading.Lock()
    lock_name = "__" + method.__name__ + "_lock" + "__"

    def sync_method(self, *args, **kws):
        with outer_lock:
            if not hasattr(self, lock_name):
                setattr(self, lock_name, threading.Lock())
            lock = getattr(self, lock_name)
            with lock:
                return method(self, *args, **kws)

    return sync_method


def copy_file(src, des):
    try:
        shutil.copy(src, des)
    # eg. src and des are the same file
    except shutil.Error as e:
        print('Error: %s' % e)
    # eg. source or destination doesn't exist
    except IOError as e:
        print('Error: %s' % e.strerror)


def download(url: AnyStr, folder, file: Optional[AnyStr] = None) -> Tuple[AnyStr, AnyStr]:
    path = file

    if not file:
        filename = url.split("/")[-1]
        path = f"{folder}/{filename}"

    r = requests.get(url, stream=True)
    if r.status_code == 200:
        # print(f"save to {path}")
        with open(path, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
            f.close()
        return url, path
    else:
        print(r.status_code)
        # r.raise_for_status()
    return "", ""


async def download_retry(params: list):
    return await download_with_retry(*params)


async def download_with_retry(loop, url: AnyStr, folder, file: Optional[AnyStr] = None,
                              retry: int = 5, base_url: str = None) -> Tuple[AnyStr, AnyStr]:
    path = file

    if not file:
        filename = url.split("/")[-1]
        path = f"{folder}/{filename}"

    if os.path.exists(path):
        # print(imghdr.what(path), path)
        if imghdr.what(path) is not None:  # and os.path.getsize(path) > 0:
            # TextOut.out(f"File already exist {path}")
            TextOut.out(f"Skip {path}")
            return url, file

    count = 0
    r_url = ""
    r_path = ""

    while r_url == "" and count < retry:
        print(count, retry)
        r_url, r_path = await download_file(url, path, base_url, loop)
        count += 1
        if r_url == "":
            TextOut.out(f"Retry {path} << {url}")

    return r_url, r_path


def bypass_test(url: str):
    res = requests.get(url)
    if '<title>Please Wait... | Cloudflare</title>' in res.text:
        print("cf challenge fail")
        with sync_playwright() as p:
            global cf_clearance_value, ua
            cf_clearance_value = ""
            ua = ""
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            sync_stealth(page, pure=True)
            page.goto(url)
            res = sync_cf_retry(page)
            if res:
                cookies = page.context.cookies()
                for cookie in cookies:
                    if cookie.get('name') == 'cf_clearance':
                        cf_clearance_value = cookie.get('value')
                        print(cf_clearance_value)
                ua = page.evaluate('() => {return navigator.userAgent}')
                print(ua)
            else:
                print("cf challenge fail")
            browser.close()


jar = {
    "nhentai": parse_cookies("nhentai.net"),
    "xsnvshen": parse_cookies("www.xsnvshen.com"),
    "v2ph": parse_cookies(".v2ph.com"),
    "hentai-cosplays": parse_cookies("hentai-cosplays.com")
}

user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'


def get_cookie(url: str):
    for key in jar.keys():
        if url.find(key) >= 0:
            print(key)
            return jar[key]
    return None


def get_agent() -> str:
    return user_agent


async def download_file(url: AnyStr, path: AnyStr, base_url=None, loop=None) -> Tuple[AnyStr, AnyStr]:
    if not base_url:
        base_url = "{0.scheme}://{0.netloc}/".format(urlsplit(url))

    headers = {
        'Referer': base_url,
        "User-Agent": get_agent()
    }

    return await __download(url, headers, get_cookie(base_url), path, loop)


async def __download(url, header, cookie, path, loop) -> tuple[str, str]:
    if not loop:
        loop = asyncio.get_event_loop()

    try:
        r = await loop.run_in_executor(None, lambda: requests.get(url, stream=True, timeout=(6.0, 12.0),
                                                                  headers=header, cookies=cookie, verify=False))
    except Timeout:
        return "", path

    if r.status_code == 200:
        # print(r.headers["content-type"])
        try:
            with open(path, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
                f.close()
            # if imghdr.what(path) is not None:
            size = os.path.getsize(path)
            if size > 0:
                TextOut.out(f"{size} Saved {path} << {url}")
            else:
                TextOut.out(f"Failed {path} << {url}")
                return "", path
        except Exception as e:
            print(e)
            return "", path
        return url, path
    else:
        TextOut.out(f"Save Image Error {r.status_code} << {url}")
        return "", path


"""
    try:
        request = urllib.request.Request(url, headers=headers)
        data = urllib.request.urlopen(request, timeout=10.0).read()
        with open(path, mode="wb") as f:
            f.write(data)
        TextOut.out(f"{os.path.getsize(path)} Saved {path} << {url}")
        return url, path
        # r = requests.get(url, stream=True, timeout=(4.0, 10.0), headers=headers)
    except Exception as e:
        TextOut.out(f"Save {path} Error {e} << {url}")
"""


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def list_dir(folder: AnyStr, custom="*") -> list:
    select = f"{glob.escape(folder)}/{custom}"
    return glob.glob(select)


def list_jpg(folder: AnyStr, no_folder_img: bool = False) -> list:
    if no_folder_img:
        data = list_dir(folder, "*.jpg")
        data.extend(list_dir(folder, "*.png"))
        return [d.replace("\\", "/") for d in data if not d.endswith("folder.jpg")]

    result = list_dir(folder, "*.jpg")
    result.extend(list_dir(folder, "*.png"))
    return [d.replace("\\", "/") for d in result]


def name_from_path(full_path: AnyStr):
    return os.path.split(full_path)[1]


def str_to_date(date_string: str):
    return date(*list(map(int, date_string.replace("/", "-").split("-"))))


def get_html(url: AnyStr) -> str:
    return requests.get(url).text
