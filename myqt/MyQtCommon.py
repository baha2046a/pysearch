from PySide6.QtWidgets import QHBoxLayout, QWidget, QLayout, QBoxLayout, QLayoutItem, QVBoxLayout, QPushButton, QFrame


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
        if isinstance(item, QWidget):
            self.addWidget(item)
        elif isinstance(item, QLayout):
            self.addLayout(item)
        return self

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


class MyButton(QPushButton):
    def __init__(self, text, on_click, *args, **kwargs):
        super().__init__(text, *args, **kwargs)
        self.clicked.connect(on_click)


class HorizontalLine(QFrame):
    def __init__(self, *args, **kwargs):
        super(HorizontalLine, self).__init__(*args, **kwargs)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)