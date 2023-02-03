from PySide6.QtCore import QSettings, Signal, Qt, Slot
from PySide6.QtWidgets import QLineEdit

from myqt.MyQtCommon import QtHBox, MyButton, QtVBox, QtDialog


class MySetting(QSettings):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def valueInt(self, *args, **kwargs) -> int:
        return int(self.value(*args, **kwargs))

    def valueFloat(self, *args, **kwargs) -> float:
        return float(self.value(*args, **kwargs))

    def valueStr(self, *args, **kwargs) -> str:
        return str(self.value(*args, **kwargs))


class SettingDialog(QtDialog):
    changed = Signal()
    FILTER = ["splitterSizes"]

    def __init__(self, parent, settings: MySetting, *groups):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)

        layout = QtVBox()

        self.groups = groups
        self.key_lists = {}
        self.val_lists = {}

        for g in self.groups:
            txt_title = QLineEdit(g.upper())
            txt_title.setReadOnly(True)
            layout.add(txt_title)

            self.val_lists[g] = []

            settings.beginGroup(g)
            self.key_lists[g] = settings.childKeys()

            for k in self.key_lists[g]:
                if k not in SettingDialog.FILTER:
                    txt_key = QLineEdit(k)
                    txt_key.setReadOnly(True)
                    txt_val = QLineEdit(str(settings.value(k)))
                    txt_val.setMinimumWidth(400)
                    self.val_lists[g].append(txt_val)

                    h_box = QtHBox().addAll(txt_key, txt_val)
                    layout.add(h_box)

            settings.endGroup()

        self.but_ok = MyButton(self._icon_ok(), self.save_settings)

        layout.addAll(self._bar_ok_cancel(self.but_ok))
        self.setLayout(layout)

    @Slot()
    def save_settings(self):
        for g in self.groups:
            self.settings.beginGroup(g)
            i = 0
            for k in self.key_lists[g]:
                if k not in SettingDialog.FILTER:
                    self.settings.setValue(k, self.val_lists[g][i].text())
                    i += 1
            self.settings.endGroup()

        self.changed.emit()
        self.accept()


