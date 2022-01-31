import os
import shutil
from typing import Optional, AnyStr
from urllib import request

from PySide6 import QtCore
from PySide6.QtCore import Signal, QSize, Qt, Slot, QThread
from PySide6.QtGui import QImageReader, QPixmap, QPalette, QImage
from PySide6.QtWidgets import QLabel, QSizePolicy, QDialog, QScrollArea, QMessageBox

from MyCommon import copy_file
from TextOut import TextOut
from myqt.MyQtCommon import MyButton, MyHBox, MyVBox
from myqt.MyQtWorker import MyThread


class MyImageSource:
    # loader2 = QImageReader()

    def __init__(self, path: AnyStr, size: QSize = None, height: int = 0, q_pix=True, async_out: Signal = None):
        if not height and size:
            height = size.height()
        self.image_path = path
        self.pixmap: Optional[QPixmap] = None
        self.image: Optional[QImage] = None
        self.data = None
        self.async_out = async_out

        if not async_out:
            self.load(path, size, height, q_pix)
        else:
            load_thread = MyThread(None)
            load_thread.set_run(self.load, path, size, height, q_pix)
            load_thread.on_finish(on_finish=self.async_finish)
            load_thread.start()

    def async_finish(self) -> None:
        self.async_out.emit(self)

    def load(self, path, size, height, q_pix, thread: QThread = None) -> None:
        if path.startswith("http"):
            self.image_load_url(path, q_pix)
        else:
            if size is None and not height:
                self.image_load_file(path)
            else:
                self.image = self.image_load(path, height)

    def image_load_url(self, url: AnyStr, q_pix: bool) -> None:
        req = request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        if "javbus.com" in url:
            req.add_header('Referer', 'https://www.javbus.com/')
        with request.urlopen(req) as img:
            if q_pix:
                self.pixmap = QPixmap()
                self.pixmap.loadFromData(img.read())
            else:
                self.data = img.read()

    def image_load_file(self, path: AnyStr) -> None:
        self.image = QImage(path)

    def image_load(self, path: AnyStr, height: int) -> Optional[QImage]:
        # print(threading.current_thread().name, path, height)
        loader = QImageReader()
        loader.setFileName(path)
        if height > 0:
            orig_size = loader.size()
            factor = height / orig_size.height()
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

    def to_QPixmap(self) -> QPixmap:
        if self.data:
            pix = QPixmap()
            pix.loadFromData(self.data)
            return pix
        if self.pixmap:
            return self.pixmap
        return QPixmap.fromImage(self.image)


class MyImageBox(QLabel):
    on_image = Signal(MyImageSource)
    clicked = Signal(str, QLabel, bool)

    @classmethod
    def from_path(cls, path: str, size: QSize = None, *args, **kwargs):
        image = MyImageSource(path, size)
        return cls(size, image, *args, **kwargs)

    def __init__(self, size: QSize = None, image: MyImageSource = None, auto_confirm=False, parent=None):
        super().__init__(parent)
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self._size = size
        self.image_path = None
        self.ready = False
        self.auto_confirm = auto_confirm
        self.set_image(image)
        self.on_image.connect(self.set_image, Qt.QueuedConnection)

    def set_path(self, path):
        self.set_image(MyImageSource(path, self._size))
        return self

    def set_path_async(self, path):
        if path is not None:
            MyImageSource(path, self._size, async_out=self.on_image)
        return self

    @Slot()
    def set_image(self, image):
        if image is not None:
            self.image_path = image.image_path

            try:
                self.setPixmap(image.to_QPixmap())
            except Exception as e:
                self.ready = False
                print(e)
                return self

            if self._size:
                self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                my_width = min(self._size.width() * 2, image.width())
                # self.setFixedSize(QSize(my_width, image.height()))
                self.setFixedSize(QSize(my_width, self._size.height()))
            self.ready = True
        else:
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


class MyImageDialog(QDialog):
    FORMAT = ["jpg", "jpeg", "png"]

    def __init__(self, parent, path, max_size: QSize,
                 thumb=None, auto_confirm=False,
                 folder_image_change_action=None,
                 scale_size: QSize = None,
                 *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.setWindowTitle(path)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self.max_size = max_size
        self.image = MyImageSource(path, scale_size)
        self.thumb = thumb
        self.auto_confirm = auto_confirm
        self.folder_image_change_action = folder_image_change_action

        label = MyImageBox(None, self.image)

        self.but_delete_file = MyButton("Delete", self.action_delete_file)
        self.but_use_folder_jpg = MyButton("Folder.jpg", self.action_use_folder_jpg)
        self.but_prev = MyButton("<", self.action_prev)
        self.but_next = MyButton(">", self.action_next)

        bar = MyHBox().addAll(self.but_use_folder_jpg, self.but_delete_file, self.but_prev, self.but_next)

        if self.image.width() > self.max_size.width() or self.image.height() > (self.max_size.height() - 100):
            scroll = QScrollArea(self)
            scroll.setBackgroundRole(QPalette.Dark)
            scroll.setWidget(label)
            scroll.setWidgetResizable(True)
            w = min(self.image.width(), self.max_size.width() - 40)
            h = min(self.image.height(), self.max_size.height() - 100)
            scroll.setFixedSize(w, h)
            layout = MyVBox().addAll(bar, scroll)
        else:
            layout = MyVBox().addAll(bar, label)
        self.setLayout(layout)

    @QtCore.Slot()
    def action_prev(self):
        src = self.windowTitle()
        folder = os.path.dirname(src)
        file_num = os.path.basename(src)
        print(file_num[:-4])
        try:
            prev_num = int(file_num[:-4]) - 1
            prev_path = '{}/{:04}.jpg'.format(folder, prev_num)
            if os.path.exists(prev_path):
                tmp_path = '{}/tmp.jpg'.format(folder)
                shutil.move(prev_path, tmp_path)
                shutil.move(src, prev_path)
                shutil.move(tmp_path, src)
                self.setWindowTitle(prev_path)
                TextOut.out(f"{prev_path} << {src}")
        except Exception as e:
            print(e)

    @QtCore.Slot()
    def action_next(self):
        src = self.windowTitle()
        folder = os.path.dirname(src)
        file_num = os.path.basename(src)
        print(file_num[:-4])
        try:
            next_num = int(file_num[:-4]) + 1
            next_path = '{}/{:04}.jpg'.format(folder, next_num)
            if os.path.exists(next_path):
                tmp_path = '{}/tmp.jpg'.format(folder)
                shutil.move(next_path, tmp_path)
                shutil.move(src, next_path)
                shutil.move(tmp_path, src)
                self.setWindowTitle(next_path)
                TextOut.out(f"{next_path} << {src}")
        except Exception as e:
            print(e)

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
