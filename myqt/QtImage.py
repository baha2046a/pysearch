import base64
import os
import shutil
from typing import Optional, AnyStr, Union
from urllib import request

import PySide6.QtGui
from PySide6 import QtCore
from PySide6.QtCore import Signal, QSize, Qt, Slot
from PySide6.QtGui import QImageReader, QPixmap, QPalette, QImage
from PySide6.QtWidgets import QLabel, QSizePolicy, QScrollArea, QMessageBox

from MyCommon import copy_file, next_image_path
from myqt.MyQtCommon import MyButton, QtHBox, QtVBox, fa_icon, QtDialogAutoClose
from myqt.MyQtWorker import MyThreadPool


class MyImageSource:
    # loader2 = QImageReader()

    @classmethod
    def from_image(cls, q_img: QImage, path: AnyStr):
        img = cls("")
        img.image_path = path
        img.image = q_img
        return img

    @classmethod
    def from_base64(cls, base_64: Union[str, bytes]):
        if isinstance(base_64, str):
            base_64 = base_64.encode()
        img = cls("")
        pixmap = QPixmap()
        pixmap.loadFromData(QtCore.QByteArray.fromBase64(base_64))
        img.pixmap = pixmap
        return img

    def __init__(self, path: AnyStr, size: QSize = None, height: int = 0, q_pix=True, async_out: Signal = None):
        if not height and size:
            height = size.height()
        self.image_path = path
        self.pixmap: Optional[QPixmap] = None
        self.image: Optional[QImage] = None
        self.data = None
        self.async_out = async_out

        if path != "":
            if path.startswith("data:image/"):
                if isinstance(path, str):
                    path = path.encode()
                path = path[path.find(b"/9j"):]
                data = base64.b64decode(path)
                self.pixmap = QPixmap()
                self.pixmap.loadFromData(data)
                if async_out:
                    self.async_out.emit(self)
            else:
                if not async_out:
                    self.load(path, size, height, q_pix)
                else:
                    MyThreadPool.start(None, None, None, None,
                                       self.load, path, size, height, q_pix)

    def load(self, path, size, height, q_pix) -> None:
        if path.startswith("http"):
            self.image_load_url(path, q_pix, height)
        else:
            if size is None and not height:
                self.image_load_file(path)
            else:
                self.image = self.image_load(path, height)
        if self.async_out:
            self.async_out.emit(self)

    def image_load_url(self, url: AnyStr, q_pix: bool, height: int = 0) -> None:
        try:
            req = request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            if "javbus.com" in url:
                req.add_header('Referer', 'https://www.javbus.com/')
            with request.urlopen(req) as img:
                if q_pix:
                    self.pixmap = QPixmap()
                    self.pixmap.loadFromData(img.read())
                    if 0 < height < self.pixmap.height():
                        self.pixmap = self.pixmap.scaledToHeight(height)
                else:
                    self.data = img.read()
        except Exception as ex:
            self.data = None
            self.pixmap = None
            print("image_load_url", ex)

    def image_load_file(self, path: AnyStr) -> None:
        self.image = QImage(path)

    def image_load(self, path: AnyStr, height: int) -> Optional[QImage]:
        # print(threading.current_thread().name, path, height)
        loader = QImageReader()
        loader.setFileName(path)
        if height > 0:
            orig_size = loader.size()
            factor = height / orig_size.height()
            if factor > 1:
                factor = 1
                height = orig_size.height()
            try:
                loader.setScaledSize(QSize(int(orig_size.width() * factor), height))
                return loader.read()
            except Exception as e:
                print(e)
        else:
            orig_size = loader.size()
            try:
                loader.setScaledSize(orig_size)
                return loader.read()
            except Exception as e:
                print(e)
        return None

    def as_size(self, size: QSize):
        if self.pixmap:
            self.pixmap = self.pixmap.scaledToHeight(size.height(), Qt.SmoothTransformation)
        else:
            if self.image:
                self.image = self.image.scaledToHeight(size.height(), Qt.SmoothTransformation)
        return self

    def size(self) -> QSize:
        if self.pixmap:
            return self.pixmap.rect().size()
        return self.image.rect().size()

    def width(self) -> int:
        if self.pixmap:
            return self.pixmap.width()
        return self.image.width()

    def height(self) -> int:
        if self.pixmap:
            return self.pixmap.height()
        return self.image.height()

    def to_QPixmap(self) -> Optional[QPixmap]:
        if self.data:
            pix = QPixmap()
            pix.loadFromData(self.data)
            return pix
        if self.pixmap:
            return self.pixmap
        if self.image:
            return QPixmap.fromImage(self.image)
        return None


