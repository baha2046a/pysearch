#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import List

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from qt_material import apply_stylesheet

from MyCommon import list_jpg, str_to_date, list_dir
from myparser import parse_url_get_images
from myparser.CreateRecordDialog import CreateRecordDialog
from myparser.FanzaMain import get_fanza_result, file_name_to_movie_id, get_all_fanza
from myparser.InfoMovie import InfoMovie, load_movie_db, save_movie_db, load_info, save_info
from myparser.MovieWidget import MovieWidget, RenameDialog
from myqt.MyDirModel import MyDirModel
from myqt.MyQtCommon import MyHBox, MyVBox, MyButton
from myqt.MyQtFlow import MyQtScrollableFlow
from myqt.MyQtImage import MyImageBox, MyImageSource, MyImageDialog
from myqt.MyQtSetting import MySetting, SettingDialog
from myqt.MyQtWorker import MyThread


class MainWidget(QtWidgets.QWidget):
    info_out = Signal(str)
    image_signal = Signal(str, QSize, MyImageSource)
    new_movie_signal = Signal(InfoMovie)
    progress_reset_signal = Signal(int)
    progress_signal = Signal(int)

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
        self.but_open_explorer = MyButton('Explorer', self.action_open_explorer)
        self.but_show_folder_images = MyButton('Show', self.action_show_folder_images)

        h_box_top_bar = MyHBox().addAll(self.but_settings,
                                        self.but_open_explorer,
                                        self.but_show_folder_images)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(1)

        self.image_frame = MyImageBox(QSize(300, 240))

        self.txt_move_path = QLineEdit("Folder")
        # self.txt_url.setReadOnly(True)
        self.but_up_path = MyButton("Up", self.action_up_path)
        self.but_refresh_path = MyButton("Refresh", self.action_refresh_path)
        self.but_move_to_download_folder = MyButton("Download", self.action_to_download_folder)
        self.but_move_to_movie_folder = MyButton("Movie", self.action_to_movie_folder)
        self.but_rename_path = MyButton("Rename", self.action_rename_path)

        h_box_url = MyHBox().addAll(self.but_move_to_download_folder,
                                    self.but_move_to_movie_folder,
                                    self.but_refresh_path,
                                    self.but_rename_path,
                                    self.but_up_path)

        self.txt_date = QLineEdit("Movie Control")
        self.but_scan_all = MyButton('Scan All', self.action_get_all_movie)
        self.but_recheck = MyButton("Scan", self.action_load_folder)
        self.but_update = MyButton("Rename", self.action_rename)
        self.but_mp4_to_folder = MyButton('+', self.action_mp4_to_folder)
        self.but_delete_info = MyButton('-', self.action_delete_info)

        h_box_date = MyHBox().addAll(self.txt_date,
                                     self.but_scan_all,
                                     self.but_recheck,
                                     self.but_update,
                                     self.but_delete_info,
                                     self.but_mp4_to_folder)

        self.view = QListView()
        self.model = MyDirModel(self)  # QFileSystemModel(self)  # QStringListModel()
        # self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot)
        # self.model.setReadOnly(True)

        self.view.setModel(self.model)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # self.view.setViewMode(QListView.IconMode)
        self.view.clicked.connect(self.action_list_click)
        self.view.doubleClicked.connect(self.action_list_double_click)

        self.but_exit = MyButton('Exit', self.safe_exit)

        h_box_bottom_bar = MyHBox().addAll(self.but_exit)

        v_box_left = MyVBox().addAll(h_box_top_bar,
                                     self.progress_bar,
                                     self.image_frame,
                                     h_box_url,
                                     h_box_date,
                                     self.view,
                                     h_box_bottom_bar)

        self.left_panel_widget = QWidget(self)
        self.left_panel_widget.setLayout(v_box_left)
        self.left_panel_widget.setFixedWidth(500)

        self.txt_info = [QLabel(self), QLabel(self), QLabel(self)]
        for txt in self.txt_info:
            txt.setMaximumWidth(1200)

        self.selected_path: str = ""

        self.image_flow = MyQtScrollableFlow()
        self.image_new_flow = MyQtScrollableFlow()
        # h_sep = HorizontalLine()
        # self.vbox_right.addWidget(h_sep)

        self.splitter_right = QSplitter(self)
        self.splitter_right.setOrientation(Qt.Vertical)
        self.splitter_right.addWidget(self.image_flow)
        self.splitter_right.addWidget(self.image_new_flow)

        if settings.contains("movie/splitterSizes"):
            self.splitter_right.restoreState(settings.value("movie/splitterSizes"))

        self.right_panel = MyVBox().addAll(self.splitter_right, *self.txt_info)

        layout = MyHBox().addAll(self.left_panel_widget, self.right_panel)

        self.setLayout(layout)

        self.thumb_size = QSize(140, 200)
        self.selected_data: InfoMovie = None
        self.update_delay = 0.001
        self.apply_settings()

        self.progress_signal.connect(self.progress_bar.setValue)
        self.progress_reset_signal.connect(self.progress_bar.setMaximum)
        self.info_out.connect(self.action_info_out)
        self.image_signal.connect(self.action_show_img, Qt.QueuedConnection)
        self.new_movie_signal.connect(self.action_save_movie, Qt.QueuedConnection)
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

        # self.set_dir(settings.value("bitgirl/root"))

        load_movie_db(settings.valueStr("movie/base"))

        self.selected_path = settings.valueStr("movie/last_selection", None)

        print(self.selected_path)
        self.model.setRootPath(settings.value("movie/root"))

        self.model.makeSelect(self.selected_path, self.view)
        self.show_info()
        # self.root_idx = self.model.setRootPath(settings.value("bitgirl/root"))
        # self.view.setRootIndex(self.root_idx)

    @Slot()
    def action_list_click(self, index):
        self.selected_path = os.path.join(self.model.rootPath, index.data())
        print(self.selected_path)
        settings.setValue("movie/last_selection", self.selected_path)
        self.show_info()

    @Slot()
    def action_list_double_click(self, index):
        enter_path = os.path.join(self.model.rootPath, index.data()).replace("\\", "/")
        print(enter_path)
        if os.path.isdir(enter_path):
            self.selected_path = None
            self.model.setRootPath(enter_path)
            settings.setValue("movie/root", enter_path)
        else:
            if enter_path.split(".")[-1].lower() in MyImageDialog.FORMAT:
                dialog = MyImageDialog(self, enter_path, screen.availableGeometry().size())
                dialog.exec()
            else:
                os.startfile(enter_path)

    @Slot()
    def action_up_path(self):
        out_path = os.path.dirname(self.model.rootPath)
        self.selected_path = None
        self.model.setRootPath(out_path)
        settings.setValue("movie/root", out_path)

    @Slot()
    def action_settings(self):
        dialog = SettingDialog(self, settings, "movie")
        if dialog.exec():
            self.apply_settings()

    @Slot()
    def action_info_out(self, mess):
        for i in range(0, len(self.txt_info) - 1):
            self.txt_info[i].setText(self.txt_info[i + 1].text())
        self.txt_info[-1].setText(mess)

    @Slot()
    def action_show_img(self, name, as_size, img: MyImageSource) -> None:
        self.image_flow.show_img(as_size, img, self.action_show_large_img)

    @Slot()
    def action_show_new_img(self, name, as_size, img: MyImageSource) -> None:
        self.image_new_flow.show_img(as_size, img, self.action_show_large_img)

    @Slot()
    def action_rename(self):
        if self.selected_path is not None and os.path.isdir(self.selected_path):
            if self.selected_data and self.selected_data.path == self.selected_path:
                self.image_flow.clearAll()

                self.selected_data.rename()

                self.model.setRootPath(self.model.rootPath)
                self.selected_path = self.selected_data.path
                self.model.makeSelect(self.selected_path, self.view)
                self.show_info()

    @Slot()
    def action_refresh_path(self):
        self.selected_path = None
        self.model.setRootPath(self.model.rootPath)

    @Slot()
    def action_delete_info(self):
        if self.selected_data:
            self.image_flow.clearAll()
            self.selected_data.delete()

    @Slot()
    def action_rename_path(self):
        if self.selected_path is not None:
            dial = RenameDialog(self, self.selected_path)
            if dial.exec():
                out = dial.t_n.text()
                out_path = os.path.join(self.model.rootPath, out).replace("\\", "/")
                if not os.path.exists(out_path):
                    shutil.move(self.selected_path, out_path)
                    time.sleep(0.1)
                    self.model.setRootPath(self.model.rootPath)

                    self.selected_path = out_path
                    self.model.makeSelect(out, self.view)
                    self.show_info()
                else:
                    self.info_out.emit(out_path + " Already Exists")
        self.model.setRootPath(self.model.rootPath)

    @Slot()
    def action_to_download_folder(self):
        self.selected_path = None
        self.model.setRootPath(settings.valueStr("movie/download"))

    @Slot()
    def action_to_movie_folder(self):
        self.selected_path = None
        self.model.setRootPath(settings.valueStr("movie/base"))

    @Slot()
    def action_open_explorer(self):
        if self.selected_path is not None:
            print(self.selected_path)
            subprocess.Popen('explorer {}'.format(self.selected_path.replace('/', '\\')))

    @Slot()
    def action_recheck(self):
        if self.selected_path is not None:
            folder = self.selected_path.split("/")[-1]
            dialog = CreateRecordDialog(self, settings, folder, self.txt_move_path.text())

            if dialog.exec():
                url = dialog.txt_url.text()
                if url:
                    self.txt_move_path.setText(url)
                    self.selected_data['url'] = url

    @Slot()
    def action_mp4_to_folder(self):
        if os.path.isfile(self.selected_path) and self.selected_path.endswith(".mp4"):
            base = self.model.rootPath
            folder_name = Path(self.selected_path).stem

            m = re.compile(r"\[([0-9A-Z]+?)-?(\d+)]").match(folder_name)
            if m:
                folder_name = f"[{m.groups()[0]}-{int(m.groups()[1]):03d}]"
                new_file_name = os.path.join(base, folder_name + ".mp4").replace("\\", "/")

                shutil.move(self.selected_path, new_file_name)
                self.selected_path = new_file_name

            new_folder = os.path.join(base, folder_name)
            self.move_file_to_folder(self.selected_path, new_folder)

    def move_file_to_folder(self, file, folder):
        if not os.path.exists(folder):
            os.makedirs(folder)
            shutil.move(file, folder)
            self.model.setRootPath(self.model.rootPath)

            self.selected_path = folder
            self.model.makeSelect(folder, self.view)
            self.show_info()
        else:
            self.move_file_to_folder(file, folder + " 1")

    @Slot()
    def action_show_folder_images(self):
        if self.selected_path is not None:
            run_thread = MyThread("image_flow")
            run_thread.set_run(self.async_load_folder_images,
                               self.selected_path,
                               self.thumb_size)
            run_thread.on_finish(on_before=self.action_show_folder_images_start)
            run_thread.start()

            print(sys.getrefcount(run_thread))

    def action_show_folder_images_start(self):
        self.image_flow.clearAll()
        self.image_flow.group_by_date = True

    def async_load_folder_images(self, folder, as_size, thread):
        files = list_jpg(folder)
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
            time.sleep(self.update_delay)
        return True

    @Slot()
    def action_show_large_img(self, path, thumb, auto_confirm):
        dialog = MyImageDialog(self, path, screen.availableGeometry().size(), thumb, auto_confirm)
        dialog.exec()

    @Slot()
    def action_open_url(self):
        url = self.txt_move_path.text()
        print(url)
        if url:
            webbrowser.open(url)

    def show_info(self):
        if self.selected_path is not None:
            # image = imutils.url_to_image("https://pbs.twimg.com/media/E_24DrNVUAIPlFe.jpg:small")
            if os.path.isdir(self.selected_path) or self.selected_path.lower().endswith(".mp4"):
                movie = load_info(self.selected_path)
                if movie is not None and InfoMovie.LATEST == movie.version:
                    self.local_movie_data(movie)
                else:
                    self.action_load_folder()

    @Slot()
    def action_load_folder(self):
        mid = file_name_to_movie_id(self.selected_path)
        if mid:
            self.image_flow.clearAll()
            self.get_movie_data(mid)

    @Slot()
    def action_get_all_movie(self):
        print(self.model.rootPath)
        paths = list_dir(self.model.rootPath, "*/")
        paths = list(map(lambda n: n.replace("\\", "/")[:-1], paths))

        force = False
        if settings.valueInt("movie/force_scan") == 1:
            force = True

        thread = MyThread("get_movie_data")
        thread.set_run(get_all_fanza, paths, self.info_out, self.new_movie_signal,
                       self.progress_reset_signal, self.progress_signal, force=force)
        thread.on_finish(on_finish=self.action_get_all_movie_finish)
        thread.start()

    def action_get_all_movie_finish(self):
        self.info_out.emit("Update Finish")

    @Slot()
    def action_save_movie(self, movie: InfoMovie):
        if movie.path == self.selected_path:
            print(threading.currentThread(), movie.movie_id)
            w = MovieWidget(movie, local=False)
            w.on_save.connect(self.local_movie_data)
            self.image_flow.addWidget(w)

    def get_movie_data(self, mid: str):
        # print(get_fanza_result(mid))
        self.image_flow.clearAll()
        self.search_id = mid
        print(mid)

        thread = MyThread("get_movie_data")
        thread.set_run(get_fanza_result, self.selected_path, mid, self.new_movie_signal)
        thread.on_finish(on_result=self.get_movie_data_result)
        thread.start()

    def get_movie_data_result(self, movie: List[InfoMovie]):
        if len(movie) and movie[0].path == self.selected_path:
            if settings.value("movie/search_mode") == "same":
                hits = []
                for m in movie:
                    print(m.movie_id, self.search_id)
                    if m.movie_id == self.search_id:
                        hits.append(m)
                if hits:
                    for m in hits:
                        w = MovieWidget(m)
                        w.on_save.connect(self.local_movie_data)
                        self.image_flow.addWidget(w)
                else:
                    for m in movie:
                        w = MovieWidget(m)
                        w.on_save.connect(self.local_movie_data)
                        self.image_flow.addWidget(w)
            else:
                for m in movie:
                    w = MovieWidget(m)
                    w.on_save.connect(self.local_movie_data)
                    self.image_flow.addWidget(w)

    def local_movie_data(self, movie: InfoMovie):
        self.image_flow.clearAll()
        self.selected_data = movie
        self.image_flow.addWidget(MovieWidget(movie, local=True))

    @Slot()
    def action_download_new_img(self):
        if self.selected_path is not None:
            self.selected_data['url'] = self.txt_move_path.text()
            update_thread = MyThread("update_thread")
            update_thread.set_run(parse_url_get_images,
                                  self.txt_move_path.text(),
                                  str_to_date(self.txt_date.text()),
                                  self.selected_path,
                                  self.thumb_size,
                                  txt_out=self.info_out,
                                  image_out=self.new_image_signal)
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
            save_info(self.selected_path, self.selected_data)
            self.show_info()
        else:
            data = load_info(path)
            data['lastUpdate'] = latest_date
            save_info(path, data)

    def action_download_new_img_done(self):
        self.but_update.setEnabled(True)

    @QtCore.Slot()
    def safe_exit(self):
        save_movie_db()
        settings.sync()
        settings.setValue("movie/splitterSizes", self.splitter_right.saveState())
        settings.setValue("main/width", self.width())
        settings.setValue("main/height", self.height())
        self.deleteLater()
        self.close()
        self.destroy()
        app.exit()


if __name__ == '__main__':
    print("Program Start")

    settings = MySetting("soft.jp", "Manager")

    if not settings.contains("movie/search_mode"):
        settings.setValue("movie/search_mode", "same")
    if not settings.contains("movie/root"):
        settings.setValue("movie/root", "X:/Movies/AV/(Glory Quest)")
    if not settings.contains("movie/base"):
        settings.setValue("movie/base", "X:/Movies/AV")
    if not settings.contains("movie/download"):
        settings.setValue("movie/download", "C:/Users/baha2/Downloads")
    if not settings.contains("movie/force_scan"):
        settings.setValue("movie/force_scan", "0")

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
