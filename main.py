#!/usr/bin/env python3
import os
import subprocess
import sys
import webbrowser

import dill
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from qt_material import apply_stylesheet

from TextOut import TextOut
from MyCommon import list_jpg, str_to_date, join_path
from myparser import search_dup, parse_url_get_images
from myparser.CreateRecordDialog import CreateRecordDialog
from myparser.InfoImage import InfoImage
from myparser.ParserCommon import get_soup
from myqt.MyDirModel import MyDirModel
from myqt.MyQtCommon import MyHBox, MyVBox, MyButton
from myqt.MyQtFlow import MyQtScrollableFlow
from myqt.MyQtImage import MyImageBox, MyImageSource, MyImageDialog
from myqt.MyQtSetting import MySetting, SettingDialog
from myqt.MyQtWorker import MyThread


class MainWidget(QtWidgets.QWidget):
    info_out = Signal(str)
    image_signal = Signal(str, QSize, MyImageSource)
    new_image_signal = Signal(str, QSize, MyImageSource)
    progress_reset_signal = Signal(int)
    progress_signal = Signal(int)
    page_display = Signal(int)

    def __init__(self):
        super().__init__()

        # self.threadpool = QThreadPool()

        """
        database = QFontDatabase()
        fontFamilies = database.families()
        print(fontFamilies)
        awFont = QFont("Font Awesome 5 Free", 34)
        print(fa.icons['thumbs-up'])
        """

        self.but_settings = MyButton('Setting', self.action_settings)
        self.but_find_dup = MyButton('Find Dup', self.action_find_dup)
        self.but_show_folder_images = MyButton('Show', self.action_show_images_local)
        self.but_new_record = MyButton('+', self.action_add_record)

        h_box_top_bar = MyHBox().addAll(self.but_settings,
                                        self.but_find_dup,
                                        self.but_show_folder_images,
                                        self.but_new_record)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(1)

        self.image_frame = MyImageBox(QSize(300, 240))

        self.txt_url = QLineEdit("")
        # self.txt_url.setReadOnly(True)
        self.but_open_url = MyButton("Open", self.action_open_url)

        h_box_url = MyHBox().addAll(self.txt_url, self.but_open_url)

        self.txt_date = QLineEdit("")
        self.but_recheck = MyButton("Check", self.action_recheck)
        self.but_show_desc = MyButton("Desc", self.action_show_desc)
        self.but_update = MyButton("Update", self.action_download_new_img)

        h_box_date = MyHBox().addAll(self.txt_date,
                                     self.but_recheck,
                                     self.but_show_desc,
                                     self.but_update)

        self.model = MyDirModel()  # QFileSystemModel(self)  # QStringListModel()
        # self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot)
        # self.model.setReadOnly(False)

        # self.view.setViewMode(QListView.IconMode)
        self.model.signal_clicked.connect(self.action_list_click)
        self.model.signal_double_clicked.connect(self.action_list_double_click)
        self.model.view.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.but_exit = MyButton('Exit', self.safe_exit)

        h_box_bottom_bar = MyHBox().addAll(self.but_exit)

        v_box_left = MyVBox().addAll(h_box_top_bar,
                                     self.progress_bar,
                                     self.image_frame,
                                     h_box_url,
                                     h_box_date,
                                     self.model.tool_bar,
                                     self.model.view,
                                     h_box_bottom_bar)

        self.left_panel_widget = QWidget(self)
        self.left_panel_widget.setLayout(v_box_left)
        self.left_panel_widget.setFixedWidth(500)

        self.txt_info = [QLabel(self), QLabel(self), QLabel(self)]

        self.selected_path: str = ""

        self.image_flow = MyQtScrollableFlow()
        self.image_new_flow = MyQtScrollableFlow()
        # h_sep = HorizontalLine()
        # self.vbox_right.addWidget(h_sep)

        self.splitter_right = QSplitter(self)
        self.splitter_right.setOrientation(Qt.Vertical)
        self.splitter_right.addWidget(self.image_flow)
        self.splitter_right.addWidget(self.image_new_flow)

        if settings.contains("bitgirl/splitterSizes"):
            self.splitter_right.restoreState(settings.value("bitgirl/splitterSizes"))

        self.right_panel = MyVBox().addAll(self.splitter_right, *self.txt_info)

        layout = MyHBox().addAll(self.left_panel_widget, self.right_panel)

        self.setLayout(layout)

        self.thumb_size = QSize(140, 200)
        self.selected_data = None
        self.download_retry = 10
        self.apply_settings()

        self.progress_signal.connect(self.progress_bar.setValue)
        self.progress_reset_signal.connect(self.progress_bar.setMaximum)
        self.info_out.connect(self.action_info_out, Qt.QueuedConnection)
        self.image_signal.connect(self.action_show_img, Qt.QueuedConnection)
        self.new_image_signal.connect(self.action_show_new_img, Qt.QueuedConnection)
        self.page_display.connect(self.action_show_page, Qt.QueuedConnection)

        TextOut.out = self.info_out.emit
        # self.model.directoryLoaded.connect(self.model_loaded)

    def apply_settings(self):
        thumb_w = settings.valueInt("image/thumb/width", 140)
        thumb_y = settings.valueInt("image/thumb/height", 200)
        self.thumb_size = QSize(thumb_w, thumb_y)

        win_w = settings.valueInt("main/width", screen.availableGeometry().width() - 50)
        win_h = settings.valueInt("main/height", screen.availableGeometry().height() - 50)
        print(win_w, win_h)
        n_size = QSize(win_w, win_h).boundedTo(screen.availableGeometry().size())
        self.resize(n_size)

        self.download_retry = settings.valueFloat("bitgirl/download_retry")

        # self.set_dir(settings.value("bitgirl/root"))

        self.selected_path = settings.valueStr("bitgirl/last_selection", None)
        self.model.setRootPath(settings.valueStr("bitgirl/root"))
        self.model.makeSelect(self.selected_path)

        print(self.selected_path)

        # self.root_idx = self.model.setRootPath(settings.value("bitgirl/root"))
        # self.view.setRootIndex(self.root_idx)

    @QtCore.Slot(str, result=None)
    def model_loaded(self, path):
        print("model_loaded")
        if self.selected_path:
            self.model.makeSelect(self.selected_path)
            self.show_info()

    @Slot()
    def action_list_click(self, path, _1, _2) -> None:
        if path != self.selected_path:
            self.selected_path = path
            print(self.selected_path)
            settings.setValue("bitgirl/last_selection", self.selected_path)
            if path is not None and os.path.isdir(path):
                self.show_info()

    @Slot()
    def action_list_double_click(self, path, _1, _2) -> None:
        if path.split(".")[-1].lower() in MyImageDialog.FORMAT:
            dialog = MyImageDialog(self, path, screen.availableGeometry().size())
            dialog.exec()
            dialog.deleteLater()
        else:
            os.startfile(path)

    @Slot()
    def action_settings(self):
        dialog = SettingDialog(self, settings, "bitgirl")
        if dialog.exec():
            self.apply_settings()
        dialog.deleteLater()

    @Slot()
    def action_info_out(self, mess):
        for i in range(0, len(self.txt_info) - 1):
            self.txt_info[i].setText(self.txt_info[i + 1].text())
        self.txt_info[-1].setText(mess)

    @Slot()
    def action_show_img(self, _, as_size, img: MyImageSource) -> None:
        self.image_flow.show_img(as_size, img, self.action_show_large_img)
        QCoreApplication.processEvents()

    @Slot()
    def action_show_new_img(self, _, as_size, img: MyImageSource) -> None:
        self.image_new_flow.show_img(as_size, img, self.action_show_large_img)
        QCoreApplication.processEvents()

    @Slot()
    def action_find_dup(self):
        if self.selected_path is not None:
            dup_thread = MyThread("image_flow")
            dup_thread.set_run(search_dup, self.selected_path, self.thumb_size,
                               self.image_signal, self.new_image_signal,
                               self.progress_reset_signal, self.progress_signal)
            dup_thread.on_finish(on_before=self.action_find_dup_start)
            dup_thread.start()

    def action_find_dup_start(self):
        self.image_new_flow.clearAll()
        self.image_flow.clearAll()
        self.image_flow.group_by_date = False

    @Slot()
    def action_show_desc(self):
        url = self.txt_url.text()
        if url:
            soup = get_soup(url)
            div = soup.select("div[class=entry-desp]")
            if div:
                desc = div[0].contents[0]
                if desc:
                    # QMessageBox.about(self, "", str(desc))
                    msg_box = QMessageBox(None, "", "", QMessageBox.Ok, self)
                    msg_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    msg_box.setText("<h2>" + str(desc) + "</h2>")
                    msg_box.setWindowTitle("@" + url.split("/")[-1])
                    msg_box.setWindowFlags(Qt.Tool | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
                    msg_box.exec()

    @Slot()
    def action_recheck(self):
        if self.selected_path is not None:
            folder = self.selected_path.split("/")[-1]
            dialog = CreateRecordDialog(self, settings, folder, self.txt_url.text())

            if dialog.exec():
                url = dialog.txt_url.text()
                if url:
                    self.txt_url.setText(url)
                    self.selected_data['url'] = url
            dialog.deleteLater()

    @Slot()
    def action_add_record(self):
        dialog = CreateRecordDialog(self, settings)

        if dialog.exec():
            name = dialog.txt_name.text()
            url = dialog.txt_url.text()

            if name and url:
                match = self.model.makeSelect(name)

                # match(self.model.index(0,0), Qt.DisplayRole, name, 1, Qt.MatchExactly)
                if match:
                    self.info_out.emit(f"Record {name} Already Exist")
                else:
                    out_path, _ = self.model.mkdir(name)
                    self.info_out.emit(f"Create Directory: {out_path}")
                    info = {'url': url, 'lastUpdate': "2000-01-01", 'count': -1}
                    InfoImage.save_info(out_path, info)
                    self.show_info()

                # self.model_loaded(None)

    @Slot()
    def action_show_images_local(self, page=0):
        if self.selected_path is not None:
            run_thread = MyThread("image_flow")
            run_thread.set_run(self.async_load_images_local,
                               self.selected_path,
                               self.thumb_size, page)
            run_thread.on_finish(on_before=self.action_show_images_start)
            run_thread.start()

            print(sys.getrefcount(run_thread))

    def action_show_images_start(self):
        self.image_flow.clearAll()
        self.image_flow.group_by_date = True

    @Slot()
    def action_show_page(self, num: int):
        w = MyButton("1", self.action_show_images_local, param=[0])
        self.image_flow.addWidget(w)
        for i in range(num):
            w = MyButton(str(i + 2), self.action_show_images_local, param=[i + 1])
            self.image_flow.addWidget(w)

    def async_load_images_local(self, folder, as_size, page, thread: QThread):
        files = list_jpg(folder)
        files.sort(reverse=True)

        p = int(len(files) / 500)
        self.page_display.emit(p)

        files = files[page * 500:(page + 1) * 500]

        self.progress_reset_signal.emit(len(files))

        progress = 0

        for f in files:
            progress += 1
            self.progress_signal.emit(progress)
            if f.endswith("folder.jpg"):
                continue
            file = f.replace("\\", "/")
            img = MyImageSource(file, self.thumb_size)
            self.image_signal.emit(file, as_size, img)
            if QThread.isInterruptionRequested(thread):
                break
        return True

    @Slot()
    def action_show_large_img(self, path, thumb, auto_confirm):
        dialog = MyImageDialog(self, path, screen.availableGeometry().size(), thumb, auto_confirm, self.show_info)
        dialog.exec()
        dialog.deleteLater()

    @Slot()
    def action_open_url(self):
        url = self.txt_url.text()
        print(url)
        if url:
            webbrowser.open(url)

    def show_info(self):
        image_path = None
        url = ""
        last = ""
        if self.selected_path is not None:
            # image = imutils.url_to_image("https://pbs.twimg.com/media/E_24DrNVUAIPlFe.jpg:small")

            image_path = join_path(self.selected_path, "folder.jpg")
            # img = MyImageSource(image_path, self.image_frame.size)
            self.selected_data = InfoImage.load_info(self.selected_path)
            if self.selected_data is not None:
                url = self.selected_data['url']
                last = self.selected_data['lastUpdate']
        self.show_info_imp(image_path, url, last)

    def show_info_imp(self, image_path, url, last):
        self.image_frame.set_path_async(image_path)
        self.txt_url.setText(url)
        self.txt_date.setText(last)

    @Slot()
    def action_download_new_img(self):
        if self.selected_path is not None:
            self.selected_data['url'] = self.txt_url.text()
            update_thread = MyThread("update_thread")
            update_thread.set_run(parse_url_get_images,
                                  self.txt_url.text(),
                                  str_to_date(self.txt_date.text()),
                                  self.selected_path,
                                  self.thumb_size,
                                  image_out=self.new_image_signal,
                                  retry=self.download_retry)
            update_thread.on_finish(on_finish=self.action_download_new_img_done,
                                    on_result=self.action_download_new_img_result,
                                    on_before=self.action_download_new_img_start)

            update_thread.start()

    def action_download_new_img_start(self):
        self.but_update.setEnabled(False)
        self.image_new_flow.clearAll()

    def action_download_new_img_result(self, result):
        path, latest_date = result
        print(latest_date)
        if path == self.selected_path:
            self.selected_data['lastUpdate'] = latest_date
            InfoImage.save_info(self.selected_path, self.selected_data)
            self.show_info()
        else:
            data = InfoImage.load_info(path)
            data['lastUpdate'] = latest_date
            InfoImage.save_info(path, data)

    def action_download_new_img_done(self):
        self.but_update.setEnabled(True)

    @QtCore.Slot()
    def safe_exit(self):
        settings.sync()
        """exit the application gently so Spyder IDE will not hang"""
        settings.setValue("bitgirl/splitterSizes", self.splitter_right.saveState())
        settings.setValue("main/width", self.width())
        settings.setValue("main/height", self.height())
        self.deleteLater()
        self.close()
        self.destroy()
        app.exit()


if __name__ == '__main__':
    print("Program Start")

    settings = MySetting("soft.jp", "Manager")

    if not settings.contains("bitgirl/url1"):
        settings.setValue("bitgirl/url1", "https://bi-girl.net/")
    if not settings.contains("bitgirl/url2"):
        settings.setValue("bitgirl/url2", "https://cosppi.net/user/")
    if not settings.contains("bitgirl/root"):
        settings.setValue("bitgirl/root", "X:/Image/Twitter")
    if not settings.contains("bitgirl/download_retry"):
        settings.setValue("bitgirl/download_retry", 10)

    print("Create App")

    app = QtCore.QCoreApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    user_theme = settings.value("main/theme", "dark_pink.xml")
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

    widget = MainWidget()
    widget.setWindowTitle(" ")
    # widget.setWindowIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
    widget.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
    widget.show()

    sys.exit(app.exec())
