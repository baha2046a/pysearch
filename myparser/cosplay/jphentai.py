from typing import Callable

from MyCommon import bypass_test
from myparser.cosplay import *
from myqt.MyQtWorker import MyThreadPool


class ParseJpHentai1(CosplayParserBase):
    tag = "https://ja.hentai-cosplays.com/"

    @staticmethod
    def parse(url,
              use_path,
              check_cancel: Callable[[], bool] = None):
        MyThreadPool.asyncio(ParseJpHentai1.parse_async, [url, use_path, check_cancel])

    @staticmethod
    async def parse_async(loop, url,
                          use_path,
                          check_cancel: Callable[[], bool] = None):
        soup = get_soup(url)

        folder = get_folder_name(soup, "h2")
        if folder is None:
            signal_out.info_out.emit(f"Error: Title not Found << {url}")
            return
        signal_out.info_out.emit(f"Download to: {folder}")

        page_count = 1
        page_element = soup.select_one('span:-soup-contains("最後へ")')
        if not page_element:
            page_element = soup.select_one('span:-soup-contains("last>>")')
        if page_element:
            try:
                last_page_url = page_element.find("a").attrs['href']
                print(last_page_url)
                page_count = int(last_page_url.rsplit('/', 2)[1])
            except Exception as e:
                print(e)

        signal_out.info_out.emit(f"Page to scan: {page_count}")

        image_list = get_image_data(soup, ["div[class=icon-overlay]", "img", "src"])
        for i in range(2, page_count + 1):
            page_url = f"{url}page/{i}/"
            print(page_url)
            soup = await get_soup_async(loop, page_url)
            image_list += get_image_data(soup, ["div[class=icon-overlay]", "img", "src"])
        image_list = [i.replace("/p=700", "") for i in image_list]

        # print(image_list)

        if len(image_list) > 0:
            bypass_test(image_list[0])
            await process_image_list(loop, url, folder, image_list, use_path, check_cancel)


class ParseJpHentai2(CosplayParserBase):
    tag = "https://hentai-cosplays.com/"

    @staticmethod
    def parse(url, use_path, thread: QThread):
        return ParseJpHentai1.parse(url, use_path, thread)
