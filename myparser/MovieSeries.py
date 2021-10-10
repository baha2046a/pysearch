import os
import re
import time
from multiprocessing import Pool

from PySide6.QtCore import QStringListModel, Slot, Signal
from PySide6.QtWidgets import QWidget, QListView, QAbstractItemView

from myparser.JavBusMain import get_javbus_series
from myparser.MovieCache import MovieCache
from myparser.MovieNameFix import movie_name_fix
from myqt.MyQtCommon import MyVBox, MyButton
from myqt.MyQtImage import MyImageSource
from myqt.MyQtWorker import MyThread


class PathSeriesWidget(QWidget):
    output = Signal(dict, MyImageSource, bool)

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
                    self.s_list[m1].append(m2)
                else:
                    self.s_list[m1] = [m2]

        self.view = QListView()
        self.model = QStringListModel(self)
        self.view.setModel(self.model)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.clicked.connect(self.action_list_click)

        self.model.setStringList(sorted(self.s_list.keys()))

        self.b_search = MyButton("Search", self.action_show_series)

        layout = MyVBox().addAll(self.view, self.b_search)
        self.setLayout(layout)

    @Slot()
    def action_list_click(self, index):
        self.selected = index.data()

    @Slot()
    def action_show_series(self):
        thread = MyThread("get_series")
        thread.set_run(self.loop_get_data2)
        thread.start()
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            cors = [get_javbus_series(f"{self.selected}-{str(i).zfill(3)}") for i in range(1000)]
            f = {executor.submit(get_javbus_series, mid): mid for mid in cors}
        """

    def loop_get_data2(self, thread):
        if self.selected:
            exist = self.s_list[self.selected]
            with Pool() as pool:
                mid_list = [f"{self.selected}-{str(i).zfill(3)}" for i in range(1000)]
                m_data = pool.imap(get_javbus_series, mid_list)
                pool.close()
                end_count = 0
                first = True
                for m in m_data:
                    if m:
                        end_count = 0
                        first = False
                        m['title'] = movie_name_fix(m['title'])
                        MovieCache.put(m)
                        is_local = m['mid'][-3:] in exist
                        self.output.emit(m, MyImageSource(m['cover']), is_local)
                        time.sleep(0.001)
                    else:
                        if not first:
                            end_count += 1
                            if end_count > 15:
                                pool.terminate()
                                break
                pool.join()
                time.sleep(1)

    def loop_get_data(self, thread):
        if self.selected:
            with Pool() as pool:
                for loop in range(1, 1000, 10):
                    mid_list = [f"{self.selected}-{str(i).zfill(3)}" for i in range(loop, loop + 10)]
                    m_data = pool.imap(get_javbus_series, mid_list)

                    if thread.isInterruptionRequested():
                        return None

                    for m in m_data:
                        if m:
                            self.output.emit(m)
                            time.sleep(0.1)
