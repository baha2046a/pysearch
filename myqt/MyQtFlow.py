#!/usr/bin/env python3
import sys
from typing import Optional
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt, QMargins, QPoint, QRect, QSize, Slot
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import *
from PySide6.QtWidgets import QWidget

from myqt.QtImage import MyImageSource, MyImageBox


class MyQtFlowLayout(QLayout):
    add_to_front = False

    def __init__(self, parent=None):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(QMargins(0, 0, 0, 0))

        self._item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem) -> None:
        if MyQtFlowLayout.add_to_front:
            self._item_list.insert(0, item)
        else:
            self._item_list.append(item)

    def count(self) -> int:
        return len(self._item_list)

    def itemAt(self, index: int) -> Optional[QLayoutItem]:
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index: int) -> Optional[QLayoutItem]:
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width: int) -> int:
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect) -> None:
        super(MyQtFlowLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2 * self.contentsMargins().top(),
                      2 * self.contentsMargins().top())
        return size

    def _do_layout(self, rect, test_only) -> int:
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        last_type = None
        full_width = rect.right() - rect.x() - 10

        for item in self._item_list:
            current_type = type(item.widget())
            new_line: bool = current_type is not last_type
            last_type = current_type

            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(QSizePolicy.PushButton,
                                                   QSizePolicy.PushButton,
                                                   Qt.Horizontal)
            layout_spacing_y = style.layoutSpacing(QSizePolicy.PushButton,
                                                   QSizePolicy.PushButton,
                                                   Qt.Vertical)

            # item.widget().setFixedWidth(rect.right() - rect.x())

            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y
            next_x = x + item.sizeHint().width() + space_x
            if (new_line or next_x - space_x > rect.right()) and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                if current_type is QPushButton:
                    item.setGeometry(QRect(QPoint(x, y), QSize(full_width, item.sizeHint().height())))
                else:
                    item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()


class MyQtFlowWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(MyQtFlowLayout(self))
        self.date_str = ""

    def sizeHint(self) -> QSize:
        return self.layout().sizeHint()

    def minimumSize(self) -> QSize:
        return self.layout().minimumSize()

    def addWidget(self, _widget: QWidget) -> None:
        self.layout().addWidget(_widget)

    def clearAll(self) -> None:
        QWidget().setLayout(self.layout())
        self.setLayout(MyQtFlowLayout())


class MyQtScrollableFlow(QScrollArea):
    def __init__(self, flow_widget=None, parent=None, group_by_date=False):
        super().__init__(parent)
        self.date_str = ""
        self.group_by_date = group_by_date
        self.flow = flow_widget
        if not self.flow:
            self.flow = MyQtFlowWidget(self)
        self.setBackgroundRole(QPalette.Dark)
        self.setWidget(self.flow)
        self.setWidgetResizable(True)
        self.can_remove = True

    @Slot()
    def change_can_remove(self, val: bool) -> None:
        self.can_remove = val

    def addWidget(self, item: QWidget, front=False) -> None:
        MyQtFlowLayout.add_to_front = front
        self.flow.addWidget(item)
        if hasattr(item, 'can_remove'):
            item.can_remove.connect(self.change_can_remove, Qt.QueuedConnection)

    def clearAll(self) -> None:
        if self.can_remove:
            self.date_str = ""
            self.flow.clearAll()

    def show_img(self, as_size, img: MyImageSource, on_click):
        if self.group_by_date:
            date_str = img.image_path.split("/")[-1][:7]
            if not date_str == self.date_str:
                self.date_str = date_str
                date_label = QPushButton(date_str)
                date_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                self.addWidget(date_label)
        label = MyImageBox(self, as_size, img).display(self)
        label.on_click(on_click)


if __name__ == '__main__':
    print("Program Start")
    app = QtCore.QCoreApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    widget = QWidget()
    widget.setWindowTitle(" ")
    widget.setWindowFlags(Qt.Dialog)
    widget.show()

    sys.exit(app.exec())
