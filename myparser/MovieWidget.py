import os.path
import webbrowser
from typing import List

from PySide6.QtCore import Slot, Signal
from PySide6.QtWidgets import QWidget, QLineEdit, QDialog

from myparser.InfoMovie import InfoMovie, InfoKeyword, InfoActor
from myqt.MyQtCommon import MyHBox, MyVBox, MyButton
from myqt.MyQtImage import MyImageBox


class RenameDialog(QDialog):
    def __init__(self, parent, path: str, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.t_o = QLineEdit(os.path.basename(path))
        self.t_o.setReadOnly(True)
        self.t_n = QLineEdit(os.path.basename(path))

        self.b_ok = MyButton("Apply", self.accept)
        self.b_cancel = MyButton("Cancel", self.reject)
        layout = MyVBox().addAll(self.t_o, self.t_n, self.b_ok, self.b_cancel)
        self.setLayout(layout)
        self.resize(600, 200)


class EditMakerDialog(QDialog):
    def __init__(self, label: str, maker: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.t_l = QLineEdit(label)
        self.t_m = QLineEdit(maker)
        self.b_ok = MyButton("Apply", self.accept)
        self.b_cancel = MyButton("Cancel", self.reject)

        layout = MyVBox().addAll(self.t_l, self.t_m, self.b_ok, self.b_cancel)
        self.setLayout(layout)
        self.resize(400, 200)


class EditActorDialog(QDialog):
    def __init__(self, actor: List[str], movie_id: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.movie_id = movie_id
        self.txt = []
        layout = MyVBox()
        for i in range(6):
            e1 = QLineEdit()
            e2 = QLineEdit()
            h = MyHBox().addAll(e1, e2)
            self.txt.append(e1)
            self.txt.append(e2)
            layout.add(h)

        for i, name in enumerate(actor):
            self.txt[i].setText(name)

        self.suggest = []

        self.txt_word = QLineEdit()
        self.b_hint = MyButton("Hints", self.action_hint)
        self.b_search = MyButton("Search", self.action_search_actor)
        h_1 = MyHBox().addAll(self.txt_word, self.b_hint, self.b_search)
        layout.add(h_1)

        for i in range(4):
            h1 = QLineEdit()
            h2 = QLineEdit()
            h = MyHBox().addAll(h1, h2)
            self.suggest.append(h1)
            self.suggest.append(h2)
            layout.add(h)

        self.b_ok = MyButton("Apply", self.accept)
        self.b_cancel = MyButton("Cancel", self.reject)
        layout.addAll(self.b_ok, self.b_cancel)
        self.setLayout(layout)
        self.resize(500, 400)
        self.move(50, 50)

    @Slot()
    def action_hint(self):
        if self.txt_word.text():
            check = self.actor_suggest(self.txt_word.text())
            for i, txt in enumerate(self.suggest):
                txt.setText("")
                if len(check) > i:
                    txt.setText(check[i])

    @Slot()
    def action_search_actor(self):
        url = f"http://sougouwiki.com/search?keywords={self.movie_id}"
        webbrowser.open(url)

    def actor_suggest(self, word):
        check = []
        for name in InfoActor.data.keys():
            if word in name:
                check.append(name)
        return check


class MovieWidget(QWidget):
    on_save = Signal(InfoMovie)

    def __init__(self, movie: InfoMovie, local=False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.movie = movie

        self.txt_title = QLineEdit(movie.title)
        f = self.txt_title.font()
        f.setPointSize(20)
        self.txt_title.setFont(f)
        self.txt_title.setFixedHeight(50)

        """
        mid = movie.movie_id
        m = re.compile("(^[0-9A-Z]+?)-?(\d+)").match(mid).groups()
        if m:
            mid = f"{m[0]}-{int(m[1]):03d}"
        """
        self.txt_id = QLineEdit(movie.movie_id)
        self.txt_date = QLineEdit(movie.date)
        self.txt_len = QLineEdit(str(movie.length))
        self.txt_director = QLineEdit(movie.director)

        self.but_label = MyButton(movie.label)
        self.but_maker = MyButton(movie.maker)
        self.but_edit_maker = MyButton("Edit", self.action_edit_maker)
        self.but_edit_maker.setFixedWidth(90)
        h_box_maker = MyHBox().addAll(self.but_label, self.but_maker, self.but_edit_maker)

        self.but_edit_actor = MyButton("Actor", self.action_edit_actor)
        self.but_edit_actor.setFixedWidth(90)

        self.txt_series = QLineEdit(movie.series)
        but_open = MyButton("Open", self.action_open_url)
        but_open.setFixedWidth(90)
        h_box_series = MyHBox().addAll(self.txt_series, self.but_edit_actor, but_open)

        try:
            if movie.back_img_path:
                self.cover = MyImageBox.from_path(movie.back_img_path)
            else:
                self.cover = MyImageBox.from_path(movie.back_img_url)
        except Exception as e:
            print(e)
            self.cover = None

        try:
            if movie.front_img_path:
                self.thumb = MyImageBox.from_path(movie.front_img_path)
            else:
                self.thumb = MyImageBox.from_path(movie.front_img_url)
        except Exception as e:
            print(e)
            self.thumb = None

        self.h_box_actor = MyHBox()
        for actor in movie.actors:
            self.h_box_actor.add(MyButton(actor))

        h_box_keyword = MyHBox()
        for keyword in movie.keywords:
            if keyword not in InfoKeyword.FILTER:
                h_box_keyword.add(MyButton(keyword))

        self.but_save = MyButton("Save", self.action_save)
        self.but_save.setFixedWidth(90)
        if local:
            self.but_save.setText("Modify")

        h_box1 = MyHBox().addAll(self.txt_id, self.txt_date, self.txt_director,
                                 self.txt_len)

        if movie.path[-4:-3] != ".":
            h_box1.add(self.but_save)

        v_box1 = MyVBox().addAll(h_box1,
                                 h_box_maker,
                                 h_box_series,
                                 self.h_box_actor,
                                 h_box_keyword)
        h_box3 = MyHBox().addAll(self.thumb, v_box1)
        v_box2 = MyVBox().addAll(self.txt_title, h_box3, self.cover)
        self.setLayout(v_box2)

    @Slot()
    def action_edit_maker(self):
        edit = EditMakerDialog(self.but_label.text(), self.but_maker.text())
        if edit.exec():
            self.but_label.setText(edit.t_l.text())
            self.but_maker.setText(edit.t_m.text())

    @Slot()
    def action_edit_actor(self):
        edit = EditActorDialog(self.movie.actors, self.movie.movie_id)
        if edit.exec():
            actor_list = edit.txt
            self.movie.actors = []
            self.h_box_actor.clear()
            for actor in actor_list:
                if actor.text():
                    self.movie.actors.append(actor.text())
                    self.h_box_actor.add(MyButton(actor.text()))

    @Slot()
    def action_open_url(self):
        if self.movie.link:
            webbrowser.open(self.movie.link)

    @Slot()
    def action_save(self):
        if self.movie.path:
            self.movie.movie_id = self.txt_id.text()
            self.movie.maker = self.but_maker.text()
            self.movie.label = self.but_label.text()
            self.movie.title = self.txt_title.text()
            self.movie.length = int(self.txt_len.text())
            self.movie.series = self.txt_series.text()
            self.movie.save()
            self.on_save.emit(self.movie)
