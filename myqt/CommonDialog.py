import os
import shutil
import time
from typing import Tuple, AnyStr

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QDialog, QLineEdit

from MyCommon import list_jpg, valid_folder_name, join_path
from TextOut import TextOut
from myparser.MovieWidget import RenameHint
from myqt.MyQtCommon import MyVBox, MyButton, MyHBox, MyPasteEdit
from myqt.MyQtWorker import MyThread
from zhtools.langconv import Converter


class RenameImageDialog(QDialog):
    def __init__(self, folder: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.folder = folder
        self.file_list = sorted(list_jpg(folder))
        self.b_reorder = MyButton("Reorder", self.async_reorder)
        self.t_to = QLineEdit("1")
        self.b_rename = MyButton("Rename", self.async_rename)
        self.b_cancel = MyButton("Close", self.reject)
        self.v_box = MyVBox().addAll(self.b_reorder, self.t_to, self.b_rename, self.b_cancel)
        layout = self.v_box
        self.setLayout(layout)
        self.setWindowTitle("Rename")

    @Slot()
    def async_rename(self):
        run_thread = MyThread("rename-dialog")
        run_thread.set_run(self.rename)
        run_thread.start()
        self.accept()

    @Slot()
    def async_reorder(self):
        run_thread = MyThread("rename-dialog")
        run_thread.set_run(self.reorder)
        run_thread.start()
        self.accept()

    def reorder(self, thread):
        num = 0
        for f in self.file_list:
            target_name = '{}/{:04}.jpg'.format(self.folder, num)
            if os.path.basename(f) != "folder.jpg" and f.replace("\\", "/") != target_name:
                TextOut.out(target_name)
                shutil.move(f, os.path.join(self.folder, target_name))
            num += 1
            if thread.isInterruptionRequested():
                break

    def rename(self, thread):
        use = self.t_to.text()
        for f in self.file_list:
            file_name = os.path.basename(f)
            target_name = f"{use}{file_name[1:]}"
            if file_name != "folder.jpg" and file_name != target_name:
                TextOut.out(target_name)
                shutil.move(f, os.path.join(self.folder, target_name))
            if thread.isInterruptionRequested():
                break


class DeleteConfirmDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.b_ok = MyButton("Ok", self.accept)
        self.b_cancel = MyButton("Cancel", self.reject)
        self.v_box = MyVBox().addAll(self.b_ok, self.b_cancel)
        layout = self.v_box
        self.setLayout(layout)
        self.setWindowTitle("Confirm")


class RenameDialog(QDialog):
    def __init__(self, path_current: str, path_target: str = "",
                 hint_box: RenameHint = None, lang_convert_list=None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.t_dir = QLineEdit()
        self.t_dir.setReadOnly(True)
        self.t_o = QLineEdit()
        self.t_n = MyPasteEdit()
        self.t_o.setReadOnly(True)
        self.lang_convert_list = lang_convert_list or []
        self.old_path = path_current

        self.set(path_current, path_target)

        if hint_box is not None:
            hint_box.hint_out.connect(self.hint)
        else:
            hint_box = MyVBox()

        self.b_ok = MyButton("Apply", self.accept)
        self.b_cancel = MyButton("Cancel", self.reject)
        b_zh = MyButton("JP>ZH", self.jp_zh)
        b_jp = MyButton("ZH>JP", self.zh_jp)
        b_han = MyButton("SIM>ZH", self.sim_han)
        self.v_box = MyVBox().addAll(hint_box, self.t_dir, self.t_o, self.t_n,
                                     MyHBox().addAll(b_zh, b_jp, b_han),
                                     MyHBox().addAll(self.b_ok, self.b_cancel))
        layout = self.v_box
        self.setLayout(layout)
        self.setWindowTitle("Rename")
        self.resize(600, 200)

    def create_mode(self):
        self.t_dir.setText(self.old_path)
        self.t_o.setText("")
        self.t_n.setText("")
        self.old_path = ""
        self.setWindowTitle("Create Folder")
        return self

    def do_create_rename(self) -> Tuple[AnyStr, AnyStr]:
        if self.t_n.text() == "" or self.t_n.text() == self.t_o.text():
            return self.old_path, ""
        return RenameDialog.create_rename(self.t_dir.text(), self.old_path, self.t_n.text())

    @staticmethod
    def valid_path(in_txt: AnyStr) -> AnyStr:
        return valid_folder_name(in_txt.strip().strip('\n'))

    @staticmethod
    def create_rename(dir_path: AnyStr, old_path: AnyStr, target: AnyStr) -> Tuple[AnyStr, AnyStr]:
        target = RenameDialog.valid_path(target)

        out_path = join_path(dir_path, target)

        if old_path == "" or old_path is None:
            os.makedirs(out_path, exist_ok=True)
        else:
            while os.path.exists(out_path):
                out_path = os.path.join(dir_path, target + "_1").replace("\\", "/")
            shutil.move(old_path, out_path)
        time.sleep(0.1)
        return out_path, target

    def jp_zh(self):
        txt = self.t_n.text()
        for row in self.lang_convert_list:
            txt = txt.replace(row[0], row[1])
            if row[2] is not None:
                txt = txt.replace(row[2], row[1])
        self.t_n.setText(txt)

    def zh_jp(self):
        txt = self.t_n.text()
        for row in self.lang_convert_list:
            txt = txt.replace(row[1], row[0])
        self.t_n.setText(txt)

    def sim_han(self):
        txt = self.t_n.text()
        txt = Converter("zh-hant").convert(txt)
        self.t_n.setText(txt)

    def set(self, path_current: str, path_target: str = ""):
        self.old_path = path_current
        self.t_dir.setText(os.path.dirname(path_current))
        self.t_o.setText(os.path.basename(path_current))
        if path_target == "":
            self.t_n.setText(os.path.basename(path_current))
        else:
            self.t_n.setText(os.path.basename(path_target))

    def hint(self, text):
        self.t_n.setText(f"{text} {self.t_n.text().strip()}")
