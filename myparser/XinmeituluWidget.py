import os
import sys
from multiprocessing import Pool
from typing import AnyStr, Callable, Optional

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import *
from PySide6.QtWidgets import QLineEdit, QLabel
from qt_material import apply_stylesheet
import pyperclip

from MyCommon import chunks, download_with_retry, valid_folder_name, join_path
from myparser.InfoImage import InfoImage
from myparser.ParserCommon import get_soup
from myqt.MyQtCommon import MyButton, MyVBox, MyHBox
from myqt.MyQtImage import MyImageSource, MyImageBox
from myqt.MyQtWorker import MyThread
from zhtools.langconv import Converter


def get_image_data(soup, tag):
    es = soup.select(tag[0])
    image_list = []
    try:
        for element in es:
            url_element = element.find(tag[1])
            url = url_element.attrs[tag[2]]
            image_list.append(url)
    except Exception as e:
        print(e)
    return image_list


def get_folder_name(soup, tag, zh: bool = False):
    folder_element = soup.select_one(tag)
    if folder_element:
        try:
            folder = folder_element.text.strip('\n')
            if zh:
                folder = Converter("zh-hant").convert(folder)
            folder = valid_folder_name(folder)
            print(folder)
            return folder
        except Exception as e:
            print(e)
    return None


def get_page_xiu_mei_tulu(soup, img_size: QSize):
    es = soup.select("figure[class^=figure]")
    url_list = []

    for element in es:
        url_element = element.find("a")
        url = url_element.attrs['href']

        name = ""
        name_element = element.find("figcaption")

        if name_element:
            name = name_element.text.strip('\n')

        img = None
        img_element = element.find("img")
        if img_element:
            img_url = img_element.attrs['src']
            img = MyImageSource(img_url).as_size(img_size)

        url_list.append((name, url, img))

    return url_list


def create_folder(folder, use=None):
    if use is None:
        out_path = join_path("C:/cosplay", folder)
    else:
        out_path = use
    os.makedirs(out_path, exist_ok=True)
    return out_path


class XinmeituluListWidget(QtWidgets.QWidget):
    info_download = Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.img_size = QSize(100, 140)
        self.result = []

        self.txt_url = QLineEdit("")
        self.but_paste = MyButton('Paste', self.paste)
        self.but_parse = MyButton('Parse', self.parse)
        self.but_next = MyButton('Next', self.next)

        h_bar = MyHBox().addAll(self.but_paste,
                                self.but_parse,
                                self.txt_url,
                                self.but_next)

        self.v_result = MyVBox()
        v_box = MyVBox().addAll(h_bar, self.v_result)

        self.setMinimumWidth(1100)
        self.setLayout(v_box)

    def paste(self):
        self.txt_url.setText(pyperclip.paste())

    def parse(self):
        link = self.txt_url.text()
        if link.startswith("https://www.xinmeitulu.com/"):
            run_thread = MyThread(None)
            run_thread.set_run(self.parse_url, link)
            run_thread.on_finish(self.parse_finish)
            run_thread.start()

    def next(self):
        link = self.txt_url.text()
        try:
            if link[-2:-1] == "/":
                link = link[:-1] + str(int(link[-1:]) + 1)
            else:
                link += "page/2"
            self.txt_url.setText(link)
        except Exception as e:
            print(e)

    def parse_url(self,
                  url,
                  thread: QThread):
        soup = get_soup(url)
        self.result = get_page_xiu_mei_tulu(soup, self.img_size)

    def parse_finish(self):
        rows = chunks(self.result, 3)

        self.v_result.clear()

        for row in rows:
            row_box = MyHBox()
            for item in row:
                print(item)
                txt_name = QLineEdit(item[0])
                but_down = MyButton('Apply Link', self.download, [item[1]])
                v_box = MyVBox().addAll(txt_name, but_down)
                if item[2]:
                    img_box = MyImageBox(self.img_size, item[2])

                    h_box = MyHBox().addAll(img_box, v_box)
                else:
                    h_box = MyHBox().addAll(v_box)
                row_box.add(h_box)

            self.v_result.add(row_box)

        # self.setLayout(self.v_box)

    def download(self, url: str):
        self.info_download.emit(url)


