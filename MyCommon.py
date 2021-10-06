import glob
import os
import shutil
import threading
from datetime import date

import cv2
import numpy as np
import requests


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


def download(url: str, folder, file: str = None):
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
    return None


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def list_dir(folder, custom="*"):
    select = f"{folder}/{custom}"
    return glob.glob(select)


def list_jpg(folder):
    return list_dir(folder, "*.jpg")


def name_from_path(full_path):
    return os.path.split(full_path)[1]


def str_to_date(date_string):
    return date(*list(map(int, date_string.replace("/", "-").split("-"))))


def get_html(url):
    return requests.get(url).text
