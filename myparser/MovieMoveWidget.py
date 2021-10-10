import os
import shutil

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QWidget, QLineEdit

from myparser.InfoMovie import InfoMovie, InfoMaker
from myqt.MyQtCommon import MyVBox, MyButton, MyHBox
from myqt.MyQtSetting import EditDictDialog
from myqt.MyQtWorker import MyThread


class MovieMoveWidget(QWidget):
    on_move = Signal(str)
    progress = Signal(str)

    def __init__(self, movie: InfoMovie, movie_base: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.movie = movie
        self.movie_base = movie_base
        self.maker_path = os.path.join(movie_base, f"({InfoMaker.dir(movie.maker)})").replace("\\", "/")
        self.m_m = QLineEdit(self.maker_path)
        self.m_t = QLineEdit()
        self.txt_progress = QLineEdit()
        self.txt_progress.setReadOnly(True)
        exist = os.path.exists(self.maker_path)
        self.but_move = MyButton("Move", self.move)

        self.layout = MyVBox()

        if exist:
            self.layout.add(self.m_m)
            self.step_two()
        else:
            self.but_mapping = MyButton("Map", self.edit_mapping)
            self.but_create = MyButton("Create", self.create)
            self.layout.add(MyHBox().addAll(self.m_m, self.but_mapping, self.but_create))

        self.progress.connect(self.show_progress)

        self.setLayout(self.layout)
        self.setFixedWidth(800)

    @Slot()
    def edit_mapping(self):
        dial = EditDictDialog(InfoMaker.mod_dir, self.movie.maker)
        if dial.exec():
            InfoMaker.mod_dir = dial.get_result()
            self.maker_path = os.path.join(self.movie_base, f"({InfoMaker.dir(self.movie.maker)})") \
                .replace("\\", "/")
            self.m_m.setText(self.maker_path)
            if os.path.exists(self.maker_path):
                self.but_mapping.setEnabled(False)
                self.but_create.setEnabled(False)
                self.step_two()

    def step_two(self):
        new_path = os.path.join(self.maker_path, os.path.basename(self.movie.path)).replace("\\", "/")
        self.m_t.setText(new_path)
        if new_path == self.movie.path:
            self.m_t.setText("Already Located in Prefer Path")
            self.but_move.setEnabled(False)
        self.layout.add(MyHBox().addAll(self.m_t, self.but_move))

    @Slot()
    def create(self):
        self.but_create.setEnabled(False)
        self.maker_path = self.m_m.text()
        os.mkdir(self.maker_path)
        self.step_two()

    @Slot()
    def move(self):
        self.m_t.setReadOnly(True)
        path = self.m_t.text()
        self.but_move.setEnabled(False)
        self.layout.add(self.txt_progress)

        thread = MyThread("move_movie")
        thread.set_run(self.movie.move, path, self.progress)
        thread.on_finish(on_finish=self.finish)
        thread.start()

    @Slot()
    def show_progress(self, txt):
        self.txt_progress.setText(txt)

    def finish(self):
        self.on_move.emit(self.m_t.text())
