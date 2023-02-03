#!/usr/bin/env python3
import asyncio
import os
import re
import shutil
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional

import qasync
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import QProgressBar, QLineEdit, QComboBox, QAbstractItemView, QWidget, QLabel, QSplitter
from qt_material import apply_stylesheet

from MyCommon import list_jpg, list_dir, join_path, every
from TextOut import TextOut
from myparser.InfoMovie import InfoMovie, load_info
from myparser.MovieCache import load_movie_db, save_movie_db, MovieCache
from myparser.MovieMoveWidget import MovieMoveWidget
from myparser.MovieSeries import PathSeriesWidget, SearchMovieWidget
from myparser.MovieWidget import MovieWidget, MovieLiteWidget, ActorWidget, KeywordWidget
from myparser.movie.fanza import file_name_to_movie_id, get_all_fanza
from myparser.movie.paser import MovieParser
from myqt.CommonDialog import InputDialog
from myqt.EditDict import EditDictDialog
from myqt.MultiList import ActorListDialog
from myqt.MyDirModel import MyDirModel
from myqt.MyQtCommon import QtHBox, QtVBox, MyButton, fa_icon
from myqt.MyQtFlow import MyQtScrollableFlow
from myqt.MyQtSetting import MySetting, SettingDialog
from myqt.MyQtWorker import MyThread, MyThreadPool
from myqt.QtImage import MyImageBox, MyImageSource, MyImageDialog
from myqt.QtVideo import MyVideoDialog, QtVideoDialog