class MyImageBox(QLabel):
    on_image = Signal(MyImageSource)
    clicked = Signal(str, QLabel, bool)

    @classmethod
    def from_path(cls, parent, path: str, size: QSize = None, asyn = False, *args, **kwargs):
        if path is None:
            return None
        if asyn:
            box = cls(parent, size, None, *args, **kwargs)
            image = MyImageSource(path, size, async_out=box.on_image)
            box.set_image(image)
            return box
        else:
            image = MyImageSource(path, size)
            return cls(parent, size, image, *args, **kwargs)

    def __init__(self, parent, size: QSize = None, image: MyImageSource = None,
                 auto_confirm=False):
        super().__init__(parent)
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.out_size = size
        self.image_path = None
        self.ready = False
        self.auto_confirm = auto_confirm
        self.set_image(image)
        self.on_image.connect(self.set_image, Qt.QueuedConnection)

    def set_path(self, path):
        self.set_image(MyImageSource(path, self.out_size))
        return self

    def set_path_async(self, path):
        if path is not None:
            if self.out_size:
                height = self.out_size.height()
            else:
                height = 0
            MyImageSource(path, self.out_size, height, async_out=self.on_image)
        else:
            self.setVisible(False)
        return self

    @Slot()
    def set_image(self, image):
        if image is not None:
            self.image_path = image.image_path

            loaded_image = image.to_QPixmap()
            if loaded_image:
                self.setPixmap(image.to_QPixmap())
            else:
                self.setVisible(False)
                self.ready = False
                return self

            if self.out_size:
                self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                my_width = min(self.out_size.width() * 2, image.width())
                # self.setFixedSize(QSize(my_width, image.height()))
                self.setFixedSize(QSize(my_width, self.out_size.height()))
            self.setVisible(True)
            self.ready = True
        else:
            self.setVisible(False)
            self.ready = False
        return self

    def display(self, target):
        if self.ready:
            target.addWidget(self)
        return self

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.image_path, self, self.auto_confirm)
        return QLabel.mousePressEvent(self, event)

    def on_click(self, call):
        self.clicked.connect(call)


