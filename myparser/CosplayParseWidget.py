import sys
from typing import AnyStr, Callable, Optional

import pyperclip
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import *
from PySide6.QtWidgets import QLineEdit, QLabel
from qt_material import apply_stylesheet

from MyCommon import chunks
from myparser import cosplay
from myparser.ParserCommon import get_soup
from myparser.cosplay.parser import CosplayParser
from myqt.MyQtCommon import MyButton, QtVBox, QtHBox
from myqt.QtImage import MyImageSource, MyImageBox
from myqt.MyQtWorker import MyThread


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


class XinmeituluListWidget(QtWidgets.QWidget):
    info_download = Signal(str)

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.img_size = QSize(100, 140)
        self.result = []

        self.txt_url = QLineEdit("")
        self.but_paste = MyButton('Paste', self.paste)
        self.but_parse = MyButton('Parse', self.parse)
        self.but_next = MyButton('Next', self.next)

        h_bar = QtHBox().addAll(self.but_paste,
                                self.but_parse,
                                self.txt_url,
                                self.but_next)

        self.v_result = QtVBox()
        v_box = QtVBox().addAll(h_bar, self.v_result)

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
            row_box = QtHBox()
            for item in row:
                print(item)
                txt_name = QLineEdit(item[0])
                but_down = MyButton('Apply Link', self.download, [item[1]])
                v_box = QtVBox().addAll(txt_name, but_down)
                if item[2]:
                    img_box = MyImageBox(self, self.img_size, item[2])

                    h_box = QtHBox().addAll(img_box, v_box)
                else:
                    h_box = QtHBox().addAll(v_box)
                row_box.add(h_box)

            self.v_result.add(row_box)

        # self.setLayout(self.v_box)

    def download(self, url: str):
        self.info_download.emit(url)


class CosplayParseWidget(QtWidgets.QWidget):
    info_out = cosplay.signal_out.info_out
    download_finish = cosplay.signal_out.download_finish
    download_start = cosplay.signal_out.download_start

    def __init__(self, parent, folder_func: Callable[[AnyStr, Optional[AnyStr]], AnyStr] = None, retry: int = 999,
                 *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        cosplay.folder_func = folder_func
        cosplay.retry = retry

        self.txt_url = QLineEdit("")
        self.but_paste = MyButton('Paste', self.paste)
        self.but_download = MyButton('Download', self.download, param=[None])

        h_box = QtHBox().addAll(self.but_paste,
                                self.but_download,
                                self.txt_url)

        self.setMinimumWidth(800)
        self.setLayout(h_box)

    def paste(self):
        self.txt_url.setText(pyperclip.paste())

    def download(self, use_path: AnyStr = None):
        link = self.txt_url.text()
        print("USE", use_path)
        CosplayParser.parse(link, use_path)

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

    widget = CosplayParseWidget(None)
    widget.setWindowTitle(" ")
    widget.standalone()
    # widget.setWindowIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
    widget.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
    widget.show()

    sys.exit(app.exec())
