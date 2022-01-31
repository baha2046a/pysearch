import os
import re
import time
from multiprocessing import Pool

from PySide6.QtCore import QStringListModel, Slot, Signal
from PySide6.QtWidgets import QWidget, QListView, QAbstractItemView, QTextEdit, QLineEdit, QSpinBox

from myparser.JavBusMain import get_javbus_series
from myparser.MovieCache import MovieCacheLite
from myparser.MovieNameFix import movie_name_fix
from myqt.MyQtCommon import MyVBox, MyButton, MyHBox
from myqt.MyQtImage import MyImageSource
from myqt.MyQtWorker import MyThread


class SearchMovieWidget(QWidget):
    output = Signal(str, str)

    def __init__(self, path: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.path = path
        self.selected = None
        self.view = QListView()
        self.model = QStringListModel(self)
        self.view.setModel(self.model)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.clicked.connect(self.action_list_click)
        data = os.path.basename(path).split()
        data = list(map(lambda s: s.lstrip("[").rstrip("]"), data))

        self.model.setStringList(data)
        self.b_search = MyButton("Search", self.action_search)

        layout = MyVBox().addAll(self.view, self.b_search)
        self.setLayout(layout)

    @Slot()
    def action_list_click(self, index):
        self.selected = index.data()

    @Slot()
    def action_search(self):
        if self.selected:
            self.output.emit(self.selected, self.path)


class PathSeriesWidget(QWidget):
    output = Signal(dict, MyImageSource, str)

    def __init__(self, path, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

        self.t_len = QSpinBox()
        self.t_len.setValue(3)
        self.b_search = MyButton("Search", self.action_show_series)

        layout = MyVBox().addAll(self.view, MyHBox().addAll(self.t_len, self.b_search))
        self.setLayout(layout)

    @Slot()
    def action_list_click(self, index):
        self.selected = index.data()

    @Slot()
    def action_show_series(self):
        thread = MyThread("get_series")
        thread.set_run(self.async_get_series, MovieCacheLite.data)
        thread.start()

    def async_get_series(self, local_data, thread):
        num_len = self.t_len.value()
        if self.selected and num_len > 1:
            exist = self.s_list[self.selected]
            paths = {}
            if self.selected in self.s_list.keys():
                paths = self.s_list[self.selected]

            mid_list = [[f"{self.selected}-{str(i).zfill(num_len)}", local_data] for i in range(1, 10 ** num_len)]
            self.batch_get_movie_lite(mid_list, out_signal=self.output, thread=thread, exist=paths)

    @staticmethod
    def batch_get_movie_lite(mid_list, thread, out_signal, exist=None):
        if exist is None:
            exist = {}
        with Pool() as pool:
            results = pool.imap(get_javbus_series, mid_list)
            pool.close()
            end_count = 0
            first = True
            for result in results:
                if thread.isInterruptionRequested():
                    pool.terminate()
                    break

                if result:
                    m = result[0]
                    end_count = 0
                    first = False
                    if not result[1]:
                        m['title'] = movie_name_fix(m['title'])
                        MovieCacheLite.put(m)
                    if m['mid'][-3:] in exist.keys():
                        out_signal.emit(m, result[2], exist[m['mid'][-3:]])
                    else:
                        out_signal.emit(m, result[2], "")
                    time.sleep(0.0001)
                else:
                    if not first:
                        end_count += 1
                        if end_count > 15:
                            pool.terminate()
                            break
            pool.join()
            time.sleep(0.1)
