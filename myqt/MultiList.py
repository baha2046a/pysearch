from typing import Union, Any

import PySide6
from PySide6.QtCore import QAbstractTableModel, Slot, QModelIndex
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QTableView

from myparser.InfoMovie import InfoActor
from myparser.MovieCache import MovieCache
from myparser.MovieWidget import ActorWidget
from myqt.MyQtCommon import QtVBox, QtDialogAutoClose, MyButton, QtHBox


class ActorTableModel(QAbstractTableModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor_data = []
        self.sort_by_param = [[1, False, ""]]
        self.column_count = 6
        self.load()

    def load(self):
        movie_count = MovieCache.count_by_actor()
        actor_data = InfoActor.to_list()
        self.actor_data = [[*a, movie_count[a[0]]] for a in actor_data if a[0] in movie_count]
        self.sort_by(self.sort_by_param)

    @staticmethod
    def multi_sort(data, specs):
        for key, reverse, empty in reversed(specs):
            data.sort(key=lambda x: x[key] or empty, reverse=reverse)
        return data

    def sort_by(self, param: list):
        if param:
            col, reverse, empty = param[0]
            if len(param) < 2 and col != 1:
                param.append([1, False, ""])
            self.sort_by_param = param
            self.beginResetModel()
            self.actor_data = self.multi_sort(self.actor_data, self.sort_by_param)
            #sorted(self.actor_data, key=lambda x: x[col] or empty, reverse=reverse)
            self.endResetModel()

    def data(self, index: Union[PySide6.QtCore.QModelIndex, PySide6.QtCore.QPersistentModelIndex],
             role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self.actor_data):
            return None
        if role == Qt.DisplayRole:
            return self.actor_data[index.row()][index.column()]
        return None

    def columnCount(self, parent: Union[PySide6.QtCore.QModelIndex, PySide6.QtCore.QPersistentModelIndex] = ...) -> int:
        return self.column_count

    def rowCount(self, parent: Union[PySide6.QtCore.QModelIndex, PySide6.QtCore.QPersistentModelIndex] = ...) -> int:
        return len(self.actor_data)


class ActorListDialog(QtDialogAutoClose):
    can_open = True

    @staticmethod
    def get(parent):
        if ActorListDialog.can_open:
            return ActorListDialog(parent)
        return None

    def closeEvent(self, arg__1):
        ActorListDialog.can_open = True
        super().closeEvent(arg__1)

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        ActorListDialog.can_open = False

        self.vbox = QtVBox()
        self.table = QTableView()

        self.model = ActorTableModel()
        self.table.setModel(self.model)
        for i in range(self.model.columnCount()):
            if i > 2:
                self.table.setColumnWidth(i, 150)
            else:
                self.table.setColumnWidth(i, 300)
        self.table.clicked.connect(self.action_list_click)

        self.detail = ActorWidget()
        self.detail.setMaximumHeight(230)

        but_reload = MyButton("Reload", self.model.load)
        but_sort_name = MyButton("Sort: Name", self.model.sort_by, [[[1, False, ""]]])
        but_sort_age = MyButton("Sort: Age", self.model.sort_by, [[[3, False, 0]]])
        but_sort_tall = MyButton("Sort: Tall", self.model.sort_by, [[[4, True, 0]]])
        but_sort_movie = MyButton("Sort: Movie", self.model.sort_by, [[[5, True, 0]]])

        layout = QtVBox().addAll(self.table, self.detail,
                                 QtHBox().addAll(but_reload, but_sort_name, but_sort_age, but_sort_tall,
                                                 but_sort_movie))

        self.setLayout(layout)
        self.resize(1600, 900)
        self.setWindowTitle("Actors")

    @Slot()
    def action_list_click(self, index):
        actor = self.model.data(index.siblingAtColumn(0))
        if actor != self.detail.actor:
            self.detail.set_actor(actor)
