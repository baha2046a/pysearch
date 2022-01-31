import glob
import imghdr
import os
import shutil
import threading
from datetime import date
from typing import AnyStr, Optional, Tuple
from urllib.parse import urlsplit

import cv2
import numpy as np
import requests
from requests import Timeout
from requests.cookies import RequestsCookieJar

from TextOut import TextOut


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
        .replace("<", "＜").replace(":", "：").replace("+", "＋").replace("\"", "")


def join_path(root: AnyStr, file: AnyStr) -> AnyStr:
    return os.path.join(root, file).replace("\\", "/")


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


def download_with_retry(url: AnyStr, folder, file: Optional[AnyStr] = None,
                        retry: int = 999) -> Tuple[AnyStr, AnyStr]:
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
        r_url, r_path = download_file(url, path)
        count += 1
        if r_url == "":
            TextOut.out(f"Retry {path} << {url}")

    return r_url, r_path


def download_file(url: AnyStr, path: AnyStr) -> Tuple[AnyStr, AnyStr]:
    if url.startswith("https://cloud.xinmeitulu.com/"):
        headers = {
            'Referer': 'https://www.xinmeitulu.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/74.0.3729.169 Safari/537.36 '
        }
        jar = RequestsCookieJar()
        jar.set('zone-cap-4088596', '1', domain='www.xinmeitulu.com', path='/')
        try:
            r = requests.get(url, stream=True, timeout=(2.0, 6.0), headers=headers, cookies=jar)
        except Timeout:
            return "", path
    else:
        base_url = "{0.scheme}://{0.netloc}/".format(urlsplit(url))
        headers = {
            'Referer': base_url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/74.0.3729.169 Safari/537.36 '
        }
        try:
            r = requests.get(url, stream=True, timeout=(2.0, 6.0), headers=headers)
        except Timeout:
            return "", path

    if r.status_code == 200:
        # print(r.headers["content-type"])
        try:
            with open(path, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
                f.close()
            if imghdr.what(path) is not None:
                TextOut.out(f"{os.path.getsize(path)} Saved {path} << {url}")
            else:
                TextOut.out(f"Failed {path} << {url}")
                return "", path
        except Exception as e:
            print(e)
            return "", path
        return url, path
    else:
        print(r.status_code)
        TextOut.out(f"Save Image Error {r.status_code} << {url}")
        # r.raise_for_status()
    return "", path


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def list_dir(folder: AnyStr, custom="*") -> list:
    select = f"{glob.escape(folder)}/{custom}"
    return glob.glob(select)


def list_jpg(folder: AnyStr) -> list:
    return list_dir(folder, "*.jpg")


def name_from_path(full_path: AnyStr):
    return os.path.split(full_path)[1]


def str_to_date(date_string: str):
    return date(*list(map(int, date_string.replace("/", "-").split("-"))))


def get_html(url: AnyStr) -> str:
    return requests.get(url).text
