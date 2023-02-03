import asyncio
import json
import os
from datetime import date
from typing import AnyStr, Tuple, Callable

import imagehash
from PIL import Image  # Pillow
from PySide6.QtCore import QSize, Signal
from bs4 import Tag

from MyCommon import list_jpg, str_to_date, download_with_retry, join_path
from TextOut import TextOut
from myparser.ParserCommon import get_soup, get_soup_from_text, get_html_async
from myqt.MyQtWorker import MyThreadPool
from myqt.QtImage import MyImageSource


def search_dup(folder,
               as_size,
               signal_old, signal_new,
               progress_reset_signal, progress_signal,
               check_cancel: Callable[[], bool] = None,
               auto_del=True):
    files = list_jpg(folder)
    if files:
        exist_hash = []
        hashes, old_exist_hash, _ = read_hash_file(folder)
        for path in old_exist_hash:
            if path in files:
                exist_hash.append(path)
            else:
                TextOut.out(f"Remove hash: {path}")
                for k, v in list(hashes.items()):
                    if v == path:
                        del hashes[k]
                        TextOut.out(f"Hash removed: {path}")

        parent = []
        progress = 0
        progress_reset_signal.emit(len(files))
        for path in files:
            progress += 1
            progress_signal.emit(progress)
            if path.endswith("folder.jpg"):
                continue
            if check_cancel and check_cancel():
                break
            if path in exist_hash:
                continue
            with Image.open(path) as img:
                try:
                    temp_hash = str(imagehash.average_hash(img, 8))
                except Exception as ex:
                    print(ex, path)
                    continue
                if temp_hash in hashes:
                    if hashes[temp_hash] not in parent:
                        parent.append(hashes[temp_hash])
                        i = MyImageSource(hashes[temp_hash], as_size)
                        signal_old.emit(hashes[temp_hash], as_size, i)
                    if auto_del:
                        TextOut.out(f"Delete Image: {path}")
                        os.remove(path)
                    else:
                        n = MyImageSource(path, as_size)
                        signal_new.emit(path, as_size, n)
                else:
                    exist_hash.append(path)
                    hashes[temp_hash] = path
        write_hash_file(folder, hashes, exist_hash)
    return folder


def read_hash_file(folder) -> tuple[dict, list, bool]:
    hash_file = os.path.join(folder, "hash.json")
    hash_path = os.path.join(folder, "hash_path.json")
    hashes = {}
    exist_hash = []
    exist = False
    if os.path.exists(hash_file) and os.path.exists(hash_path):
        try:
            with open(hash_file) as f:
                hashes = json.load(f)
            with open(hash_path) as f:
                exist_hash = json.load(f)
            exist = True
        except Exception as ex:
            hashes = {}
            exist_hash = []
            print(ex)
    return hashes, exist_hash, exist


def write_hash_file(folder, hashes=None, exist_hash=None):
    if exist_hash is None:
        exist_hash = []
    if hashes is None:
        hashes = {}
    hash_file = os.path.join(folder, "hash.json")
    hash_path = os.path.join(folder, "hash_path.json")
    with open(hash_path, 'w') as f:
        json.dump(exist_hash, f, ensure_ascii=False)
    with open(hash_file, 'w') as f:
        json.dump(hashes, f, ensure_ascii=False)


def check(soup):
    not_found_h1 = soup.select("h1[class=entry-title]")
    if not_found_h1:
        return not not_found_h1[0].contents[0] == "404 NOT FOUND"
    return True


def covert_date_url_to_url_file(info: Tuple[date, str]) -> Tuple[str, str]:
    img_name = info[1].split("/")[-1]
    modify_img_name = f"{info[0]} {img_name}"
    return info[1], modify_img_name


def get_page_data(soup, after):
    es = soup.select("div[class^=img_wrapper]")

    image_list = []

    for element in es:
        date_element = element.select("div[class=img_footer] span")
        url_element = element.find("a")
        if date_element and url_element is not None:
            img_date = str_to_date(date_element[0].contents[0])
            url = url_element.attrs['href']

            if url[-4:-3] == '.' and img_date > after:
                image_list.append((img_date, url))
                # rint(date)
                # rint(url)

    return image_list


"""
    with open('readme.txt') as f:
        lines = f.readlines()
    image = imread(path)
    if not image is None:
        #if image.shape[1] > image.shape[0]:
        #    image = imutils.resize(image, width = 200)
        #else:
        #    image = imutils.resize(image, height = 200)
        image = imutils.resize(image, height = 240)
        image = QtGui.QImage(image.data, image.shape[1], image.shape[0], image.strides[0], QtGui.QImage.Format_RGB888).rgbSwapped()
        self.image_frame.setPixmap(QtGui.QPixmap.fromImage(image))
    else:
        print(f"Not found: {path}")
"""


