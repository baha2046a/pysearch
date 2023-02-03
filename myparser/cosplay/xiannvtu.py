from typing import Callable

from myparser.cosplay import *
from myqt.MyQtWorker import MyThreadPool


class ParseXiannvtu(CosplayParserBase):
    tag = "https://www.xiannvtu.com/"

    @staticmethod
    def parse(url,
              use_path,
              check_cancel: Callable[[], bool] = None):
        MyThreadPool.asyncio(ParseXiannvtu.parse_async, [url, use_path, check_cancel])

    @staticmethod
    async def parse_async(loop, url,
                          use_path,
                          check_cancel: Callable[[], bool] = None):

        soup = get_soup(url, "utf-8")

        folder = get_folder_name(soup, "h2")
        if folder is None:
            signal_out.info_out.emit(f"Error: Title not Found << {url}")
            return
        signal_out.info_out.emit(f"Download to: {folder}")

        page_elements = soup.select_one("div[class=page]").select("a")
        page_list = set()

        for url in page_elements:
            if 'href' in url.attrs:
                page: str = url.attrs['href']
                print(page)
                if page.endswith("html"):
                    page_list.add("https://www.xiannvtu.com/v/" + page)

        image_elements = soup.select_one("div[class=picbox]")
        image_list = get_image_data(image_elements, ["img", None, "src"])

        for url in image_list:
            image_list += get_image_data(image_elements, ["img", None, "src"])

        await process_image_list(loop, url, folder, image_list, use_path, check_cancel)
