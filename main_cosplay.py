#!/usr/bin/env python3
import imghdr
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from typing import AnyStr

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from qt_material import apply_stylesheet

from MyCommon import list_jpg
from TextOut import TextOut
from myparser import search_dup
from myparser.CosplayMoveWidget import CosplayMoveWidget
from myparser.InfoImage import InfoImage
from myparser.MovieWidget import RenameHint
from myparser.XinmeituluWidget import XinmeituluWidget, XinmeituluListWidget
from myqt.CommonDialog import RenameDialog, DeleteConfirmDialog, RenameImageDialog
from myqt.MyDirModel import MyDirModel
from myqt.MyQtCommon import MyHBox, MyVBox, MyButton
from myqt.MyQtFlow import MyQtScrollableFlow
from myqt.MyQtImage import MyImageBox, MyImageSource, MyImageDialog
from myqt.MyQtSetting import MySetting, SettingDialog
from myqt.MyQtWorker import MyThread
from zhtools.langconv import Converter


class MainWidget(QtWidgets.QWidget):
    info_out = Signal(str)
    image_signal = Signal(str, QSize, MyImageSource)
    new_image_signal = Signal(str, QSize, MyImageSource)
    progress_reset_signal = Signal(int)
    progress_signal = Signal(int)
    page_display = Signal(int)
    refresh_and_select = Signal(str)

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
        self.but_find_dup = MyButton('Dup', self.action_find_dup)
        self.but_show_folder_images = MyButton('Show', self.action_show_images_local)
        self.but_move_folder = MyButton("Move", self.action_move_folder)
        self.but_parse = MyButton("+", self.action_parse_page)

        h_box_top_bar = MyHBox().addAll(self.but_settings,
                                        self.but_find_dup,
                                        self.but_move_folder,
                                        self.but_parse)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(1)

        self.image_frame = MyImageBox(QSize(300, 240))

        self.txt_folder = QLineEdit("")
        self.txt_url = QLineEdit("")
        # self.txt_url.setReadOnly(True)
        self.but_open_url = MyButton("Open", self.action_open_url)
        self.but_update = MyButton("Update", self.action_update)

        h_box_url = MyHBox().addAll(self.txt_url, self.but_open_url, self.but_update)

        self.txt_date = QLineEdit("")

        self.rename_dialog = None

        self.cos_root = settings.valueStr("cosplay/root")

        self.but_move_to_root = MyButton("Root", self.action_to_folder, [self.cos_root])
        self.but_move_to_down = MyButton("Download", self.action_to_folder, [settings.valueStr("cosplay/download")])
        self.but_rename_images = MyButton("Rename", self.action_rename_images)

        h_box_move_1 = MyHBox().addAll(self.but_move_to_root,
                                       self.but_move_to_down,
                                       self.but_rename_images,
                                       self.but_show_folder_images,
                                       )

        self.lang_convert_list = [
            ["デート・ア・ライブ", "約會大作戰", "DATE A LIVE"],
            ["アルトリア", "阿爾托莉雅", "Alter"],
            ["ネロ", "尼祿", None],
            ["玉藻前", "玉藻前", "Tamamo"],
            ["ワンピース", "ONE PIECE", "ONE PIECE"],
            ["マシュ", "瑪修", "Matthew"],
            ["スカサハ", "斯卡哈", None],
            ["水着", "泳裝", None],
            ["花嫁", "婚紗", None],
            ["ネコぱら", "NEKOPARA", "NEKOPARA"],
            ["ホロライブ", "hololive", "hololive"],
            ["ショコラ", "巧克力", None],
            ["バニラ", "香草", None],
            ["霞ヶ丘詩羽", "霞之丘詩羽", None],
            ["ヱヴァンゲリヲン", "新世紀福音戰士", "EVA"],
            ["鬼滅の刃", "鬼滅之刃", None],
            ["初音ミク", "初音未來", "Miku"],
            ["LOL ", "英雄聯盟 ", "LOL "],
            ["Ahri", "阿狸", "Ahri"],
            ["黒獣", "黑獸", None],
            ["グランブルーファンタジー", "碧藍幻想", "Granblue Fantasy"],
            ["バイオハザード", "BIOHAZARD", "BIOHAZARD"],
            ["コヤンスカヤ", "高揚斯卡娅", None],
            ["冴えない彼女の育てかた", "路人女主的養成方式", None],
            ["賭ケグルイ", "狂賭之淵", None],
            ["酒吞童子", "酒呑童子", None],
            ["アズールレーン", "碧藍航線", "Azur Lane"],
            ["Tifa", "蒂法", "Tifa"],
            ["プリンセスコネクト", "公主連結", None],
            ["小林さんちのメイド", "小林家的龍女僕", None],
            ["リゼロ", "從零開始的異世界生活", None],
            ["レム", "蕾姆", None],
            ["ZONE-00", "零之地帶", "ZONE-00"],
            ["ネトゲの嫁は女の子じゃないと思った", "線上遊戲的老婆不可能是女生", None],
            ["NieR", "尼爾 機械紀元", "NieR"],
            ["NANA", "大崎娜娜", "NANA"],
            ["涼宮ハルヒの憂鬱", "涼宮春日的憂鬱", None],
            ["俺の妹がこんなに可愛いわけがない", "我的妹妹哪有這麼可愛", None],

            # 黑獸 奧莉加
        ]

        hint = ["碧藍航線", "賭ケグルイ", "日常", "兔女郎",
                "明日方舟", "少女前線", "我的妹妹不可能這麼可愛", "五更琉璃",
                "黒獣", "崩壞3rd", "從零開始的異世界生活", "蕾姆",
                "美少女萬華鏡 篝之霧枝", "魔鏡Mirror", "泳裝", "婚紗",
                "聖誕", "內衣", "賽車", "ヱヴァンゲリヲン",
                "冴えない彼女の育てかた", "加藤惠", "英梨梨", "霞ヶ丘詩羽",
                "Fate", "酒吞童子", "アルトリア", "尼祿",
                "黑貞德", "斯卡哈", "伊斯塔凜", "玉藻前",
                "白貞德", "葛饰北斋", "源頼光", "艾蕾",
                "歪萌社", "靡烟旗袍", "南半球女僕", "黑暗王朝",
                "魅魔", "透明女僕", "萊莎的鍊金工房", "hololive",
                "デート・ア・ライブ", "時崎狂三", "エロマンガ先生", "FF7",
                "Granblue Fantasy", "魔太郎", "豔娘幻夢譚", "瓶兒",
                "アイドルマスター", "ONE PIECE", "Persona 5", "化物語 戦場ヶ原",
                "原神", "優菈", "菲謝爾", "刻晴",
                "青春ブタ野郎", "桜島麻衣", "ソードアート・オンライン", "瑪修",
                "VOCALOID", "初音未來", "東方Project", "NieR",
                "緣之空", "春日野穹", "監獄学園", "バイオハザード"]

        self.hint = RenameHint(hint)

        self.model = MyDirModel(hint=self.hint, lang_convert_list=self.lang_convert_list)
        # QFileSystemModel(self)  # QStringListModel()
        # self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot)
        # self.model.setReadOnly(False)

        # self.view.setViewMode(QListView.IconMode)
        self.model.signal_clicked.connect(self.action_list_click)
        self.model.signal_double_clicked.connect(self.action_list_double_click)
        self.model.signal_root_changed.connect(self.model_root_changed)
        self.model.view.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.but_exit = MyButton('Exit', self.safe_exit)

        h_box_bottom_bar = MyHBox().addAll(self.but_exit)

        v_box_left = MyVBox().addAll(h_box_top_bar,
                                     h_box_move_1,
                                     self.progress_bar,
                                     self.image_frame,
                                     self.txt_folder,
                                     h_box_url,
                                     self.model.tool_bar,
                                     self.model.view,
                                     h_box_bottom_bar)

        self.left_panel_widget = QWidget(self)
        self.left_panel_widget.setLayout(v_box_left)
        self.left_panel_widget.setFixedWidth(500)

        self.txt_info = [QLabel(self), QLabel(self), QLabel(self), QLabel(self), QLabel(self)]

        self.selected_path: str = ""

        self.image_flow = MyQtScrollableFlow()
        self.image_new_flow = MyQtScrollableFlow()

        self.xin_mei_tutu = XinmeituluWidget(self.create_folder)
        self.xin_mei_tutu.info_out.connect(self.info_out)
        self.xin_mei_tutu.download_start.connect(self.model.lock_folder)
        self.xin_mei_tutu.download_finish.connect(self.model.unlock_folder)

        # self.vbox_right.addWidget(h_sep)

        self.splitter_right = QSplitter(self)
        self.splitter_right.setOrientation(Qt.Vertical)
        self.splitter_right.addWidget(self.image_flow)
        self.splitter_right.addWidget(self.image_new_flow)

        if settings.contains("cosplay/splitterSizes"):
            self.splitter_right.restoreState(settings.value("cosplay/splitterSizes"))

        self.right_panel = MyVBox().addAll(self.splitter_right, self.xin_mei_tutu, *self.txt_info)

        layout = MyHBox().addAll(self.left_panel_widget, self.right_panel)

        self.setLayout(layout)

        self.thumb_size = QSize(140, 200)
        self.selected_data = None
        self.apply_settings()

        self.progress_signal.connect(self.progress_bar.setValue)
        self.progress_reset_signal.connect(self.progress_bar.setMaximum)
        self.info_out.connect(self.action_info_out, Qt.QueuedConnection)
        self.image_signal.connect(self.action_show_img, Qt.QueuedConnection)
        self.new_image_signal.connect(self.action_show_new_img, Qt.QueuedConnection)
        self.page_display.connect(self.action_show_page, Qt.QueuedConnection)

        self.refresh_and_select.connect(self.refresh_and_select_path, Qt.QueuedConnection)

        TextOut.func = self.info_out.emit
        # self.model.directoryLoaded.connect(self.model_loaded)

    def create_folder(self, folder, use_path: AnyStr = None):
        if use_path is None:
            out_path, out = RenameDialog.create_rename(self.model.rootPath, "", folder)
        else:
            out_path = use_path
        self.refresh_and_select.emit(out_path)
        return out_path

    @Slot()
    def refresh_and_select_path(self, out_path):
        if out_path != "" and out_path != self.selected_path:
            self.model.makeSelect(out_path, reload=True)

    @Slot()
    def action_rename_images(self):
        if self.selected_path:
            rename = RenameImageDialog(self.selected_path)
            rename.exec()

    def action_to_folder(self, path, goto=True):
        self.selected_path = None
        self.image_new_flow.clearAll()
        if goto:
            self.model.setRootPath(path)
        else:
            self.model.setRootPath(self.model.rootPath)

    def apply_settings(self):
        thumb_w = settings.valueInt("image/thumb/width", 140)
        thumb_y = settings.valueInt("image/thumb/height", 200)
        self.thumb_size = QSize(thumb_w, thumb_y)

        win_w = settings.valueInt("main/width", screen.availableGeometry().width() - 50)
        win_h = settings.valueInt("main/height", screen.availableGeometry().height() - 50)
        print(win_w, win_h)
        n_size = QSize(win_w, win_h).boundedTo(screen.availableGeometry().size())
        self.resize(n_size)

        self.xin_mei_tutu.retry = settings.valueFloat("cosplay/download_retry")

        self.model.setRootPath(settings.valueStr("cosplay/current"))
        selected_path = settings.valueStr("cosplay/last_selection", None)
        print(selected_path)

        self.model.makeSelect(selected_path)
        # self.root_idx = self.model.setRootPath(settings.value("bitgirl/root"))
        # self.view.setRootIndex(self.root_idx)

    @Slot()
    def action_list_click(self, path, root, _) -> None:
        if path != self.selected_path:
            self.selected_path = path
            print(self.selected_path)
            settings.setValue("cosplay/last_selection", self.selected_path)
            if path is not None and os.path.isdir(path):
                self.show_info()
                if root == settings.valueStr("cosplay/download"):
                    self.action_show_images_local()

    @Slot()
    def action_list_double_click(self, path, _1, _2) -> None:
        if path.split(".")[-1].lower() in MyImageDialog.FORMAT:
            dialog = MyImageDialog(self, path, screen.availableGeometry().size())
            dialog.exec()
            dialog.deleteLater()
        else:
            os.startfile(path)

    @Slot()
    def model_root_changed(self, new_root):
        settings.setValue("cosplay/current", new_root)

    @Slot()
    def action_settings(self) -> None:
        dialog = SettingDialog(self, settings, "cosplay")
        if dialog.exec():
            self.apply_settings()
        dialog.deleteLater()

    @Slot()
    def action_info_out(self, mess) -> None:
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
        pass

    @Slot()
    def action_recheck(self):
        pass

    @Slot()
    def action_parse_page(self):
        w = XinmeituluListWidget()
        self.image_new_flow.clearAll()
        self.image_new_flow.addWidget(w, front=True)
        w.info_download.connect(self.paste_download_url)

    @Slot()
    def action_move_folder(self):
        w = CosplayMoveWidget(settings.valueStr("cosplay/root"), self.selected_path)
        self.image_new_flow.clearAll()
        self.image_new_flow.addWidget(w, front=True)
        w.on_move.connect(self.action_to_folder)

    @Slot()
    def paste_download_url(self, url):
        self.xin_mei_tutu.txt_url.setText(url)

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
        self.image_flow.group_by_date = False

    @Slot()
    def action_show_page(self, num: int):
        w = MyButton("1", self.action_show_images_local, param=[0])
        self.image_flow.addWidget(w)
        for i in range(num):
            w = MyButton(str(i + 2), self.action_show_images_local, param=[i + 1])
            self.image_flow.addWidget(w)

    def async_load_images_local(self, folder, as_size, page, thread):
        files = list_jpg(folder)

        p = int(len(files) / 500)
        self.page_display.emit(p)

        files = files[page * 500:(page + 1) * 500]

        self.progress_reset_signal.emit(len(files))

        progress = 0
        count = 0

        for f in files:
            progress += 1
            self.progress_signal.emit(progress)
            if f.endswith("folder.jpg"):
                count += 1
                continue
            file = f.replace("\\", "/")

            if imghdr.what(file) is None:
                continue

            count += 1
            img = MyImageSource(file, self.thumb_size)
            self.image_signal.emit(file, as_size, img)
            if QThread.isInterruptionRequested(thread):
                break
        self.info_out.emit(f"{self.selected_path}: {count} / {len(files)}")
        return True

    @Slot()
    def action_show_large_img(self, path, thumb, auto_confirm):
        dialog = MyImageDialog(self, path, screen.availableGeometry().size(), thumb,
                               True, self.show_info,
                               scale_size=screen.availableGeometry().size())
        dialog.exec()

    @Slot()
    def action_open_url(self):
        url = self.txt_url.text()
        print(url)
        if url:
            webbrowser.open(url)

    @Slot()
    def action_update(self):
        if self.selected_path:
            url = self.txt_url.text()
            if url:
                self.xin_mei_tutu.txt_url.setText(url)
                self.xin_mei_tutu.download(self.selected_path)

    def show_info(self):
        image_path = None
        url = ""
        last = ""
        if self.selected_path is not None:
            if os.path.isdir(self.selected_path):
                # image = imutils.url_to_image("https://pbs.twimg.com/media/E_24DrNVUAIPlFe.jpg:small")
                self.txt_folder.setText(os.path.basename(self.selected_path))
                image_path = os.path.join(self.selected_path, "folder.jpg")
                # img = MyImageSource(image_path, self.image_frame.size)
                self.selected_data = InfoImage.load_info(self.selected_path)
                if self.selected_data is not None:
                    url = self.selected_data['url']
                    last = self.selected_data['lastUpdate']
        self.show_info_imp(image_path, url, last)

    def show_info_imp(self, img, url, last):
        self.image_frame.set_path_async(img)
        self.txt_url.setText(url)
        self.txt_date.setText(last)

    @Slot()
    def safe_exit(self):
        """exit the application gently so Spyder IDE will not hang"""
        settings.setValue("cosplay/splitterSizes", self.splitter_right.saveState())
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

    # settings.setValue("cosplay/current", "Y:/Cosplay/星之迟迟")

    if not settings.contains("cosplay/url1"):
        settings.setValue("cosplay/url1", "https://www.xinmeitulu.com//")
    if not settings.contains("cosplay/root"):
        settings.setValue("cosplay/root", "Y:/cosplay")
    if not settings.contains("cosplay/download"):
        settings.setValue("cosplay/download", "Y:/download/cosplay")
    if not settings.contains("cosplay/download_retry"):
        settings.setValue("cosplay/download_retry", 999)

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
