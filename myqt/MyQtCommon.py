import pyperclip
from PySide6.QtWidgets import QHBoxLayout, QWidget, QLayout, QBoxLayout, QLayoutItem, QVBoxLayout, QPushButton, QFrame, \
    QLineEdit


def clear_all(layout) -> None:
    if layout is not None:
        while layout.count():
            child: QLayoutItem = layout.takeAt(0)
            if child.widget() is not None:
                child.widget().deleteLater()
            elif child.layout() is not None:
                clear_all(child.layout())


class MyQtLayout(QBoxLayout):
    def add(self, item):
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

    def set(self, item):
        clear_all(self)
        self.add(item)
        return self

    def setAll(self, *args):
        clear_all(self)
        self.addAll(args)
        return self


class MyHBox(QHBoxLayout, MyQtLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class MyVBox(QVBoxLayout, MyQtLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class MyPasteEdit(MyHBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.txt = QLineEdit("")
        self.but_paste = MyButton('📋', self.paste)
        self.addAll(self.txt, self.but_paste)

    def text(self) -> str:
        return self.txt.text()

    def setText(self, text: str):
        self.txt.setText(text)

    def setReadOnly(self, read: bool):
        self.txt.setReadOnly(read)

    def paste(self):
        self.txt.setText(pyperclip.paste())


class MyButton(QPushButton):
    def __init__(self, text, on_click=None, param=None, large_text: bool = False, *args, **kwargs):
        super().__init__(text=text, *args, **kwargs)
        if param is None:
            param = []
        if large_text:
            self.setStyleSheet("font-size: 22px;" "padding: 4px;")

        if on_click:
            if param is not None:
                self.clicked.connect(lambda: on_click(*param))
            else:
                self.clicked.connect(on_click())


class HorizontalLine(QFrame):
    def __init__(self, *args, **kwargs):
        super(HorizontalLine, self).__init__(*args, **kwargs)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)
