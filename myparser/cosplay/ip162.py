import asyncio
from typing import Callable

from myparser.cosplay import CosplayParserBase, get_soup, get_folder_name, signal_out, get_image_data, \
    process_image_list, get_soup_async
from myqt.MyQtWorker import MyThreadPool


class Parse162(CosplayParserBase):
    tag = "https://162.209.156.219"
    group = "XiuRen"

    @staticmethod
    def parse(url,
              use_path,
              check_cancel: Callable[[], bool] = None):
        MyThreadPool.asyncio(Parse162.parse_async, [url, use_path, check_cancel])

    @staticmethod
    async def parse_async(loop, url,
                          use_path,
                          check_cancel: Callable[[], bool] = None):

        if url.find("category") >= 0:
            soup = get_soup(url)
            cat_element = soup.select("h2[class=entry-title]")
            print(len(cat_element))
            f = []
            for cat_url in cat_element:
                page_url = cat_url.select_one("a")
                if page_url:
                    page_url = page_url.attrs["href"]
                    print(page_url)
                    f.append(Parse162.parse_single(loop, page_url, use_path, 1, check_cancel))
            await asyncio.gather(*f)
        else:
            await Parse162.parse_single(loop, url, use_path, 0, check_cancel)

    @staticmethod
    async def parse_single(loop, url: str,
                           use_path,
                           mode: int,
                           check_cancel: Callable[[], bool] = None):

        soup = await get_soup_async(loop, url)

        folder = get_folder_name(soup, "span[class=post-title]")
        if folder is None:
            signal_out.info_out.emit(f"Error: Title not Found << {url}")
            return

        if mode == 1 and folder.find(Parse162.group) < 0:
            signal_out.info_out.emit(f"Skip: {folder}")
            return

        folder = folder.replace('-', ' ').replace("[XIAOYU语画界] Vol.", "").replace("[XiuRen秀人网] No.", "")
        try_split = folder.split(" ")
        if len(try_split) > 2:
            folder = f"{try_split[0]} {try_split[1]}"

        signal_out.info_out.emit(f"Download to: {folder}")

        page_list = []
        page_element = soup.select("a[class=post-page-numbers]")
        if page_element:
            for e in page_element:
                page_list.append(e.attrs['href'])

        image_list = get_image_data(soup, ["div[class^=spotlight]", None, "data-src"])
        for p in page_list:
            p_soup = await get_soup_async(loop, p)
            image_list.extend(get_image_data(p_soup, ["div[class^=spotlight]", None, "data-src"]))

        image_list = [f"{Parse162.tag}{i}" for i in image_list]

        if image_list:
            folder_image = image_list[0].replace("0.webp", "cover/0.webp")
            image_list.append(folder_image)

            await process_image_list(loop, url, folder, image_list, use_path, check_cancel, folder_image)
