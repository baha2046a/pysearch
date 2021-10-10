from PySide6.QtCore import QSettings, Signal, Qt, Slot
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit

from myqt.MyQtCommon import MyHBox, MyButton, MyVBox


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
    FILTER = ["splitterSizes"]

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
                if k not in SettingDialog.FILTER:
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
            i = 0
            for k in self.key_lists[g]:
                if k not in SettingDialog.FILTER:
                    self.settings.setValue(k, self.val_lists[g][i].text())
                    i += 1
            self.settings.endGroup()

        self.changed.emit()
        self.accept()


class EditDictDialog(QDialog):
    def __init__(self, in_dict, add=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = MyVBox()
        self.k_list = []
        self.v_list = []
        for k in in_dict:
            self.layout.add(self.get_row(k, in_dict[k]))
        self.but_new_row = MyButton("Add", self.new_row)
        self.b_ok = MyButton("Apply", self.accept)
        self.b_cancel = MyButton("Cancel", self.reject)
        self.layout.addAll(self.but_new_row, self.b_ok, self.b_cancel)
        if add:
            self.new_row(add)
        self.setLayout(self.layout)
        self.resize(800, 200)

    @Slot()
    def new_row(self, key=""):
        self.layout.add(self.get_row(key, ""))

    def get_row(self, i, j):
        k = QLineEdit(i)
        v = QLineEdit(j)
        self.k_list.append(k)
        self.v_list.append(v)
        return MyHBox().addAll(k, v)

    def get_result(self):
        r = {}
        for v, k in enumerate(self.k_list):
            key: str = k.text()
            val: str = self.v_list[v].text()
            if key and val:
                r[key] = val
        print(r)
        return r







