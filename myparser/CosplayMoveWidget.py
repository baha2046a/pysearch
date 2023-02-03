import os
import shutil
from typing import AnyStr

from PySide6.QtCore import Signal, Slot, QThread
from PySide6.QtWidgets import QWidget, QLineEdit

from FileCopyProgress import CopyProgress
from MyCommon import list_dir, chunks, join_path
from myqt.MyQtCommon import QtVBox, MyButton, QtHBox
from myqt.MyQtWorker import MyThread


class CosplayMoveWidget(QWidget):
    on_move = Signal(str, bool)
    progress = Signal(str)

    def __init__(self, parent, cos_root: str, path: str, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        folder_list = list_dir(cos_root, "*/")
        # print(path, folder_list)

        self.current_path = path
        self.target_path = ""
        self.goto = True

        self.move_list = []
        rows = chunks(folder_list, 3)
        for row in rows:
            row_box = QtHBox()
            for folder in row:
                link = folder.replace("\\", "/")
                name = os.path.basename(os.path.dirname(link))
                txt = QLineEdit(name)
                txt.setMinimumWidth(100)
                but = MyButton("Move", self.action_move, param=[link, False])
                row_box.add(QtHBox().addAll(txt, but))
            # but2 = MyButton("Move And Show", self.action_move, (u, True))
            self.move_list.append(row_box)

        self.txt_progress = QLineEdit()
        self.txt_progress.setReadOnly(True)

        self.layout = QtVBox().addAll(*self.move_list)
        self.progress.connect(self.show_progress)

        self.setLayout(self.layout)
        self.setFixedWidth(1100)

    def move_folder(self, prefer_path, txt_out: Signal, thread: QThread):
        print("Move")
        sub = 1
        try_path = prefer_path
        while os.path.exists(try_path):
            try_path = f"{prefer_path} ({sub})"
            sub += 1

        same_fs = os.stat(os.path.dirname(try_path)).st_dev == os.stat(self.current_path).st_dev

        if not same_fs and txt_out:
            CopyProgress(self.current_path, try_path, txt_out)
            shutil.rmtree(self.current_path)
        else:
            shutil.move(self.current_path, try_path)
        self.target_path = try_path

    @Slot()
    def action_move(self, folder: AnyStr, goto: bool) -> None:
        self.target_path = join_path(folder, os.path.basename(self.current_path))
        self.goto = goto
        self.layout.add(self.txt_progress)

        thread = MyThread("move_image")
        thread.set_run(self.move_folder, self.target_path, self.progress)
        thread.on_finish(on_finish=self.finish)
        thread.start()

    @Slot()
    def show_progress(self, txt):
        self.txt_progress.setText(txt)

    def finish(self):
        self.on_move.emit(os.path.dirname(self.target_path), self.goto)
