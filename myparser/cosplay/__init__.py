import asyncio
import os
from typing import Callable, AnyStr, Optional

from PySide6.QtCore import *

from MyCommon import valid_folder_name, join_path, chunks, download_retry
from myparser import ParserCommon
from myparser.InfoImage import InfoImage
from myparser.cosplay.base import CosplayParserBase
from myqt.MyQtWorker import MyThreadPool
from zhtools.langconv import Converter

__all__ = ["CosplayParserBase",
           "QThread", "get_soup", "get_soup_async",
           "get_image_data", "get_folder_name", "signal_out", "process_image_list"]

retry = 5


def get_soup(url, encode=None):
    return ParserCommon.get_soup(url, encode)


async def get_soup_async(loop, url, encode=None):
    result = await loop.run_in_executor(None, lambda: ParserCommon.get_soup(url, encode))
    return result


def get_image_data(soup, tag):
    es = soup.select(tag[0])
    image_list = []
    try:
        for element in es:
            if tag[1] is not None:
                url_element = element.find(tag[1])
            else:
                url_element = element
            url = url_element.attrs[tag[2]]
            image_list.append(url)
    except Exception as e:
        print(e)
    return image_list


def get_folder_name(soup, tag, zh: bool = False):
    folder_element = soup.select_one(tag)

    if folder_element:
        try:
            folder = folder_element.text.strip('\n')
            if zh:
                folder = Converter("zh-hant").convert(folder)
            folder = valid_folder_name(folder)
            print(folder)
            return folder
        except Exception as e:
            print(e)
    return None


def create_folder(folder, use=None):
    if use is None:
        out_path = join_path("C:/cosplay", folder)
    else:
        out_path = use
    os.makedirs(out_path, exist_ok=True)
    return out_path


async def process_image_list(loop, url,
                             folder,
                             image_list,
                             use_path,
                             check_cancel: Callable[[], bool] = None,
                             folder_image=None,
                             re: int = retry,
                             base_url: str = None):
    if check_cancel and check_cancel():
        return None

    if image_list:
        signal_out.info_out.emit(f"Image To Download: {len(image_list)}")

        out_path = folder_func(folder, use_path)

        signal_out.download_start.emit(out_path)

        info = {'url': url, 'lastUpdate': "2000-01-01", 'count': len(image_list)}
        InfoImage.save_info(out_path, info)

        job_list = []

        for i, url in enumerate(image_list):
            if url[-3:] == "png":
                job_list.append(download_retry([loop, url, "", '{}/{:04}.png'.format(out_path, i), re, base_url]))
            else:
                job_list.append(download_retry([loop, url, "", '{}/{:04}.jpg'.format(out_path, i), re, base_url]))

        if folder_image:
            job_list.append(download_retry([loop, folder_image, "", f"{out_path}/folder.jpg", re]))

        await asyncio.gather(*job_list)

        signal_out.info_out.emit(f"Complete << {folder}")
        print("complete")
        signal_out.download_finish.emit(out_path)
        return folder
    else:
        signal_out.info_out.emit("Not Found")


class CosplayParserSignal(QObject):
    info_out = Signal(str)
    download_finish = Signal(str)
    download_start = Signal(str)


folder_func: Callable[[AnyStr, Optional[AnyStr]], AnyStr] = create_folder
signal_out = CosplayParserSignal()
