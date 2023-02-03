import os
import shutil
import subprocess
import time
from typing import AnyStr, Optional, Tuple

from PySide6.QtCore import *
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import QListView, QStyle, QApplication

from MyCommon import join_path, list_dir
from myqt.CommonDialog import DeleteConfirmDialog, RenameDialog
from myqt.EditDict import EditDictDialog
from myqt.MyQtCommon import MyButton, QtHBox, fa_icon


class MyDirModel(QStringListModel):
    folder_icon = None
    file_icon = None
    lock_dir: set[AnyStr] = set()
    short_cut_path = ""

    lst_icon = []
    lst_color = []

    signal_change_select = Signal(str)
    signal_clicked = Signal(str, str, QModelIndex)
    signal_double_clicked = Signal(str, str, QModelIndex)
    signal_root_changed = Signal(str, name="root_changed")

    @staticmethod
    def list_dir_as_name(folder: AnyStr) -> list:
        return sorted(list(map(MyDirModel.name_from_path, list_dir(folder))))

    @staticmethod
    def name_from_path(full_path: AnyStr) -> AnyStr:
        return os.path.split(full_path)[1]

    def __init__(self, hint=None, lang_convert_list=None, shortcut=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if shortcut is None:
            shortcut = {}
        self.shortcut = shortcut
        self.rootPath = None
        self.select = None
        self.rename_dialog = None
        self.filtered = False
        self.hint = hint
        self.lang_convert_list = lang_convert_list
        self.last_record = {}

        self.view = QListView()
        self.view.setModel(self)
        self.view.setUniformItemSizes(True)
        self.view.clicked.connect(self.list_clicked)
        self.view.doubleClicked.connect(self.list_double_clicked)

        self.but_explorer = MyButton(fa_icon("ph.folder-open-fill"), self.action_explorer)
        self.but_up = MyButton(fa_icon("ri.folder-upload-line"), self.action_up)
        self.but_refresh = MyButton(fa_icon("fa.refresh"), self.setRootPath, icon_size=24)
        self.but_delete = MyButton(fa_icon("mdi.delete-forever"), self.action_delete)
        self.but_rename = MyButton(fa_icon("mdi.rename-box"), self.action_rename)
        self.but_create = MyButton(fa_icon("ph.folder-simple-plus-fill"), self.action_create)

        self.tool_bar = QtHBox().addAll(self.but_explorer, self.but_up, self.but_refresh,
                                        self.but_delete, self.but_rename, self.but_create)

        self.shortcut_bar = QtHBox()
        self.update_shortcut()

    def update_shortcut(self):
        but_edit_shortcut = MyButton(fa_icon("ei.file-edit"), self.edit_shortcut)
        self.shortcut_bar.set(but_edit_shortcut)
        for k, v in self.shortcut.items():
            but = MyButton(k, self.change_path, [v])
            self.shortcut_bar.add(but)

    def edit_shortcut(self):
        edit = EditDictDialog(in_dict=self.shortcut)
        if edit.exec():
            self.shortcut = edit.get_result()
            self.update_shortcut()

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
                self.makeSelect(None)
                self.setRootPath(self.rootPath)

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
        # t = time.time()
        path = join_path(self.rootPath, index.data())
        if path != self.select:
            self.select = path
            not_locked = path not in MyDirModel.lock_dir
            self.but_rename.setEnabled(not_locked)
            self.but_delete.setEnabled(not_locked)
            self.signal_clicked.emit(path, self.rootPath, index)
        # print(time.time() - t)

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
            self.change_path(path)
        else:
            self.signal_double_clicked.emit(path, self.rootPath, index)

    def change_path(self, path):
        print("change_path", path)
        self.last_record[self.rootPath] = self.select
        self.setRootPath(path)
        self.makeSelect(None)

    def set_filter(self, f):
        self.filtered = True
        filtered = [path for path in MyDirModel.list_dir_as_name(self.rootPath) if path.find(f) >= 0]
        self.setStringList(filtered)
        self.makeSelect(None)

    def clear_filter(self):
        if self.filtered:
            self.setStringList(MyDirModel.list_dir_as_name(self.rootPath))
            self.makeSelect(self.select)

    def setRootPath(self, path=None):
        print("setRootPath", path)
        if path is None:
            path = self.rootPath
        else:
            self.rootPath = path
        self.filtered = False
        self.setStringList(MyDirModel.list_dir_as_name(path))
        time.sleep(0.1)
        self.signal_root_changed.emit(path)

    def change_and_select(self, new_path):
        self.signal_change_select.emit(new_path)

    def mkdir(self, name: AnyStr) -> Tuple[AnyStr, AnyStr]:
        print("self.rootPath", self.rootPath)
        out_path, out = RenameDialog.create_rename(self.rootPath, "", name)
        self.makeSelect(out_path, reload=True)
        print(out_path)
        return out_path, out

    def makeSelect(self, path: Optional[AnyStr] = None, reload: bool = False) -> Optional[int]:
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

    def setData(self, index: QModelIndex, value="", role=None, *args, **kwargs):
        result = super().setData(index, *args, **kwargs)
        print(role)
        if result and role == Qt.DisplayRole:
            full = os.path.join(self.rootPath, value)
            if not os.path.isdir(full):
                if not MyDirModel.file_icon:
                    MyDirModel.file_icon = QApplication.style().standardIcon(QStyle.SP_FileIcon)
                self.lst_icon.insert(index.row(), MyDirModel.file_icon)
            else:
                if not MyDirModel.folder_icon:
                    MyDirModel.folder_icon = QApplication.style().standardIcon(QStyle.SP_DirIcon)
                self.lst_icon.insert(index.row(), MyDirModel.folder_icon)
        return result

    def setStringList(self, strings, p_str=None):
        # color = QBrush()
        # color.setColor(QColor.fromRgb(255, 115, 0, 255))
        self.lst_icon = []
        self.lst_color = []
        for filename in strings:
            full = os.path.join(self.rootPath, filename)
            if not os.path.isdir(full):
                if not MyDirModel.file_icon:
                    MyDirModel.file_icon = QApplication.style().standardIcon(QStyle.SP_FileIcon)
                self.lst_icon.append(MyDirModel.file_icon)
            else:
                if not MyDirModel.folder_icon:
                    MyDirModel.folder_icon = QApplication.style().standardIcon(QStyle.SP_DirIcon)
                self.lst_icon.append(MyDirModel.folder_icon)
        super().setStringList(strings)

    def data(self, index: QModelIndex, role=Qt.DisplayRole, *args, **kwargs):
        if role == Qt.DecorationRole:
            return self.lst_icon[index.row()]
        else:
            return super().data(index, role)
