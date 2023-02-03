from typing import Callable

from myparser.cosplay import *


class ParseAsiaPretty(CosplayParserBase):
    tag = "https://asiapretty.com/"

    @staticmethod
    def parse(url,
              use_path,
              check_cancel: Callable[[], bool] = None):

        soup = get_soup(url)

        folder = get_folder_name(soup, "h1")
        if folder is None:
            signal_out.info_out.emit(f"Error: Title not Found << {url}")
            return
        signal_out.info_out.emit(f"Download to: {folder}")

        page_count = 1
        page_element = soup.select_one('a.last')
        if page_element:
            try:
                last_page_url = page_element.attrs['href']
                print(last_page_url)
                page_count = int(last_page_url.rsplit('/', 2)[-2])
                print(page_count)
            except Exception as e:
                print(e)

        signal_out.info_out.emit(f"Page to scan: {page_count}")

        image_element = soup.select_one("div.entry-inner")
        image_list = get_image_data(image_element, ["img", None, "src"])
        for i in range(2, page_count):
            page_url = f"{url}{i}/"
            print(page_url)
            soup = get_soup(page_url)
            image_element = soup.select_one("div.entry-inner")
            image_list.extend(get_image_data(image_element, ["img", None, "src"]))

        print(image_list)

        process_image_list(url, folder, image_list, use_path, check_cancel, base_url=url)