class MainWidget(QtWidgets.QWidget):
    info_out = Signal(str)
    info_out_n = Signal(str)
    image_signal = Signal(str, QSize, MyImageSource, bool)

    progress_reset_signal = Signal(int)
    progress_signal = Signal(int)
    update_thread_count_signal = Signal(str)

    search_result_signal = Signal(list)

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

        self.but_exit = MyButton(fa_icon('mdi.exit-run'), self.safe_exit)
        self.but_settings = MyButton(fa_icon('ri.settings-3-line'), self.action_settings)
        self.but_move_movie = MyButton('Move', self.action_move_movie)
        self.but_list_series = MyButton('Series', self.action_list_series)
        self.but_list_actor = MyButton(fa_icon('fa5s.female'), self.action_list_actor)
        self.but_search_movie = MyButton(fa_icon('fa5s.compress-arrows-alt'), self.action_search_movie)
        self.but_show_images_local = MyButton(fa_icon('fa5.images'), self.action_show_images_local)

        h_box_top_bar = QtHBox().addAll(self.but_exit, self.but_settings,
                                        self.but_move_movie, self.but_list_series, self.but_list_actor,
                                        self.but_search_movie, self.but_show_images_local)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(1)

        self.txt_thread = QLabel(self)
        self.txt_thread.setText("0")
        self.txt_thread.setMaximumWidth(30)

        self.image_frame = MyImageBox(self, QSize(300, 240))

        self.txt_move_path = QLineEdit("Folder")
        # self.txt_url.setReadOnly(True)

        shortcut = {"Download": settings.valueStr("movie/download"),
                    "Movie": settings.valueStr("movie/base"),
                    "D": "D:/",
                    "Ready": "X:/ready"}

        self.filter_mid = QComboBox(self)
        self.filter_mid.setFixedWidth(100)
        self.filter_mid.currentIndexChanged.connect(self.filter_change)
        self.but_scan_all = MyButton('Scan All', self.action_get_all_movie)
        self.but_recheck = MyButton("Scan", self.action_custom_search)
        self.but_update = MyButton("Rename", self.action_rename)
        self.but_mp4_to_folder = MyButton('+', self.action_mp4_to_folder)
        self.but_delete_info = MyButton('-', self.action_delete_info)

        h_box_date = QtHBox().addAll(self.filter_mid,
                                     self.but_scan_all,
                                     self.but_recheck,
                                     self.but_update,
                                     self.but_delete_info,
                                     self.but_mp4_to_folder)

        self.model = MyDirModel(shortcut=shortcut)  # QFileSystemModel(self)  # QStringListModel()
        # self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot)
        # self.model.setReadOnly(True)

        self.model.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # self.view.setViewMode(QListView.IconMode)
        self.model.signal_clicked.connect(self.action_list_click, Qt.QueuedConnection)
        self.model.signal_double_clicked.connect(self.action_list_double_click, Qt.QueuedConnection)
        self.model.signal_root_changed.connect(self.model_root_changed, Qt.QueuedConnection)

        v_box_left = QtVBox().addAll(h_box_top_bar,
                                     h_box_date,
                                     QtHBox().addAll(self.progress_bar, self.txt_thread),
                                     self.image_frame,
                                     self.model.shortcut_bar,
                                     self.model.tool_bar,
                                     self.model.view)

        self.left_panel_widget = QWidget(self)
        self.left_panel_widget.setLayout(v_box_left)
        self.left_panel_widget.setFixedWidth(500)

        self.txt_info = [QLabel(self), QLabel(self), QLabel(self)]
        for txt in self.txt_info:
            txt.setMaximumWidth(1200)

        # self.selected_path: str = ""
        self.movie_base = ""

        self.image_flow = MyQtScrollableFlow()
        self.image_new_flow = MyQtScrollableFlow()
        # h_sep = HorizontalLine()
        # self.vbox_right.addWidget(h_sep)

        self.splitter_right = QSplitter(Qt.Vertical, self)
        # self.splitter_right.setOrientation(Qt.Vertical)
        self.splitter_right.addWidget(self.image_flow)
        self.splitter_right.addWidget(self.image_new_flow)

        if settings.contains("movie/splitterSizes"):
            self.splitter_right.restoreState(settings.value("movie/splitterSizes"))

        self.right_panel = QtVBox().addAll(self.splitter_right, *self.txt_info)

        layout = QtHBox().addAll(self.left_panel_widget, self.right_panel)

        self.setLayout(layout)

        self.thumb_size = QSize(140, 200)
        self.selected_data: Optional[InfoMovie] = None
        self.update_delay = 0.001
        self.apply_settings()

        self.progress_signal.connect(self.progress_bar.setValue)
        self.progress_reset_signal.connect(self.progress_bar.setMaximum)
        self.update_thread_count_signal.connect(self.txt_thread.setText, Qt.QueuedConnection)

        self.info_out.connect(self.action_info_out, Qt.QueuedConnection)
        self.info_out_n.connect(self.action_info_out_no_newline, Qt.QueuedConnection)
        self.image_signal.connect(self.action_show_img, Qt.QueuedConnection)

        self.search_result_signal.connect(self.movie_result_single, Qt.QueuedConnection)
        # self.model.directoryLoaded.connect(self.model_loaded)

        TextOut.out = self.info_out.emit
        TextOut.progress_max = self.progress_reset_signal.emit
        TextOut.progress = self.progress_signal.emit

        threading.Thread(target=lambda: every(1, self.count_thread), daemon=True).start()

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
        if not os.path.exists(self.movie_base):
            self.movie_base = "D:/AV"

        load_movie_db("D:/AV")  # self.movie_base)

        # self.selected_path = settings.valueStr("movie/last_selection", None)

        self.model.setRootPath(settings.value("movie/root"))
        self.model.makeSelect(settings.valueStr("movie/last_selection", None))

        # self.root_idx = self.model.setRootPath(settings.value("bitgirl/root"))
        # self.view.setRootIndex(self.root_idx)

    def count_thread(self):
        self.update_thread_count_signal.emit(str(MyThread.size() + MyThreadPool.size()))

    @Slot()
    def action_search_movie(self):
        dial = InputDialog()
        if dial.exec():
            mid = dial.get_result()
            if mid:
                if len(mid) > 4:
                    m = MovieCache.get(mid)
                    if m and m.path:
                        self.model.makeSelect(m.path, False)
                else:
                    m = MovieCache.startswith(mid)
                    r_dial = EditDictDialog(m, sort=True)
                    r_dial.show()

    @Slot()
    def filter_change(self, idx) -> None:
        if idx > 0:
            f = self.filter_mid.itemText(idx)
            print(f)
            self.model.set_filter(f)
        else:
            self.model.clear_filter()

    @qasync.asyncSlot()
    async def action_list_click(self, path, _1, _2) -> None:
        settings.setValue("movie/last_selection", path)
        await self.show_info(path)

    @Slot()
    def model_root_changed(self, new_root):
        self.filter_mid.clear()
        self.filter_mid.insertItem(0, "None")
        settings.setValue("movie/root", new_root)

    @Slot()
    def action_list_double_click(self, path, _1, _2) -> None:
        if os.path.isfile(path):
            ext = os.path.splitext(path)[1].lower()

            if ext in MyImageDialog.FORMAT:
                dialog = MyImageDialog(self, path, screen.availableGeometry().size())
                dialog.exec()
            elif ext in QtVideoDialog.FORMAT_VIDEO:
                if QtVideoDialog.available:
                    dialog = MyVideoDialog(self, [path])
                    dialog.show()
            elif ext in QtVideoDialog.FORMAT_AUDIO:
                if QtVideoDialog.available:
                    dialog = MyVideoDialog(self, [path], audio_only=True)
                    dialog.show()
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
        print(mess)

    @Slot()
    def action_info_out_no_newline(self, mess):
        self.txt_info[-1].setText(mess)

    @Slot()
    def action_show_img(self, path: str, as_size, img: MyImageSource, check_path: bool = False) -> None:
        if check_path:
            if not path.startswith(self.model.select):
                return
        self.image_flow.show_img(as_size, img, self.action_show_large_img)
        QCoreApplication.processEvents()

    @Slot()
    def action_show_new_img(self, _, as_size, img: MyImageSource) -> None:
        self.image_new_flow.show_img(as_size, img, self.action_show_large_img)
        QCoreApplication.processEvents()

    @Slot()
    def action_rename(self):
        if self.model.select is not None and os.path.isdir(self.model.select):
            if self.selected_data and self.selected_data.path == self.model.select:
                self.image_flow.clearAll()
                self.but_update.setEnabled(False)
                selected = self.selected_data
                self.model.makeSelect(None)
                thread = MyThread()
                thread.set_run(selected.rename)
                thread.on_finish(on_result=self.action_rename_end)
                thread.start()

    def action_rename_end(self, path):
        self.but_update.setEnabled(True)
        self.model.makeSelect(path, reload=True)

    @Slot()
    def action_delete_info(self):
        if self.selected_data:
            self.image_flow.clearAll()
            self.selected_data.delete()

    @Slot()
    def action_mp4_to_folder(self):
        path = self.model.select
        if os.path.isfile(path) and (path.endswith(".mp4") or path.endswith(".avi")):
            base = self.model.rootPath
            folder_name = Path(path).stem

            file_list = [path]
            extra_index = 1
            head, tail = os.path.splitext(path)
            while os.path.exists(f"{head} ({extra_index}){tail}"):
                file_list.append(f"{head} ({extra_index}){tail}")
                extra_index += 1

            m = re.compile(r"\[([0-9A-Z]+?)-?(\d+)]").match(folder_name)
            if m:
                folder_name = f"[{m.groups()[0]}-{int(m.groups()[1]):03d}]"
            else:
                words = folder_name.split(" ")
                for word in words:
                    m = re.compile(r"([0-9A-Z]+?)-?(\d+)").match(word)
                    if m:
                        folder_name = f"[{m.groups()[0]}-{int(m.groups()[1]):03d}]"
                        break

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
        if self.selected_data is not None and self.model.select == self.selected_data.path:
            w = MovieMoveWidget(self, self.selected_data, self.movie_base)
            self.image_flow.addWidget(w, front=True)
            w.on_move.connect(self.action_move_movie_finish, Qt.QueuedConnection)

    @Slot()
    def action_custom_search(self):
        if self.model.select:
            w = SearchMovieWidget(self, self.model.select)
            self.output_2(w, True)
            w.output.connect(self.search_result_signal)

    def action_show_actor_widget(self, actor):
        w = ActorWidget(actor)
        self.output_2(w, True)
        w.output.connect(self.show_info, Qt.QueuedConnection)
        w.lite_movie.connect(self.show_lite_from_list)

    def action_show_keyword_widget(self, keyword):
        w = KeywordWidget(keyword)
        self.output_2(w, True)
        w.lite_movie.connect(self.show_lite_from_list)

    @Slot()
    def action_list_series(self):
        w = PathSeriesWidget(self, self.model.rootPath)
        for item in w.model.stringList():
            if self.filter_mid.findText(item) < 0:
                self.filter_mid.insertItem(self.filter_mid.count(), item)
        self.output_2(w, True)
        w.output.connect(self.action_display_movie_lite)

    @Slot()
    def action_list_actor(self):
        dial = ActorListDialog.get(self)
        if dial:
            dial.show()
            dial.detail.output.connect(self.show_info, Qt.QueuedConnection)
            dial.detail.lite_movie.connect(self.show_lite_from_list)

    def action_display_movie_lite(self, w: dict, cover, path):
        lite_widget = MovieLiteWidget(self, w, cover, path)
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
            # self.show_info(os.path.join(self.model.rootPath, path))
            self.model.makeSelect(path, False)
        else:
            self.action_load_folder(mid)

    @Slot()
    def action_show_images_local(self):
        if self.model.select and os.path.isdir(self.model.select):
            folder = self.model.select
            run_thread = MyThread("image_flow")
            frames_folder = QtVideoDialog.has_preview(folder)
            if frames_folder:
                folder = frames_folder
            else:
                run_thread.on_finish(on_before=self.action_show_images_start)
            run_thread.set_run(self.async_load_images_local, folder, self.thumb_size)
            run_thread.start()

    def action_show_images_start(self):
        self.image_flow.clearAll()
        self.image_flow.group_by_date = False

    @Slot(str, result=None)
    def action_move_movie_finish(self, path: str) -> None:
        self.model.makeSelect(path, reload=True)

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

    def async_load_images_local(self, folder, as_size, thread):
        files = list_jpg(folder, no_folder_img=True)
        self.progress_reset_signal.emit(len(files))

        progress = 0

        for f in files:
            progress += 1
            self.progress_signal.emit(progress)
            file = f.replace("\\", "/")
            img = MyImageSource(file, as_size)
            self.image_signal.emit(file, as_size, img, False)
            if QThread.isInterruptionRequested(thread):
                break
            time.sleep(0.01)
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

    @qasync.asyncSlot()
    async def show_info(self, selected_path):
        if selected_path is not None:
            # image = imutils.url_to_image("https://pbs.twimg.com/media/E_24DrNVUAIPlFe.jpg:small")
            if os.path.isdir(selected_path) or selected_path.lower().endswith(".mp4"):
                movie = await load_info(selected_path)
                if movie is not None and InfoMovie.LATEST == movie.version:
                    MovieCache.put(movie)
                    self.local_movie_data(movie, selected_path)
                    front_mid = movie.movie_id.split("-", 1)[0]
                    if self.filter_mid.findText(front_mid) < 0:
                        self.filter_mid.insertItem(self.filter_mid.count(), front_mid)
                else:
                    self.action_load_folder()

    @Slot()
    def action_load_folder(self, mid=None, path=None):
        if not mid and self.model.select:
            mid = file_name_to_movie_id(self.model.select)
            path = self.model.select
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
        # await get_all_fanza(paths, self.progress_reset_signal, self.progress_signal, force=force)
        thread = MyThread("get_all_movie_data")
        thread.set_run(get_all_fanza, paths, self.progress_reset_signal, self.progress_signal, force=force)
        thread.on_finish(on_finish=lambda: TextOut.out("Update Finish"))
        thread.start()

    def get_movie_data(self, path: str, mid: str):
        self.output_1(None, clear=True)
        MovieParser.parse(path, mid, self.search_result_signal, single_mode=True,
                          signal_out_start=TextOut.progress_start, signal_out_end=TextOut.progress_end)

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

    def movie_result_multi(self, movies: list) -> None:  # List[MovieWidget]):
        for m in movies:
            self.movie_result_single(m)

    def movie_result_single(self, movie: list) -> None:
        if len(movie) < 3:
            self.output_1(None, clear=True)
        else:
            w = MovieWidget(self, movie[0], loaded_f=movie[1], loaded_b=movie[2])
            w.on_save.connect(self.local_movie_data)
            self.output_1(w)
        QCoreApplication.processEvents()

    def local_movie_data(self, movie: InfoMovie, selected_path=None):
        if selected_path is None:
            selected_path = self.model.select
        movie.set_local_path(selected_path)
        # movie.path.replace("\\", "/")
        self.selected_data = movie
        w = MovieWidget(self, movie, local=True)
        self.output_1(w, clear=True)
        w.on_actor.connect(self.action_show_actor_widget)
        w.on_keyword.connect(self.action_show_keyword_widget)

    @qasync.asyncSlot()
    async def safe_exit(self):
        await save_movie_db()
        settings.setValue("movie/last_selection", self.model.select)
        settings.setValue("movie/splitterSizes", self.splitter_right.saveState())
        settings.setValue("main/width", self.width())
        settings.setValue("main/height", self.height())
        settings.sync()
        self.deleteLater()
        self.close()
        self.destroy()
        app.exit()


def main():
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    widget.show()
    sys.exit(app.exec())


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

    user_theme = settings.value("main/theme", "dark_teal.xml")
    apply_stylesheet(app, theme="dark_lightgreen.xml")

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

    main()
