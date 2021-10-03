import json
import os
from multiprocessing import Pool
from typing import Any

import imagehash
from PIL import Image
from PySide6.QtCore import QThread, QSize

from MyCommon import list_jpg, str_to_date, chunks, download
from myparser.InfoImage import InfoImage
from myparser.ParserCommon import get_soup, get_html, get_soup_from_text
from myqt.MyQtImage import MyImageSource


def search_dup(folder,
               as_size,
               signal_info,
               signal_old, signal_new,
               progress_reset_signal, progress_signal,
               thread: QThread,
               auto_del=True):
    files = list_jpg(folder)
    if files:
        hashes = {}
        parent = []
        progress = 0
        progress_reset_signal.emit(len(files))
        for _path in files:
            path = _path.replace("\\", "/")
            progress += 1
            progress_signal.emit(progress)
            if path.endswith("folder.jpg"):
                continue
            if thread.isInterruptionRequested():
                break
            with Image.open(path) as img:
                temp_hash = imagehash.average_hash(img, 8)
                if temp_hash in hashes:
                    if hashes[temp_hash] not in parent:
                        parent.append(hashes[temp_hash])
                        i = MyImageSource(hashes[temp_hash], as_size)
                        signal_old.emit(hashes[temp_hash], as_size, i)
                    if auto_del:
                        signal_info.emit(f"Delete Image: {path}")
                        os.remove(path)
                    else:
                        n = MyImageSource(path, as_size)
                        signal_new.emit(path, as_size, n)
                else:
                    hashes[temp_hash] = path
    return True


def check(soup):
    not_found_h1 = soup.select("h1[class=entry-title]")
    if not_found_h1:
        return not not_found_h1[0].contents[0] == "404 NOT FOUND"
    return True


def load_info(path):
    info_path = os.path.join(path, InfoImage.FILE)
    try:
        with open(info_path, encoding="utf-8") as f:
            data = json.load(f)
            info = InfoImage(**data)
            print(info)
            return data
    except Exception as e:
        print(e)
        return None


def save_info(path, data):
    if data is not None:
        info_path = os.path.join(path, InfoImage.FILE)
        try:
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(e)
        finally:
            f.close()


def covert_date_url_to_url_file(info):
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


def parse_url_get_images(url,
                         date_after,
                         folder,
                         thumb_size: QSize,
                         txt_out,
                         image_out,
                         thread: QThread):
    print("BitGirl >> update")

    soup = get_soup(url)
    txt_out.emit(f"Try to Update: {folder}")

    image_list = get_page_data(soup, date_after)
    max_page_div = soup.find_all("div", class_="pageLinkNum_border pageLinkNum_border_last")

    with Pool() as pool:
        if max_page_div:
            max_page_a = max_page_div[0].find("a")
            if max_page_a is not None:
                max_page = int(max_page_a.attrs['href'].rpartition("/")[-1])

                txt_out.emit(f"Page To Load: {max_page}")

                url_list = []

                for i in range(2, max_page + 1):
                    url_list.append(f"{url}/page/{i}")

                html_str_list = pool.map(get_html, url_list)

                for t in html_str_list:
                    image_list.extend(get_page_data(get_soup_from_text(t), date_after))
        else:
            next_page_div = soup.select_one("div[class=ranking_page_link_zengo_wrapper_inner]")
            if next_page_div:
                next_page = next_page_div.select_one("span[class=right] a")
                if next_page:
                    ex_url = next_page.attrs['href']
                    ex_soup = get_soup(ex_url)
                    image_list.extend(get_page_data(ex_soup, date_after))
                    print(ex_url)

        if thread.isInterruptionRequested():
            return None
            # date_check = datetime.date()
        image_list = list(dict.fromkeys(image_list))

        if image_list:
            latest_date = str(max(list(map(lambda x: x[0], image_list))))

            image_list = sorted(image_list, key=lambda x: x[0])
            url_list = list(map(covert_date_url_to_url_file, image_list))

            txt_out.emit(f"Image To Download: {len(url_list)}")

            # print(threading.get_ident())

            jobs = chunks(list(map(lambda x: (x[0], None, os.path.join(folder, x[1])), url_list)), 30)

            for job in jobs:
                download_result = pool.starmap(download, job)

                for d in download_result:
                    if d:
                        url, img_path = d
                        txt_out.emit(f"Saved Image From {url} To {img_path}")
                        img = MyImageSource(img_path, thumb_size)
                        image_out.emit(img_path, thumb_size, img)
                        # time.sleep(self.update_delay)
                    else:
                        txt_out.emit(f"Error Download Image From {d[0]}")

                if thread.isInterruptionRequested():
                    break

            if thread.isInterruptionRequested():
                return None

            txt_out.emit("Update Completed")
            return folder, latest_date
        else:
            txt_out.emit("No Update Found")
    return None

    # print(url_list)
