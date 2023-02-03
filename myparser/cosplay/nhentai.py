from typing import Callable

from myparser.ParserCommon import get_html_js
from myparser.cosplay import *
from myqt.MyQtWorker import MyThreadPool


class ParseNhentai(CosplayParserBase):
    tag = "https://nhentai.net/"

    @staticmethod
    def parse(url,
              use_path,
              check_cancel: Callable[[], bool] = None):
        MyThreadPool.asyncio(ParseNhentai.parse_async, [url, use_path, check_cancel])

    @staticmethod
    async def parse_async(loop, url,
                          use_path,
                          check_cancel: Callable[[], bool] = None):

        soup = get_soup(url)

        print(soup)

        folder = get_folder_name(soup, "h2.title")
        if folder is None:
            folder = get_folder_name(soup, "h1.title")
        if folder is None:
            signal_out.info_out.emit(f"Error: Title not Found << {url}")
            return
        folder = folder.replace("	", " ").replace(" [DL版]", "")
        signal_out.info_out.emit(f"Download to: {folder}")

        image_list = get_image_data(soup, ["img.lazyload", None, "data-src"])
        image_list = [u.replace("https://t", "https://i").replace("t.jpg", ".jpg").replace("t.png", ".png") for u in
                      image_list]

        remove = []
        for i, u in enumerate(image_list):
            if u.endswith("thumb.jpg") or u.endswith("cover.jpg"):
                remove.append(i)

        remove.reverse()
        for idx in remove:
            image_list.pop(idx)

        await process_image_list(loop, url, folder, image_list, use_path, check_cancel)
