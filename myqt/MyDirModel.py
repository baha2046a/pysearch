import glob
import os
import shutil
import subprocess
import time
from typing import Any, AnyStr, Optional, Tuple

from PySide6.QtCore import *
from PySide6.QtWidgets import QListView, QStyle, QApplication

from MyCommon import join_path, list_dir
from myqt.CommonDialog import DeleteConfirmDialog, RenameDialog
from myqt.MyQtCommon import MyButton, MyHBox


class MyDirModel(QStringListModel):
    folder_icon = None
    file_icon = None
    lock_dir: set[AnyStr] = set()

    signal_change_select = Signal(str)
    signal_clicked = Signal(str, str, QModelIndex)
    signal_double_clicked = Signal(str, str, QModelIndex)
    signal_root_changed = Signal(str, name="root_changed")

    @staticmethod
    def list_dir_as_name(folder: AnyStr) -> list:
        return list(map(MyDirModel.name_from_path, list_dir(folder)))

    @staticmethod
    def name_from_path(full_path: AnyStr) -> AnyStr:
        return os.path.split(full_path)[1]

    def __init__(self, hint=None, lang_convert_list=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rootPath = None
        self.select = None
        self.rename_dialog = None
        self.hint = hint
        self.lang_convert_list = lang_convert_list
        self.last_record = {}

        self.view = QListView()
        self.view.setModel(self)
        self.view.clicked.connect(self.list_clicked)
        self.view.doubleClicked.connect(self.list_double_clicked)

        self.but_explorer = MyButton('🗂', self.action_explorer, large_text=True)
        self.but_up = MyButton("🔝", self.action_up, large_text=True)
        self.but_delete = MyButton("🗑", self.action_delete, large_text=True)
        self.but_rename = MyButton("🖊", self.action_rename, large_text=True)
        self.but_create = MyButton("📂", self.action_create, large_text=True)

        self.tool_bar = MyHBox().addAll(self.but_explorer,
                                        self.but_up, self.but_delete, self.but_rename, self.but_create)

    @Slot()
    def action_explorer(self):
        if self.select is not None:
            if os.path.isdir(self.select):
                subprocess.Popen('explorer {}'.format(self.select.replace('/', '\\')))
            else:
                subprocess.Popen('explorer {}'.format(self.rootPath.replace('/', '\\')))

    def action_up(self):
        self.last_record[self.rootPath] = self.select
        out_path = os.path.dirname(self.rootPath)
        self.setRootPath(out_path)
        self.makeSelect(None)

    def action_delete(self):
        if self.select is not None:
            if DeleteConfirmDialog().exec():
                if os.path.isdir(self.select):
                    shutil.rmtree(self.select)
                else:
                    os.remove(self.select)
                self.setRootPath(self.rootPath)
                self.makeSelect(None)

    def action_rename(self):
        if self.select is not None:
            if self.rename_dialog is None:
                self.rename_dialog = RenameDialog(self.select, self.select,
                                                  self.hint, self.lang_convert_list)
            else:
                self.rename_dialog.set(self.select, self.select)

            if self.rename_dialog.exec():
                out_path, out = self.rename_dialog.do_create_rename()
                self.makeSelect(out_path, reload=True)

    def action_create(self):
        if self.rootPath is not None:
            if self.rename_dialog is None:
                self.rename_dialog = RenameDialog(self.rootPath, "",
                                                  self.hint, self.lang_convert_list)
            else:
                self.rename_dialog.set(self.rootPath, "")
            self.rename_dialog.create_mode()
            if self.rename_dialog.exec():
                out_path, out = self.rename_dialog.do_create_rename()
                self.makeSelect(out_path, reload=True)

    def list_clicked(self, index: QModelIndex) -> None:
        path = join_path(self.rootPath, index.data())
        self.select = path
        not_locked = path not in MyDirModel.lock_dir
        self.but_rename.setEnabled(not_locked)
        self.but_delete.setEnabled(not_locked)
        self.signal_clicked.emit(path, self.rootPath, index)

    def lock_folder(self, folder: AnyStr) -> None:
        MyDirModel.lock_dir.add(folder)
        if folder == self.select:
            self.but_rename.setEnabled(False)
            self.but_delete.setEnabled(False)

    def unlock_folder(self, folder: AnyStr) -> None:
        if folder in MyDirModel.lock_dir:
            MyDirModel.lock_dir.remove(folder)
        if folder == self.select:
            self.but_rename.setEnabled(True)
            self.but_delete.setEnabled(True)

    def list_double_clicked(self, index: QModelIndex) -> None:
        path = join_path(self.rootPath, index.data())

        if os.path.isdir(path):
            self.last_record[self.rootPath] = path
            self.setRootPath(path)
            self.makeSelect(None)
        else:
            self.signal_double_clicked.emit(path, self.rootPath, index)

    def setRootPath(self, path=None):
        if path is None:
            path = self.rootPath
        else:
            self.rootPath = path
        self.setStringList(MyDirModel.list_dir_as_name(path))
        time.sleep(0.1)
        self.signal_root_changed.emit(path)

    def change_and_select(self, new_path):
        self.signal_change_select.emit(new_path)

    def mkdir(self, name: AnyStr) -> Tuple[AnyStr, AnyStr]:
        out_path, out = RenameDialog.create_rename(self.rootPath, "", name)
        self.makeSelect(out_path, reload=True)
        return out_path, out

    def makeSelect(self, path: Optional[AnyStr] = None, reload: bool = False) -> Optional[QModelIndex]:
        self.select = path

        if path is None:
            if self.rootPath in self.last_record.keys():
                path = self.last_record[self.rootPath]

        if path is None:
            self.signal_clicked.emit(None, self.rootPath, None)
            return None

        name = os.path.basename(path)
        root = os.path.dirname(path)
        if root != self.rootPath or reload:
            self.setRootPath(root)

        match = self.match(self.index(0, 0), Qt.DisplayRole, name, 1, Qt.MatchExactly)
        if len(match) > 0:
            if self.view:
                self.view.setCurrentIndex(match[0])
            self.signal_clicked.emit(path, self.rootPath, match[0])
            return match[0]
        else:
            return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole, *args, **kwargs):
        if role == Qt.DecorationRole:
            filename = super().data(index, Qt.DisplayRole)
            full = os.path.join(self.rootPath, filename)
            if not os.path.isdir(full):
                if not MyDirModel.file_icon:
                    MyDirModel.file_icon = QApplication.style().standardIcon(QStyle.SP_FileIcon)
                return MyDirModel.file_icon
            else:
                if not MyDirModel.folder_icon:
                    MyDirModel.folder_icon = QApplication.style().standardIcon(QStyle.SP_DirIcon)
                return MyDirModel.folder_icon  # QtGui.QColor('green') SP_FileIcon
        else:
            return super().data(index, role)