class XinmeituluWidget(QtWidgets.QWidget):
    info_out = Signal(str, name="info_out")
    download_finish = Signal(str)
    download_start = Signal(str)

    def __init__(self, folder_func: Callable[[AnyStr, Optional[AnyStr]], AnyStr] = None, retry: int = 999,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.folder_func = folder_func
        self.retry = retry
        self.txt_url = QLineEdit("")
        self.but_paste = MyButton('Paste', self.paste)
        self.but_download = MyButton('Download', self.download, param=[None])

        h_box = MyHBox().addAll(self.but_paste,
                                self.but_download,
                                self.txt_url)

        self.setMinimumWidth(800)
        self.setLayout(h_box)

    def paste(self):
        self.txt_url.setText(pyperclip.paste())

    def download(self, use_path: AnyStr = None):
        link = self.txt_url.text()
        parser = self.get_parser(link)
        print("USE", use_path)
        if parser is not None:
            run_thread = MyThread(None)
            run_thread.set_run(parser, link, use_path)
            run_thread.start()

    def get_parser(self, link):
        if link.startswith("https://www.xinmeitulu.com/"):
            return self.parse_xin_mei_tulu
        elif link.startswith("https://ja.hentai-cosplays.com/") or link.startswith("https://hentai-cosplays.com/"):
            return self.parse_jp_hentai
        elif link.startswith("https://eyecoser.com/"):
            return self.parse_eyecoser
        return None

    def parse_eyecoser(self,
                       url,
                       use_path,
                       thread: QThread):
        soup = get_soup(url)

        folder = get_folder_name(soup, "span[class=current]")
        if folder is None:
            self.info_out.emit(f"Error: Title not Found << {url}")
            return
        self.info_out.emit(f"Download to: {folder}")

        image_list = get_image_data(soup, ["figure[class=wp-block-image]", "img", "data-src"])
        self.process_image_list(url, folder, image_list, use_path, thread)

    def parse_jp_hentai(self,
                        url,
                        use_path,
                        thread: QThread):
        soup = get_soup(url)

        folder = get_folder_name(soup, "h2")
        if folder is None:
            self.info_out.emit(f"Error: Title not Found << {url}")
            return
        self.info_out.emit(f"Download to: {folder}")

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

        self.info_out.emit(f"Page to scan: {page_count}")

        image_list = get_image_data(soup, ["div[class=icon-overlay]", "img", "src"])
        for i in range(2, page_count + 1):
            page_url = f"{url}page/{i}/"
            print(page_url)
            soup = get_soup(page_url)
            image_list += get_image_data(soup, ["div[class=icon-overlay]", "img", "src"])

        # print(image_list)

        self.process_image_list(url, folder, image_list, use_path, thread)

    def parse_xin_mei_tulu(self,
                           url,
                           use_path,
                           thread: QThread):
        soup = get_soup(url)

        folder = get_folder_name(soup, "h1[class=h3]", zh=True)
        if folder is None:
            self.info_out.emit(f"Error: Title not Found << {url}")
            return
        self.info_out.emit(f"Download to: {folder}")

        image_list = get_image_data(soup, ["figure[class^=figure]", "a", "href"])
        self.process_image_list(url, folder, image_list, use_path, thread)

    def process_image_list(self, url, folder, image_list, use_path, thread: QThread):
        with Pool() as pool:
            if thread.isInterruptionRequested():
                return None

            if image_list:
                self.info_out.emit(f"Image To Download: {len(image_list)}")

                if self.folder_func is None:
                    out_path = create_folder(folder, use_path)
                else:
                    out_path = self.folder_func(folder, use_path)

                self.download_start.emit(out_path)

                info = {'url': url, 'lastUpdate': "2000-01-01", 'count': len(image_list)}
                InfoImage.save_info(out_path, info)

                job_list = []

                for i, url in enumerate(image_list):
                    job_list.append((url, "", '{}/{:04}.jpg'.format(out_path, i), self.retry))

                jobs = chunks(job_list, 150)

                for job in jobs:
                    pool.starmap(download_with_retry, job)

                    if thread.isInterruptionRequested():
                        break

                self.info_out.emit(f"Complete << {folder}")
                print("complete")
                self.download_finish.emit(out_path)
                return folder
            else:
                self.info_out.emit("Not Found")
        return None

    def standalone(self):
        but_exit = MyButton('Exit', self.safe_exit)
        self.txt_info = [QLabel(self), QLabel(self), QLabel(self), QLabel(self), QLabel(self)]
        for txt in self.txt_info:
            txt.setMaximumWidth(900)
        self.info_out.connect(self.action_info_out)
        self.v_box.addAll(but_exit, *self.txt_info)

    @Slot(name="info_out")
    def action_info_out(self, mess):
        for i in range(0, len(self.txt_info) - 1):
            self.txt_info[i].setText(self.txt_info[i + 1].text())
        self.txt_info[-1].setText(mess)

    @Slot()
    def safe_exit(self):
        self.deleteLater()
        self.close()
        self.destroy()
        app.exit()


if __name__ == '__main__':
    app = QtCore.QCoreApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    user_theme = "dark_pink.xml"
    apply_stylesheet(app, theme=user_theme)

    # file = glob.glob("X:\Image\Twitter/*")
    # model = QFileSystemModel()
    # model.setRootPath("X:\Image\Twitter")

    screen = app.primaryScreen()
    print('Screen: %s' % screen.name())
    size = screen.size()
    print('Size: %d x %d' % (size.width(), size.height()))
    rect = screen.availableGeometry()
    print('Available: %d x %d' % (rect.width(), rect.height()))

    widget = XinmeituluWidget()
    widget.setWindowTitle(" ")
    widget.standalone()
    # widget.setWindowIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
    widget.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
    widget.show()

    sys.exit(app.exec())
