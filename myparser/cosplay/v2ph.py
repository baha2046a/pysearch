from typing import Callable

from myparser.cosplay import *
from myqt.MyQtWorker import MyThreadPool


class ParseV2ph(CosplayParserBase):
    tag = "https://www.v2ph.com/"

    @staticmethod
    def parse(url,
              use_path,
              check_cancel: Callable[[], bool] = None):
        MyThreadPool.asyncio(ParseV2ph.parse_async, [url, use_path, check_cancel])

    @staticmethod
    async def parse_async(loop, url,
                          use_path,
                          check_cancel: Callable[[], bool] = None):

        soup = get_soup(url)

        folder = get_folder_name(soup, "h1.h5")
        if folder is None:
            signal_out.info_out.emit(f"Error: Title not Found << {url}")
            return
        signal_out.info_out.emit(f"Download to: {folder}")

        page_count = 1
        page_element = soup.select('a.page-link')
        for link in page_element:
            print(link.text)
            if link.text == "最後" or link.text == "末页":
                try:
                    last_page_url = link.attrs['href']
                    print(last_page_url)
                    find_page = last_page_url.find('page=')
                    if find_page > 0:
                        page_count = last_page_url[find_page + 5:]
                    find_and = page_count.find("&")
                    if find_and > 0:
                        page_count = page_count[:find_and]
                    page_count = int(page_count)
                except Exception as e:
                    print(e)

        signal_out.info_out.emit(f"Page to scan: {page_count}")

        image_list = get_image_data(soup, ["div.album-photo", "img", "data-src"])
        for i in range(2, page_count + 1):
            page_url = f"{url}?page={i}"
            print(page_url)
            soup = await get_soup_async(loop, page_url)
            image_list.extend(get_image_data(soup, ["div.album-photo", "img", "data-src"]))

        # print(image_list)

        await process_image_list(loop, url, folder, image_list, use_path, check_cancel, base_url=url)