class MyImageDialog(QtDialogAutoClose):
    FORMAT = [".jpg", ".jpeg", ".png", ".gif"]

    @staticmethod
    def is_image(path: AnyStr) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in MyImageDialog.FORMAT

    def __init__(self, parent, path, max_size: QSize,
                 thumb=None, auto_confirm=False,
                 folder_image_change_action=None,
                 scale_size: QSize = None,
                 *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.setWindowTitle(path)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self.setWindowIcon(fa_icon('fa5s.file-image', "black"))

        self.max_size = max_size
        self.scale_size = scale_size

        if scale_size is not None and scale_size.height() >= (max_size.height() - 100):
            self.scale_size = QSize(self.scale_size.width(), max_size.height() - 100)

        self.image = MyImageSource(path, self.scale_size)
        self.thumb = thumb
        self.auto_confirm = auto_confirm
        self.folder_image_change_action = folder_image_change_action

        txt_tools = QLabel(self)
        txt_tools.setPixmap(fa_icon('fa5s.cog').pixmap(QSize(28, 28)))
        txt_tools.setContentsMargins(20, 0, 3, 0)

        self.but_delete_file = MyButton(fa_icon('fa5s.trash'), self.action_delete_file, icon_size=28)
        self.but_use_folder_jpg = MyButton(fa_icon('fa5s.folder-plus'), self.action_use_folder_jpg)

        txt_rename = QLabel(self)
        txt_rename.setPixmap(fa_icon('fa5s.file-signature').pixmap(QSize(28, 28)))
        txt_rename.setContentsMargins(20, 0, 3, 0)

        self.but_move_prev = MyButton(fa_icon('fa5s.sort-numeric-up'), self.action_move_next, [-1])
        self.but_move_next = MyButton(fa_icon('fa5s.sort-numeric-down'), self.action_move_next, [1])

        txt_move = QLabel(self)
        txt_move.setPixmap(fa_icon('fa5s.file-code').pixmap(QSize(28, 28)))
        txt_move.setContentsMargins(20, 0, 3, 0)

        self.but_prev = MyButton(fa_icon('fa5s.angle-left'), self.action_next, [-1])
        self.but_next = MyButton(fa_icon('fa5s.angle-right'), self.action_next, [1])

        self.but_external = MyButton(fa_icon('fa5s.sign-out-alt'), self.action_external)
        self.but_explorer = MyButton(fa_icon("ph.folder-open-fill"), self.action_explorer)

        set1 = QtHBox().addAll(txt_tools, self.but_use_folder_jpg, self.but_delete_file)
        set2 = QtHBox().addAll(txt_rename, self.but_move_prev, self.but_move_next)
        set3 = QtHBox().addAll(txt_move, self.but_prev, self.but_next)

        self.bar = QtHBox().addAll(self.but_external, self.but_explorer, set1, set2, set3)
        self.bar.addStretch(1)

        self.img_box = QtVBox()
        self.show_img(True)

    def keyPressEvent(self, arg__1: PySide6.QtGui.QKeyEvent) -> None:
        if arg__1.key() == Qt.Key_A:
            self.action_next(-1)
        elif arg__1.key() == Qt.Key_D:
            self.action_next(1)
        elif arg__1.key() == Qt.Key_X:
            self.close()
        super().keyPressEvent(arg__1)

    def show_img(self, first: bool = False):
        label = MyImageBox(self, None, self.image)

        if self.image.width() > self.max_size.width() or self.image.height() > (self.max_size.height() - 100):
            scroll = QScrollArea(self)
            scroll.setBackgroundRole(QPalette.Dark)
            scroll.setWidget(label)
            scroll.setWidgetResizable(True)
            w = min(self.image.width(), self.max_size.width() - 40)
            h = min(self.image.height(), self.max_size.height() - 100)
            scroll.setFixedSize(w, h)
            self.img_box.set(scroll)
        else:
            self.img_box.set(label)

        if first:
            self.setLayout(QtVBox().addAll(self.bar, self.img_box))

    @QtCore.Slot()
    def action_move_next(self, delta: int):
        src = self.windowTitle()
        folder = os.path.dirname(src)
        next_path = next_image_path(src, delta)
        if next_path and os.path.exists(next_path):
            tmp_path = '{}/tmp.jpg'.format(folder)
            shutil.move(next_path, tmp_path)
            shutil.move(src, next_path)
            shutil.move(tmp_path, src)
            self.set_new_path(next_path)

    @QtCore.Slot()
    def action_next(self, delta: int):
        src = self.windowTitle()
        next_path = next_image_path(src, delta)
        if next_path and os.path.exists(next_path):
            self.set_new_path(next_path)

    def set_new_path(self, path):
        self.image = MyImageSource(path, self.scale_size)
        self.setWindowTitle(path)
        self.show_img()

    @QtCore.Slot()
    def action_use_folder_jpg(self):
        src = self.windowTitle()
        des = os.path.join(os.path.dirname(src), "folder.jpg")
        print(src, des)
        copy_file(src, des)
        if self.folder_image_change_action:
            self.folder_image_change_action()

    @QtCore.Slot()
    def action_delete_file(self):
        if not self.auto_confirm:
            ret = QMessageBox.information(self, "Confirm", "Delete File?", QMessageBox.Yes, QMessageBox.No)
        else:
            ret = QMessageBox.Yes

        if ret == QMessageBox.Yes:
            try:
                os.remove(self.windowTitle())
                self.thumb.setParent(None)
                self.thumb.deleteLater()
            except Exception as e:
                print(e)
            finally:
                self.accept()
