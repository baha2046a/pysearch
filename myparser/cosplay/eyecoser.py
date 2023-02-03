from typing import Callable

from myparser.cosplay import *
from myqt.MyQtWorker import MyThreadPool


class ParseEyecoser(CosplayParserBase):
    tag = "https://eyecoser.com/"

    @staticmethod
    def parse(url,
              use_path,
              check_cancel: Callable[[], bool] = None):
        MyThreadPool.asyncio(ParseEyecoser.parse_async, [url, use_path, check_cancel])

    @staticmethod
    async def parse_async(loop, url,
                          use_path,
                          check_cancel: Callable[[], bool] = None):
        soup = get_soup(url)

        folder = get_folder_name(soup, "span[class=current]")
        if folder is None:
            signal_out.info_out.emit(f"Error: Title not Found << {url}")
            return
        signal_out.info_out.emit(f"Download to: {folder}")

        image_list = get_image_data(soup, ["figure[class=wp-block-image]", "img", "data-src"])
        await process_image_list(loop, url, folder, image_list, use_path, check_cancel, re=1)
