from PySide6.QtCore import Slot
from PySide6.QtWidgets import QDialog, QLineEdit

from myparser.ParserCommon import get_soup
from myqt.MyQtCommon import MyButton, MyVBox, MyPasteEdit
from myparser import check
from myqt.MyQtSetting import MySetting


class CreateRecordDialog(QDialog):
    def __init__(self, parent, settings: MySetting, name=None, url=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.settings = settings
        self.setWindowTitle("Create")
        self.p1 = None
        self.p2 = None

        self.txt_name = MyPasteEdit()
        self.txt_url = QLineEdit()
        if name:
            self.txt_name.setText(name)
            self.setWindowTitle("Modify")
        if url:
            self.txt_url.setText(url)

        self.but_check = MyButton("Check", self.action_check)
        self.but_check_b = MyButton("As BitGirl", self.action_check_b)
        self.but_check_c = MyButton("As Cosppi", self.action_check_c)

        self.but_ok = MyButton("Process", self.accept)
        self.but_cancel = MyButton("Cancel", self.reject)

        self.but_check_b.setEnabled(False)
        self.but_check_c.setEnabled(False)

        layout = MyVBox().addAll(self.txt_name,
                                 self.but_check,
                                 self.but_check_b,
                                 self.but_check_c,
                                 self.txt_url,
                                 self.but_ok,
                                 self.but_cancel)
        self.setLayout(layout)
        self.setMinimumWidth(400)

    def get_name(self):
        return self.txt_name.text().replace("のTwitter", "").replace("「", "").replace("」", "")

    @Slot()
    def action_check(self):
        name = self.get_name()
        if name:
            self.txt_name.setText(name)
            url_id = name.split("@")[-1].replace(")", "").lower()

            self.p1 = f"{self.settings.value('bitgirl/url1')}{url_id}"
            self.p2 = f"{self.settings.value('bitgirl/url2')}{url_id}"

            soup1 = get_soup(self.p1)
            self.but_check_b.setEnabled(check(soup1))
            soup2 = get_soup(self.p2)
            self.but_check_c.setEnabled(check(soup2))

    @Slot()
    def action_check_c(self):
        self.txt_url.setText(self.p2)
        # https://cosppi.net/user/sumisora_mafuri

    @Slot()
    def action_check_b(self):
        self.txt_url.setText(self.p1)
        # https://bi-girl.net/2011pingping