from typing import Callable

from myparser.cosplay import *
from myqt.MyQtWorker import MyThreadPool


class ParseXinmeitulu(CosplayParserBase):
    tag = "https://www.xinmeitulu.com/"

    @staticmethod
    def parse(url,
              use_path,
              check_cancel: Callable[[], bool] = None):
        MyThreadPool.asyncio(ParseXinmeitulu.parse_async, [url, use_path, check_cancel])

    @staticmethod
    async def parse_async(loop, url,
                          use_path,
                          check_cancel: Callable[[], bool] = None):
        soup = get_soup(url)

        folder = get_folder_name(soup, "h1[class=h3]", zh=True)
        if folder is None:
            signal_out.info_out.emit(f"Error: Title not Found << {url}")
            return
        signal_out.info_out.emit(f"Download to: {folder}")

        image_list = get_image_data(soup, ["figure[class^=figure]", "a", "href"])
        await process_image_list(loop, url, folder, image_list, use_path, check_cancel, base_url=url)
