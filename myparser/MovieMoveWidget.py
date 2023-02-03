import os

from PySide6.QtCore import *
from PySide6.QtWidgets import QWidget, QLineEdit

from MyCommon import join_path
from myparser.InfoMovie import InfoMovie, InfoMaker
from myqt.EditDict import EditDictDialog
from myqt.MyQtCommon import QtVBox, MyButton, QtHBox
from myqt.MyQtWorker import MyThreadPool


class MovieMoveWidget(QWidget):
    on_move = Signal(str)
    progress = Signal(str)
    can_remove = Signal(bool)

    def __init__(self, parent, movie: InfoMovie, movie_base: str, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.movie = movie
        self.movie_base = movie_base
        self.maker_path = join_path(movie_base, f"({InfoMaker.dir(movie.maker)})")
        self.m_m = QLineEdit(self.maker_path)
        self.m_t = QLineEdit()
        self.txt_progress = QLineEdit()
        self.txt_progress.setReadOnly(True)
        exist = os.path.exists(self.maker_path)
        self.but_move = MyButton("Move", self.move)

        self.layout = QtVBox()

        if exist:
            self.layout.add(self.m_m)
            self.step_two()
        else:
            self.but_mapping = MyButton("Map", self.edit_mapping)
            self.but_create = MyButton("Create", self.create)
            self.layout.add(QtHBox().addAll(self.m_m, self.but_mapping, self.but_create))

        self.progress.connect(self.show_progress)

        self.setLayout(self.layout)
        self.setFixedWidth(800)

    @Slot()
    def edit_mapping(self):
        dial = EditDictDialog(InfoMaker.mod_dir, self.movie.maker)
        if dial.exec():
            InfoMaker.mod_dir = dial.get_result()
            InfoMaker.save()
            self.maker_path = join_path(self.movie_base, f"({InfoMaker.dir(self.movie.maker)})")
            self.m_m.setText(self.maker_path)
            if os.path.exists(self.maker_path):
                self.but_mapping.setEnabled(False)
                self.but_create.setEnabled(False)
                self.step_two()

    def step_two(self):
        new_path = join_path(self.maker_path, os.path.basename(self.movie.path))
        self.m_t.setText(new_path)
        if new_path == self.movie.path:
            self.m_t.setText("Already Located in Prefer Path")
            self.but_move.setEnabled(False)
        self.layout.add(QtHBox().addAll(self.m_t, self.but_move))

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
        self.can_remove.emit(False)

        MyThreadPool.start("move_movie", None, self.finish, self.finish,
                           self.movie.move, path, self.progress, pending_when_exist=False)

    @Slot()
    def show_progress(self, txt):
        self.txt_progress.setText(txt)

    def finish(self):
        self.can_remove.emit(True)
        self.on_move.emit(self.m_t.text())
