import os
import subprocess
from typing import overload, Callable, Union

import pyperclip
from PySide6.QtCore import Slot
from PySide6.QtGui import QIcon, Qt, QColor
from PySide6.QtWidgets import QHBoxLayout, QWidget, QLayout, QBoxLayout, QLayoutItem, QVBoxLayout, QPushButton, QFrame, \
    QLineEdit, QDialog
import PySide6.QtCore as QtCore
import qtawesome as qta


def clear_all(layout) -> None:
    if layout is not None:
        while layout.count():
            child: QLayoutItem = layout.takeAt(0)
            if child.widget() is not None:
                child.widget().deleteLater()
            elif child.layout() is not None:
                clear_all(child.layout())


def fa_icon(name: str, color=QColor(200, 200, 200)) -> QIcon:
    return qta.icon(name, color=color)


class MyQtLayout(QBoxLayout):
    def add(self, item: Union[QWidget, QLayout]):
        if item:
            if isinstance(item, QWidget):
                self.addWidget(item)
            elif isinstance(item, QLayout):
                self.addLayout(item)
        return self

    def clear(self):
        clear_all(self)

    def addAll(self, *args):
        for arg in args:
            self.add(arg)
        return self

    def setStyleSheet(self, css):
        for i in range(self.count()):
            if self.itemAt(i).widget():
                self.itemAt(i).widget().setStyleSheet(css)
        for i in self.children():
            if type(i) in (QtHBox, QtVBox):
                i.setStyleSheet(css)

    def set(self, item):
        clear_all(self)
        self.add(item)
        return self

    def setAll(self, *args):
        clear_all(self)
        self.addAll(args)
        return self

    def toWidget(self) -> QWidget:
        widget = QWidget()
        widget.setLayout(self)
        return widget


class QtHBox(QHBoxLayout, MyQtLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class QtVBox(QVBoxLayout, MyQtLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class QtPasteEdit(QtHBox):
    def __init__(self, text="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.txt = QLineEdit(text)
        self.but_paste = MyButton(fa_icon("fa.paste"), self.paste)
        self.but_copy = MyButton(fa_icon("mdi.content-cut"), self.copy)
        self.addAll(self.txt, self.but_copy, self.but_paste)

    def text(self) -> str:
        return self.txt.text()

    def setText(self, text: str):
        self.txt.setText(text)

    def setReadOnly(self, read: bool):
        self.txt.setReadOnly(read)

    def paste(self):
        self.txt.setText(pyperclip.paste())

    def copy(self):
        pyperclip.copy(self.txt.text())


class MyButton(QPushButton):
    @overload
    def __init__(self, main: str, on_click: Callable = None, param=None, large_text: bool = False, extra: QIcon = None):
        ...

    @overload
    def __init__(self, main: QIcon, on_click: Callable = None, param=None,
                 large_text: bool = False, extra: str = "", icon_size: int = 30):
        ...

    def __init__(self, main: Union[str, QIcon],
                 on_click: Callable = None, param=None,
                 large_text: bool = False, extra: Union[str, QIcon] = None, icon_size: int = 30):
        if main is None:
            super().__init__()
        elif type(main) is str:
            super().__init__(text=main)
        else:
            super().__init__(icon=main, text=extra)
            self.setIconSize(QtCore.QSize(icon_size, icon_size))

        if param is None:
            param = []
        if large_text:
            self.setStyleSheet("font-size: 22px;" "padding: 4px;")

        if on_click:
            self.onClick(on_click, param)

    def onClick(self, on_click: Callable, param=None):
        if param is not None:
            self.clicked.connect(lambda: on_click(*param))
        else:
            self.clicked.connect(on_click())


class QtDialog(QDialog):
    @staticmethod
    def _icon_ok():
        return fa_icon("ei.ok-sign")

    @staticmethod
    def _icon_cancel():
        return fa_icon("ei.remove-sign")

    def _bar_ok_cancel(self, but_ok: QWidget = None) -> QtHBox:
        if but_ok is None:
            but_ok = MyButton(self._icon_ok(), self.accept)
        but_cancel = MyButton(self._icon_cancel(), self.reject)
        return QtHBox().addAll(but_ok, but_cancel)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowIcon(fa_icon("fa5s.sliders-h"))


class QtDialogAutoClose(QtDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAttribute(Qt.WA_DeleteOnClose)

    @Slot()
    def action_external(self):
        os.startfile(self.windowTitle())

    @Slot()
    def action_explorer(self):
        folder = os.path.dirname(self.windowTitle()).replace('/', '\\')
        subprocess.Popen(f"explorer {folder}")


class HorizontalLine(QFrame):
    def __init__(self, *args, **kwargs):
        super(HorizontalLine, self).__init__(*args, **kwargs)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)
