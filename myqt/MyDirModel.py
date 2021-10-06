import glob
import os
from typing import Any

from PySide6.QtCore import QStringListModel, Qt
from PySide6.QtWidgets import QListView, QStyle, QApplication


class MyDirModel(QStringListModel):
    folder_icon = None
    file_icon = None

    @staticmethod
    def list_dir_as_name(folder):
        return list(map(MyDirModel.name_from_path, MyDirModel.list_dir(folder)))

    @staticmethod
    def name_from_path(full_path):
        return os.path.split(full_path)[1]

    @staticmethod
    def list_dir(folder, custom=None):
        if custom:
            select = f"{folder}/{custom}".replace("[", "[[]").replace("]", "[]]")
            return glob.glob(select)
        else:
            return os.listdir(folder)

    @staticmethod
    def list_jpg(folder):
        return MyDirModel.list_dir(folder, "*.jpg")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rootPath = None

    def setRootPath(self, path):
        self.rootPath = path
        self.setStringList(MyDirModel.list_dir_as_name(path))

    def mkdir(self, path: str, view: QListView = None):
        try:
            os.mkdir(path)
        except Any:
            return None
        if self.insertRow(self.rowCount()):
            index = self.index(self.rowCount() - 1)
            self.setData(index, os.path.basename(path))
            self.sort(0)
            return self.makeSelect(path, view)
        return None

    def makeSelect(self, path: str, view: QListView = None):
        name = os.path.basename(path)
        match = self.match(self.index(0, 0), Qt.DisplayRole, name, 1, Qt.MatchExactly)
        if len(match) > 0:
            if view:
                view.setCurrentIndex(match[0])
            return match[0]
        else:
            return None

    def data(self, index, role=Qt.DisplayRole, *args, **kwargs):
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
