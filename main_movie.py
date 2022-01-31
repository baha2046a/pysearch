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
from typing import AnyStr

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from qt_material import apply_stylesheet

from MyCommon import list_jpg, str_to_date, list_dir, join_path
from TextOut import TextOut
from myparser import parse_url_get_images
from myparser.CreateRecordDialog import CreateRecordDialog
from myparser.FanzaMain import get_fanza_result, file_name_to_movie_id, get_all_fanza
from myparser.InfoMovie import InfoMovie, load_info, save_info
from myparser.MovieCache import load_movie_db, save_movie_db, MovieCache
from myparser.MovieMoveWidget import MovieMoveWidget
from myparser.MovieSeries import PathSeriesWidget, SearchMovieWidget
from myparser.MovieWidget import MovieWidget, MovieLiteWidget, ActorWidget, KeywordWidget
from myqt.CommonDialog import RenameDialog
from myqt.MyDirModel import MyDirModel
from myqt.MyQtCommon import MyHBox, MyVBox, MyButton
from myqt.MyQtFlow import MyQtScrollableFlow
from myqt.MyQtImage import MyImageBox, MyImageSource, MyImageDialog
from myqt.MyQtSetting import MySetting, SettingDialog
from myqt.MyQtWorker import MyThread


class MainWidget(QtWidgets.QWidget):
    info_out = Signal(str)
    info_out_n = Signal(str)
    image_signal = Signal(str, QSize, MyImageSource)
    new_movie_signal = Signal(InfoMovie)
    progress_reset_signal = Signal(int)
    progress_signal = Signal(int)
    display_movie = Signal(str, str)

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
        self.but_move_movie = MyButton('Move', self.action_move_movie)
        self.but_list_series = MyButton('Series', self.action_list_series)

        h_box_top_bar = MyHBox().addAll(self.but_settings,
                                        self.but_move_movie,
                                        self.but_list_series)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(1)

        self.image_frame = MyImageBox(QSize(300, 240))

        self.txt_move_path = QLineEdit("Folder")
        # self.txt_url.setReadOnly(True)
        self.but_refresh_path = MyButton("Refresh", self.action_refresh_path)
        self.but_move_to_download_folder = MyButton("Download", self.action_to_download_folder)
        self.but_move_to_movie_folder = MyButton("Movie", self.action_to_movie_folder)

        h_box_url = MyHBox().addAll(self.but_move_to_download_folder,
                                    self.but_move_to_movie_folder,
                                    self.but_refresh_path)

        self.txt_date = QLineEdit("Movie")
        self.but_scan_all = MyButton('Scan All', self.action_get_all_movie)
        self.but_recheck = MyButton("Scan", self.action_custom_search)
        self.but_update = MyButton("Rename", self.action_rename)
        self.but_mp4_to_folder = MyButton('+', self.action_mp4_to_folder)
        self.but_delete_info = MyButton('-', self.action_delete_info)

        h_box_date = MyHBox().addAll(self.txt_date,
                                     self.but_scan_all,
                                     self.but_recheck,
                                     self.but_update,
                                     self.but_delete_info,
                                     self.but_mp4_to_folder)

        self.model = MyDirModel()  # QFileSystemModel(self)  # QStringListModel()
        # self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot)
        # self.model.setReadOnly(True)

        self.model.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # self.view.setViewMode(QListView.IconMode)
        self.model.signal_clicked.connect(self.action_list_click)
        self.model.signal_double_clicked.connect(self.action_list_double_click)
        self.model.signal_root_changed.connect(self.model_root_changed)

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
        for txt in self.txt_info:
            txt.setMaximumWidth(1200)

        self.selected_path: str = ""
        self.movie_base = ""

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
        self.info_out_n.connect(self.action_info_out_no_newline)
        self.image_signal.connect(self.action_show_img, Qt.QueuedConnection)
        self.new_movie_signal.connect(self.action_save_movie, Qt.QueuedConnection)
        self.display_movie.connect(self.action_load_folder)
        # self.model.directoryLoaded.connect(self.model_loaded)

        TextOut.out = self.info_out.emit
        TextOut.progress_max = self.progress_reset_signal.emit
        TextOut.progress = self.progress_signal.emit

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
        self.movie_base = settings.valueStr("movie/base")
        load_movie_db(self.movie_base)

        self.selected_path = settings.valueStr("movie/last_selection", None)

        print(self.selected_path)
        self.model.setRootPath(settings.value("movie/root"))
        self.model.makeSelect(self.selected_path)

        # self.root_idx = self.model.setRootPath(settings.value("bitgirl/root"))
        # self.view.setRootIndex(self.root_idx)

    @Slot()
    def action_list_click(self, path, _1, _2) -> None:
        if path != self.selected_path:
            self.selected_path = path
            print(self.selected_path)
            settings.setValue("movie/last_selection", self.selected_path)
            self.show_info(self.selected_path)

    @Slot()
    def model_root_changed(self, new_root):
        settings.setValue("movie/root", new_root)

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
        dialog = SettingDialog(self, settings, "movie")
        if dialog.exec():
            self.apply_settings()

    @Slot()
    def action_info_out(self, mess):
        for i in range(0, len(self.txt_info) - 1):
            self.txt_info[i].setText(self.txt_info[i + 1].text())
        self.txt_info[-1].setText(mess)

    @Slot()
    def action_info_out_no_newline(self, mess):
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
    def action_rename(self):
        if self.selected_path is not None and os.path.isdir(self.selected_path):
            if self.selected_data and self.selected_data.path == self.selected_path:
                self.image_flow.clearAll()

                prefer_path = self.selected_data.rename()

                self.model.makeSelect(prefer_path, reload=True)

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
    def action_to_download_folder(self):
        self.selected_path = None
        self.model.setRootPath(settings.valueStr("movie/download"))
        self.model.makeSelect(None)

    @Slot()
    def action_to_movie_folder(self):
        self.selected_path = None
        self.model.setRootPath(settings.valueStr("movie/base"))
        self.model.makeSelect(None)

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

            file_list = [self.selected_path]
            extra_index = 1
            head, tail = os.path.splitext(self.selected_path)
            while os.path.exists(f"{head} ({extra_index}){tail}"):
                file_list.append(f"{head} ({extra_index}){tail}")
                extra_index += 1

            m = re.compile(r"\[([0-9A-Z]+?)-?(\d+)]").match(folder_name)
            if m:
                folder_name = f"[{m.groups()[0]}-{int(m.groups()[1]):03d}]"

            new_folder = join_path(base, folder_name)
            if not os.path.exists(new_folder):
                os.makedirs(new_folder)

            for i, f in enumerate(file_list):
                if len(file_list) == 1:
                    new_file_path = join_path(new_folder, f"{folder_name}{tail}")
                else:
                    new_file_path = join_path(new_folder, f"{folder_name}-{(i + 1)}{tail}")
                if os.path.exists(new_file_path):
                    new_head, _ = os.path.splitext(new_file_path)
                    new_file_path = f"{new_head}-{time.time()}{tail}"
                shutil.move(f, new_file_path)

            self.model.makeSelect(new_folder, reload=True)

    @Slot()
    def action_move_movie(self):
        print(self.selected_path)
        if self.selected_data is not None and self.selected_path == self.selected_data.path:
            w = MovieMoveWidget(self.selected_data, self.movie_base)
            self.image_flow.addWidget(w, front=True)
            w.on_move.connect(self.action_move_movie_finish)

    @Slot()
    def action_custom_search(self):
        if self.selected_path:
            w = SearchMovieWidget(self.selected_path)
            self.output_2(w, True)
            w.output.connect(self.display_movie)

    def action_show_actor_widget(self, actor):
        w = ActorWidget(actor)
        self.output_2(w, True)
        w.output.connect(self.show_info)
        w.lite_movie.connect(self.show_lite_from_list)

    def action_show_keyword_widget(self, keyword):
        w = KeywordWidget(keyword)
        self.output_2(w, True)
        w.lite_movie.connect(self.show_lite_from_list)

    @Slot()
    def action_list_series(self):
        w = PathSeriesWidget(self.model.rootPath)
        self.output_2(w, True)
        w.output.connect(self.action_display_movie_lite)

    def action_display_movie_lite(self, w: dict, cover, path):
        lite_widget = MovieLiteWidget(w, cover, path)
        self.output_2(lite_widget)
        lite_widget.on_view.connect(self.show_detail_from_lite)

    @Slot()
    def show_lite_from_list(self, paths: list[list]):
        for p in paths:
            if os.path.exists(p[2]):
                self.action_display_movie_lite({"mid": p[0], "cover": p[1]}, None, p[2])
                QCoreApplication.processEvents()

    @Slot()
    def show_detail_from_lite(self, mid, path):
        if path:
            self.show_info(os.path.join(self.model.rootPath, path))
        else:
            self.action_load_folder(mid)

    @Slot(str, result=None)
    def action_move_movie_finish(self, path: str) -> None:
        self.model.makeSelect(path, reload=True)

    def action_show_folder_images_start(self):
        self.image_flow.clearAll()
        self.image_flow.group_by_date = True

    def output_1(self, out, clear=False):
        if clear:
            self.image_flow.clearAll()
        if out:
            self.image_flow.addWidget(out)

    def output_2(self, out, clear=False):
        if clear:
            self.image_new_flow.clearAll()
        if widget:
            self.image_new_flow.addWidget(out, front=True)

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
        dialog.deleteLater()

    @Slot()
    def action_open_url(self):
        url = self.txt_move_path.text()
        print(url)
        if url:
            webbrowser.open(url)

    @Slot()
    def show_info(self, selected_path):
        if selected_path is not None:
            # image = imutils.url_to_image("https://pbs.twimg.com/media/E_24DrNVUAIPlFe.jpg:small")
            if os.path.isdir(selected_path) or selected_path.lower().endswith(".mp4"):
                movie = load_info(selected_path)
                if movie is not None and InfoMovie.LATEST == movie.version:
                    MovieCache.put(movie)
                    self.local_movie_data(movie)
                else:
                    self.action_load_folder()

    @Slot()
    def action_load_folder(self, mid=None, path=None):
        if not mid:
            mid = file_name_to_movie_id(self.selected_path)
            path = self.selected_path
        if mid:
            self.get_movie_data(path, mid)

    @Slot()
    def action_get_all_movie(self):
        print(self.model.rootPath)
        paths = list_dir(self.model.rootPath, "*/")
        paths = list(map(lambda n: n.replace("\\", "/")[:-1], paths))

        force = False
        if settings.valueInt("movie/force_scan") == 1:
            force = True

        thread = MyThread("get_all_movie_data")
        thread.set_run(get_all_fanza, paths, self.progress_reset_signal, self.progress_signal, force=force)
        thread.on_finish(on_finish=lambda: TextOut.out("Update Finish"))
        thread.start()

    @Slot()
    def action_save_movie(self, movie: InfoMovie):
        if movie.path == self.selected_path:
            print(threading.currentThread(), movie.movie_id)
            w = MovieWidget(movie, local=False)
            w.on_save.connect(self.local_movie_data)
            self.image_flow.addWidget(w)

    def get_movie_data(self, path: str, mid: str):
        # print(get_fanza_result(mid))
        self.output_1(None, clear=True)
        self.search_id = mid

        thread = MyThread("get_movie_data")
        thread.set_run(get_fanza_result, path, mid)
        thread.on_finish(on_result=self.get_movie_data_result)
        thread.start()

    """
        def get_movie_data_result(self, movie: List[InfoMovie]):
            if len(movie):
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
                            self.output_1(w)
                    else:
                        for m in movie:
                            w = MovieWidget(m)
                            w.on_save.connect(self.local_movie_data)
                            self.output_1(w)
                else:
                    for m in movie:
                        w = MovieWidget(m)
                        w.on_save.connect(self.local_movie_data)
                        self.output_1(w)
    """

    def get_movie_data_result(self, movie: list):  # List[MovieWidget]):
        for m in movie:
            w = MovieWidget(m[0], loaded_f=m[1], loaded_b=m[2])
            w.on_save.connect(self.local_movie_data)
            self.output_1(w)
            QCoreApplication.processEvents()

    def local_movie_data(self, movie: InfoMovie):
        movie.set_local_path(self.selected_path)
        # movie.path.replace("\\", "/")
        self.selected_data = movie
        w = MovieWidget(movie, local=True)
        self.output_1(w, clear=True)
        w.on_actor.connect(self.action_show_actor_widget)
        w.on_keyword.connect(self.action_show_keyword_widget)

    @QtCore.Slot()
    def safe_exit(self):
        save_movie_db()
        settings.setValue("movie/last_selection", self.selected_path)
        settings.setValue("movie/splitterSizes", self.splitter_right.saveState())
        settings.setValue("main/width", self.width())
        settings.setValue("main/height", self.height())
        settings.sync()
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
