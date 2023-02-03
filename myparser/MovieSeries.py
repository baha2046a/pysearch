import os
import re

from PySide6.QtCore import QStringListModel, Slot, Signal
from PySide6.QtWidgets import QWidget, QListView, QAbstractItemView, QSpinBox, QLineEdit

from TextOut import TextOut
from myparser.MovieCache import MovieCacheLite
from myparser.movie import SearchType
from myparser.movie.paser import MovieParser
from myqt.MyQtCommon import QtVBox, MyButton, QtHBox, QtPasteEdit
from myqt.QtImage import MyImageSource
from myqt.MyQtWorker import MyThread, MyThreadPool


class SearchMovieWidget(QWidget):
    output = Signal(list)

    def __init__(self, parent, path: str, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.path = path
        self.view = QListView()
        self.model = QStringListModel(self)
        self.view.setModel(self.model)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.clicked.connect(self.action_list_click)
        self.txt_search = QtPasteEdit()
        self.txt_search.txt.setMinimumWidth(300)
        data = os.path.basename(path).split()
        data = list(map(lambda s: s.lstrip("[").rstrip("]"), data))

        self.model.setStringList(data)
        self.b_search_fanza = MyButton("Search Fanza", self.action_search, [SearchType.FANZA])
        self.b_search_javbus = MyButton("Search Javbus", self.action_search, [SearchType.JAVBUS])
        self.b_search_mgs = MyButton("Search MGS", self.action_search, [SearchType.MGS])
        self.b_search_duga = MyButton("Search DUGA", self.action_search, [SearchType.DUGA])
        self.b_search_eiten = MyButton("Search EITEN", self.action_search, [SearchType.EITEN])

        control = QtVBox().addAll(self.b_search_fanza, self.b_search_javbus, self.b_search_mgs,
                                  self.b_search_duga, self.b_search_eiten)
        layout = QtHBox().addAll(QtVBox().addAll(self.txt_search, self.view), control)

        self.setLayout(layout)

    @Slot()
    def action_list_click(self, index):
        self.txt_search.setText(index.data())

    @Slot()
    def action_search(self, stype: SearchType):
        if self.txt_search.text():
            self.output.emit([])
            MovieParser.parse(self.path, self.txt_search.text(), self.output, stype, single_mode=False,
                              signal_out_start=TextOut.progress_start, signal_out_end=TextOut.progress_end)


class PathSeriesWidget(QWidget):
    output = Signal(dict, MyImageSource, str)

    def __init__(self, parent, path, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.path = path
        self.selected = None
        self.s_list = {}

        for p in os.listdir(self.path):
            m = re.compile(r".+?\[([0-9A-Z]+?)-?(\d+)]").match(p)
            if m:
                m1 = str(m.groups()[0])
                m2 = str(m.groups()[1])

                if m1 in self.s_list:
                    self.s_list[m1][m2] = p
                else:
                    self.s_list[m1] = {m2: p}

        self.view = QListView()
        self.model = QStringListModel(self)
        self.view.setModel(self.model)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.clicked.connect(self.action_list_click)

        self.model.setStringList(sorted(self.s_list.keys()))

        self.txt_search = QtPasteEdit()
        self.txt_search.txt.setMinimumWidth(300)

        self.t_len = QSpinBox()
        self.t_len.setValue(3)
        self.b_search = MyButton("Search", self.action_show_series)

        layout = QtVBox().addAll(self.view, self.txt_search, QtHBox().addAll(self.t_len, self.b_search))
        self.setLayout(layout)

    @Slot()
    def action_list_click(self, index):
        self.txt_search.setText(index.data())
        # self.selected = index.data()

    @Slot()
    def action_show_series(self):
        thread = MyThread("get_series")
        thread.set_run(self.async_get_series, MovieCacheLite.data)
        thread.start()

    def async_get_series(self, local_data, thread):
        num_len = self.t_len.value()
        self.selected = self.txt_search.text()
        if self.selected and num_len > 1:
            paths = {}
            if self.selected in self.s_list.keys():
                paths = self.s_list[self.selected]

            mid_list = [[f"{self.selected}-{str(i).zfill(num_len)}", local_data] for i in range(1, 10 ** num_len)]
            MyThreadPool.asyncio(MovieParser.async_batch_get_movie_lite, [mid_list, thread, self.output, paths])
            # MovieParser.async_batch_get_movie_lite(mid_list, out_signal=self.output, thread=thread, exist=paths)
