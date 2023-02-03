from typing import Callable

from myparser.cosplay import *


class ParseXsnvshen(CosplayParserBase):
    tag = "https://www.xsnvshen.com/"
    cover = "https://img.xsnvshen.com/thumb_205x308/album/22162/"

    @staticmethod
    def parse(url: str,
              use_path,
              check_cancel: Callable[[], bool] = None):

        soup = get_soup(url, "utf-8")

        folder = get_folder_name(soup, "h1")
        if folder is None:
            signal_out.info_out.emit(f"Error: Title not Found << {url}")
            return

        p = folder.find("No.")
        if p > 0:
            folder = folder[p+3:]

        signal_out.info_out.emit(f"Download to: {folder}")

        page_elements = soup.select("img[class='origin_image lazy']")
        #image_list = [ParseXsnvshen.cover + url.rsplit("/", 1)[-1] + "/cover.jpg"]
        if len(page_elements):
            image_list = ["https:" + page_elements[0].attrs["data-original"].replace("000.jpg", "cover.jpg")]
            image_list.extend(["https:" + u.attrs["data-original"] for u in page_elements])

            print(image_list)
            process_image_list(url, folder, image_list, use_path, check_cancel, base_url=url)
