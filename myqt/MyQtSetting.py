from PySide6.QtCore import QSettings, Signal, Qt, Slot
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit

from myqt.MyQtCommon import MyHBox, MyButton


class MySetting(QSettings):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def valueInt(self, *args, **kwargs):
        return int(self.value(*args, **kwargs))

    def valueFloat(self, *args, **kwargs):
        return float(self.value(*args, **kwargs))

    def valueStr(self, *args, **kwargs):
        return str(self.value(*args, **kwargs))


class SettingDialog(QDialog):
    changed = Signal()

    def __init__(self, parent, settings: MySetting, *groups):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)

        layout = QVBoxLayout()

        self.groups = groups
        self.key_lists = {}
        self.val_lists = {}

        for g in self.groups:
            txt_title = QLineEdit(self)
            txt_title.setText(g.upper())
            txt_title.setReadOnly(True)
            layout.addWidget(txt_title)

            self.val_lists[g] = []

            settings.beginGroup(g)
            self.key_lists[g] = settings.childKeys()

            for k in self.key_lists[g]:
                txt_key = QLineEdit(self)
                txt_key.setText(k)
                txt_key.setReadOnly(True)
                txt_val = QLineEdit(self)
                txt_val.setText(str(settings.value(k)))
                txt_val.setMinimumWidth(400)
                self.val_lists[g].append(txt_val)

                h_box = MyHBox().addAll(txt_key, txt_val)
                layout.addLayout(h_box)

            settings.endGroup()

        self.but_ok = MyButton("Apply", self.save_settings)
        self.but_cancel = MyButton("Cancel", self.reject)

        layout.addWidget(self.but_ok)
        layout.addWidget(self.but_cancel)
        self.setLayout(layout)

    @Slot()
    def save_settings(self):
        for g in self.groups:
            self.settings.beginGroup(g)
            for i, k in enumerate(self.key_lists[g]):
                self.settings.setValue(k, self.val_lists[g][i].text())
            self.settings.endGroup()

        self.changed.emit()
        self.accept()
