import asyncio
from typing import Callable
from urllib.parse import urlsplit

from myparser.cosplay import *
from myqt.MyQtWorker import MyThreadPool


async def convert_wnacg_page_to_img(loop, url, iid) -> list:
    soup = await get_soup_async(loop, url)
    retry = 0
    while not soup:
        if retry > 5:
            return []
        else:
            retry = retry + 1
        soup = await get_soup_async(loop, url)

    return ["https:" + get_image_data(soup, ["div[class=posselect]", "img", "src"])[0], iid]


class ParseWnacg(CosplayParserBase):
    tag = "https://www.wnacg.org/"

    @staticmethod
    def parse(url,
              use_path,
              check_cancel: Callable[[], bool] = None):
        MyThreadPool.asyncio(ParseWnacg.parse_async, [url, use_path, check_cancel])

    @staticmethod
    async def parse_async(loop, url,
                          use_path,
                          check_cancel: Callable[[], bool] = None):

        base_url = "{0.scheme}://{0.netloc}/".format(urlsplit(url))

        soup = get_soup(url)

        folder = get_folder_name(soup, "h2")
        print(folder)
        if folder is None:
            signal_out.info_out.emit(f"Error: Title not Found << {url}")
            return
        signal_out.info_out.emit(f"Download to: {folder}")

        has_next = True
        image_page_urls = []

        while has_next:
            current_page = get_image_data(soup, ["div[class='pic_box tb']", "a", "href"])
            current_page = [base_url + u for u in current_page]
            image_page_urls.extend(current_page)

            page_element = soup.select_one('span:-soup-contains("後頁")')
            if page_element:
                next_url = page_element.find("a").attrs['href']
                soup = get_soup(base_url + next_url)
            else:
                has_next = False

        # print(image_page_urls)
        image_page_urls = [[u, i] for i, u in enumerate(image_page_urls)]

        if check_cancel and check_cancel():
            return None
        signal_out.info_out.emit(f"Page To Check: {len(image_page_urls)}")

        f = []
        for ip in image_page_urls:
            f.append(convert_wnacg_page_to_img(loop, *ip))
        # image_list = MyThreadPool.map(None, image_page_urls, convert_wnacg_page_to_img)
        # image_list = pool.map(convert_wnacg_page_to_img, image_page_urls)
        image_list = await asyncio.gather(*f)

        image_list = [u for u in image_list if len(u) > 1]
        image_list = [u[0] for u in sorted(image_list, key=lambda x: x[1])]

        await process_image_list(loop, url, folder, image_list, use_path, check_cancel)
