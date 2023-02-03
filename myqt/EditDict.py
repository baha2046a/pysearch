from PySide6.QtCore import Slot
from PySide6.QtWidgets import QLineEdit

from myqt.MyQtCommon import QtVBox, MyButton, fa_icon, QtHBox, QtDialog
from myqt.MyQtFlow import MyQtScrollableFlow


class EditDictDialog(QtDialog):
    def __init__(self, in_dict: dict, add=None, sort=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dict_edit = QtVBox()
        self.k_list = []
        self.v_list = []

        if sort:
            keys = sorted(in_dict.keys())
        else:
            keys = in_dict.keys()

        for k in keys:
            self.dict_edit.add(self.get_row(k, in_dict[k]))

        w = self.dict_edit.toWidget()
        w.setMinimumWidth(770)
        flow = MyQtScrollableFlow()
        flow.addWidget(w)

        self.but_new_row = MyButton(fa_icon("ri.add-box-line"), self.new_row)

        if add:
            self.new_row(add)

        layout = QtVBox().addAll(flow, self.but_new_row, self._bar_ok_cancel())
        self.setLayout(layout)
        self.resize(800, 700)
        self.setWindowTitle("Edit")

    @Slot()
    def new_row(self, key: str = "", checked: bool = False):
        print(key)
        self.dict_edit.add(self.get_row(key, ""))

    def get_row(self, i: str, j: str):
        print(i, j)
        k = QLineEdit(i)
        v = QLineEdit(j)
        self.k_list.append(k)
        self.v_list.append(v)
        return QtHBox().addAll(k, v)

    def get_result(self):
        r = {}
        for v, k in enumerate(self.k_list):
            key: str = k.text()
            val: str = self.v_list[v].text()  # .lstrip("(").rstrip(")")
            if len(val) > 2 and val.startswith("("):
                val = val[1:-1]
            if key and val:
                r[key] = val
        print(r)
        return r