def parse_url_get_images(url: AnyStr,
                         date_after: str,
                         folder: AnyStr,
                         thumb_size: QSize,
                         image_out: Signal,
                         retry: int,
                         check_cancel: Callable[[], bool] = None):
    return MyThreadPool.asyncio(parse_async, [url, date_after, folder, thumb_size, image_out, retry, check_cancel])


async def parse_async(loop, url: AnyStr, date_after: str,
                      folder: AnyStr,
                      thumb_size: QSize,
                      image_out: Signal,
                      retry: int,
                      check_cancel: Callable[[], bool] = None):
    print("BitGirl >> update")

    soup = get_soup(url, timeout=(8.0, 12.0))
    TextOut.out(f"Try to Update: {folder}")

    image_list = get_page_data(soup, date_after)
    # max_page_div = soup.find_all("div", class_="pageLinkNum_border pageLinkNum_border_last")
    max_page_a = soup.find_all("a", class_="last_link")
    if max_page_a:
        max_page_a = max_page_a[0]

    for t in soup.find_all("span", class_="dots"):
        for item in t.next_siblings:
            if isinstance(item, Tag):
                if 'class' in item.attrs and 'next' in item.attrs['class']:
                    break
                max_page_a = item

    #    max_page_b = max_page_b[0].next_siblings
    print(max_page_a)

    # if max_page_div:
    #    max_page_a = max_page_div[0].find("a")
    if max_page_a:
        max_page = int(max_page_a.attrs['href'].rpartition("/")[-1])

        TextOut.out(f"Page To Load: {max_page}")

        async def get_page(in_url):
            h_str = await get_html_async(loop, in_url)
            if isinstance(h_str, Exception):
                return False
            image_list.extend(get_page_data(get_soup_from_text(h_str), date_after))
            return True

        as_jobs = []
        for i in range(2, max_page + 1):
            as_jobs.append(get_page(f"{url}/page/{i}"))
        await asyncio.gather(*as_jobs)
    else:
        next_page_div = soup.select_one("div[class=ranking_page_link_zengo_wrapper_inner]")
        if next_page_div:
            next_page = next_page_div.select_one("span[class=right] a")
            if next_page:
                ex_url = next_page.attrs['href']
                ex_soup = get_soup(ex_url)
                image_list.extend(get_page_data(ex_soup, date_after))
                print(ex_url)

    if check_cancel and check_cancel():
        return None
        # date_check = datetime.date()
    image_list = list(dict.fromkeys(image_list))

    if image_list:
        latest_date = str(max(list(map(lambda x: x[0], image_list))))

        image_list = sorted(image_list, key=lambda x: x[0])
        url_list = list(map(covert_date_url_to_url_file, image_list))

        TextOut.out(f"Image To Download: {len(url_list)}")

        hashes, exist_hash, write_hash = read_hash_file(folder)

        # jobs = chunks(list(map(lambda x: (loop, x[0], None, join_path(folder, x[1]), retry), url_list)), 30)
        jobs = list(map(lambda x: (loop, x[0], None, join_path(folder, x[1]), retry), url_list))

        async def download_and_show(params: tuple):
            d_url, img_path = await download_with_retry(*params)
            if d_url:
                if not write_hash:
                    img = MyImageSource(img_path, thumb_size)
                    image_out.emit(img_path, thumb_size, img)
                    return True
                with Image.open(img_path) as img:
                    try:
                        temp_hash = str(imagehash.average_hash(img, 8))
                    except Exception as ex:
                        print(ex)
                        return False
                    if temp_hash in hashes:
                        print("Dup", img_path)
                        os.remove(img_path)
                    else:
                        exist_hash.append(img_path)
                        hashes[temp_hash] = img_path
                        img = MyImageSource(img_path, thumb_size)
                        image_out.emit(img_path, thumb_size, img)
                        return True
            return False

        dl_jobs = []
        for job in jobs:
            dl_jobs.append(download_and_show(job))
        await asyncio.gather(*dl_jobs)

        if write_hash:
            write_hash_file(folder, hashes, exist_hash)

        TextOut.out("Update Completed")
        return folder, latest_date
    else:
        TextOut.out("No Update Found")
        return folder, None

# print(url_list)
