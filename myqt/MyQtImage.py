import os
from typing import Any
from urllib import request

from PySide6 import QtCore
from PySide6.QtCore import Signal, QSize, Qt
from PySide6.QtGui import QImageReader, QPixmap, QPalette, QImage
from PySide6.QtWidgets import QLabel, QSizePolicy, QDialog, QScrollArea, QMessageBox
from MyCommon import synchronized_method, copy_file
from myqt.MyQtCommon import MyButton, MyHBox, MyVBox


class MyImageSource:
    loader = QImageReader()

    def __init__(self, path: str, size: QSize = None, height: int = 0):
        if not height and size:
            height = size.height()
        self.image_path = path
        self.pixmap: QPixmap = None
        self.image: QImage = None

        if path.startswith("http"):
            self.image_load_url(path)
        else:
            self.image = self.image_load(path, height)

    def image_load_url(self, url: str):
        req = request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        if "javbus.com" in url:
            req.add_header('Referer', 'https://www.javbus.com/')
        with request.urlopen(req) as img:
            self.pixmap = QPixmap()
            self.pixmap.loadFromData(img.read())

    @synchronized_method
    def image_load(self, path: str, height: int):
        # print(threading.current_thread().name, path, height)
        MyImageSource.loader.setFileName(path)
        if height > 0:
            orig_size = MyImageSource.loader.size()
            factor = height / orig_size.height()
            MyImageSource.loader.setScaledSize(QSize(int(orig_size.width() * factor), height))
        else:
            orig_size = MyImageSource.loader.size()
            MyImageSource.loader.setScaledSize(orig_size)
        return MyImageSource.loader.read()

    def as_size(self, size: QSize):
        if self.pixmap:
            self.pixmap = self.pixmap.scaledToHeight(size.height(), Qt.SmoothTransformation)
        else:
            self.image = self.image.scaledToHeight(size.height(), Qt.SmoothTransformation)
        return self

    def size(self):
        if self.pixmap:
            return self.pixmap.rect().size()
        return self.image.rect().size()

    def width(self):
        if self.pixmap:
            return self.pixmap.width()
        return self.image.width()

    def height(self):
        if self.pixmap:
            return self.pixmap.height()
        return self.image.height()

    def to_QPixmap(self):
        if self.pixmap:
            return self.pixmap
        return QPixmap.fromImage(self.image)


class MyImageBox(QLabel):
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

    def set_path(self, path):
        self.set_image(MyImageSource(path, self._size))
        return self

    def set_image(self, image):
        if image is not None:
            self.image_path = image.image_path
            self.setPixmap(image.to_QPixmap())
            if self._size:
                self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                my_width = min(self._size.width() * 2, image.width())
                self.setFixedSize(QSize(my_width, image.height()))
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
    def __init__(self, parent, path, max_size: QSize,
                 thumb=None, auto_confirm=False, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.setWindowTitle(path)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self.max_size = max_size
        self.image = MyImageSource(path)
        self.thumb = thumb
        self.auto_confirm = auto_confirm

        label = MyImageBox(None, self.image)

        self.but_delete_file = MyButton("Delete", self.action_delete_file)
        self.but_use_folder_jpg = MyButton("Folder.jpg", self.action_use_folder_jpg)

        bar = MyHBox().addAll(self.but_use_folder_jpg, self.but_delete_file)

        if self.image.width() > self.max_size.width() or self.image.height() > self.max_size.height():
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
    def action_use_folder_jpg(self):
        src = self.windowTitle()
        des = os.path.join(os.path.dirname(src), "folder.jpg")
        print(src, des)
        copy_file(src, des)

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
            except Any:
                pass
            finally:
                self.accept()