import json
import shutil
from typing import AnyStr, Optional

import jsons
from PySide6.QtCore import Signal, Slot

from MyCommon import chunks
from myqt.MyQtCommon import QtVBox, QtHBox, MyButton


class RenameHint(QtVBox):
    data = {}
    hint_out = Signal(str)
    path = "./cosplay_map.json"

    def __init__(self, hint_list: Optional[dict], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.index_box = QtVBox()
        self.data_box = QtVBox()
        self.data_box.setContentsMargins(0, 14, 0, 0)
        if hint_list is not None:
            RenameHint.data = hint_list
        else:
            RenameHint.load()

        self.selected = ""

        self.add(MyButton("Reload", self.refresh))
        self.add(self.index_box)
        self.add(self.data_box)

        self.refresh()

    def refresh(self):
        idx_list = [k for k in RenameHint.data.keys()]
        RenameHint.set_data(idx_list, self.index_box, self.index_click, 7, None)
        self.data_box.clear()

    @staticmethod
    def add_path(k: str, v: str):
        if k in RenameHint.data.keys():
            if v not in RenameHint.data[k]:
                RenameHint.data[k].append(v)
        else:
            RenameHint.data[k] = [v]

    @staticmethod
    def set_data(data_list: list, box: QtVBox, on_click, row_count: int, on_remove=None):
        box.clear()
        if data_list:
            hint_rows = chunks(data_list, row_count)
            for hints in hint_rows:
                row = QtHBox()
                for h in hints:
                    but_hint = MyButton(h, on_click, [h])
                    row.add(but_hint)
                    if on_remove is not None:
                        but_remove = MyButton("X", on_remove, [h])
                        but_remove.setFixedWidth(40)
                        row.add(but_remove)
                box.add(row)

    @staticmethod
    def _load(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(e)
            return {}

    @staticmethod
    def _save(path: AnyStr, data) -> None:
        tmp_path = path + "_tmp"
        try:
            d = jsons.dump(data)
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False, indent=4)
            shutil.move(tmp_path, path)
        except Exception as e:
            print(e)
        finally:
            f.close()

    @staticmethod
    def load() -> None:
        RenameHint.data = RenameHint._load(RenameHint.path)
        print(RenameHint.data)

    @staticmethod
    def save() -> None:
        RenameHint._save(RenameHint.path, RenameHint.data)

    def index_click(self, idx: str):
        dt = [idx]
        dt.extend(self.data[idx].copy())

        self.selected = idx
        RenameHint.set_data(dt, self.data_box, self.hint, 7, self.remove)

    @Slot()
    def hint(self, name: str):
        self.hint_out.emit(f"{name}")

    @Slot()
    def remove(self, name: str):
        if self.selected == name:
            if self.selected in RenameHint.data.keys():
                if len(RenameHint.data[self.selected]) == 0:
                    RenameHint.data.pop(name)
                    self.refresh()
        else:
            if self.selected in RenameHint.data.keys():
                RenameHint.data[self.selected].remove(name)
                self.refresh()
