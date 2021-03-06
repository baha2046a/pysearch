import os.path
import webbrowser
from typing import List

from PySide6.QtCore import *
from PySide6.QtWidgets import QLineEdit, QDialog, QFrame, QListView, QAbstractItemView, QWidget, QLabel

from MyCommon import chunks
from myparser import get_soup
from myparser.InfoMovie import InfoMovie, InfoKeyword, InfoActor, InfoLabel
from myparser.MovieCache import MovieCache
from myqt.MyQtCommon import MyHBox, MyVBox, MyButton
from myqt.MyQtImage import MyImageBox
from myqt.MyQtSetting import EditDictDialog
from myqt.MyQtWorker import MyThread


class RenameHint(MyVBox):
    hint_out = Signal(str)

    def __init__(self, hint_list: list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hint_list:
            hint_rows = chunks(hint_list, 4)
            for hints in hint_rows:
                row = MyHBox()
                for h in hints:
                    but_hint = MyButton(h, self.hint, [h])
                    row.add(but_hint)
                self.add(row)

    @Slot()
    def hint(self, name: str):
        self.hint_out.emit(name)


class EditMakerDialog(QDialog):
    def __init__(self, label: str, maker: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.t_l = QLineEdit(label)
        self.t_m = QLineEdit(maker)
        self.b_map_l = MyButton("Map Label", self.map_label)
        self.b_ok = MyButton("Apply", self.accept)
        self.b_cancel = MyButton("Cancel", self.reject)

        layout = MyVBox().addAll(self.t_l, self.t_m,
                                 self.b_map_l,
                                 self.b_ok, self.b_cancel)
        self.setLayout(layout)
        self.resize(400, 200)

    @Slot()
    def map_label(self):
        dial = EditDictDialog(InfoLabel.modify, self.t_l.text())
        if dial.exec():
            InfoLabel.modify = dial.get_result()
            self.t_l.setText(InfoLabel.get(self.t_l.text()))


def actor_suggest(word):
    check = []
    for name in InfoActor.data.keys():
        if word in name:
            check.append(name)
    return check


def actor_parse(mid):
    url = f"http://sougouwiki.com/search?keywords={mid}"
    soup = get_soup(url)
    result = []
    if soup:
        elements = soup.select("h3[class=keyword]")
        for e in elements:
            result.append(e.text)
    return result


class ActorWidget(QWidget):
    output = Signal(str)
    lite_movie = Signal(list)

    def __init__(self, actor: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.selected = None
        self.movie_list: list[InfoMovie] = []

        self.photo = MyImageBox()
        self.profile = QListView()
        self.profile_model = QStringListModel(self)
        self.profile.setModel(self.profile_model)
        self.profile.setFixedHeight(130)
        self.profile.setEditTriggers(QAbstractItemView.NoEditTriggers)

        profile_h_box = MyHBox().addAll(self.photo, self.profile)
        self.profile_update = MyButton("Update Profile", self.action_get_profile)

        self.view = QListView()
        self.model = QStringListModel(self)
        self.view.setModel(self.model)
        self.view.setMinimumWidth(600)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.clicked.connect(self.action_list_click)
        self.model.setStringList(list(map(lambda m: m.title, self.movie_list)))

        self.l_name = MyButton(actor)
        self.l_name.setMinimumWidth(500)
        self.list_movie = MyButton("List Local Video", self.action_list_movie)

        left = MyVBox().addAll(self.l_name,
                               profile_h_box,
                               MyHBox().addAll(self.profile_update, self.list_movie))

        layout = MyHBox().addAll(left, self.view)
        self.setLayout(layout)

        self.show_profile()
        self.action_get_movies()

    def show_profile(self, data: dict = None):
        if data is None:
            name, data = InfoActor.get(self.actor)
        if "profile" in data:
            photo, profile = data["profile"]
            self.photo.set_path_async(photo)
            self.profile_model.setStringList(list(map(lambda k: f"{k[0]} : {k[1]}", profile.items())))

    def show_movie(self, movie_list: list):
        self.movie_list = movie_list
        self.model.setStringList(list(map(lambda m: m.title, self.movie_list)))

    def action_get_movies(self):
        run_thread = MyThread("ActorUpdateMovie")
        run_thread.set_run(MovieCache.get_by_actor, self.actor)
        run_thread.on_finish(on_result=self.show_movie)
        run_thread.start()

    def action_get_profile(self):
        self.profile_update.setEnabled(False)
        run_thread = MyThread("ActorUpdateProfile")
        run_thread.set_run(InfoActor.update_profile, self.actor)
        run_thread.on_finish(on_result=self.action_get_profile_finish)
        run_thread.start()

    def action_get_profile_finish(self, data):
        self.profile_update.setEnabled(True)
        if data:
            self.show_profile(data[1])

    @Slot()
    def action_list_movie(self):
        out = list(map(lambda m: [m.movie_id, m.get_front_img_path(), m.path], self.movie_list))
        self.lite_movie.emit(out)

    @Slot()
    def action_list_click(self, index):
        self.selected = index.row()
        if self.selected is not None and self.movie_list[self.selected].path:
            self.output.emit(self.movie_list[self.selected].path)


class KeywordWidget(QWidget):
    lite_movie = Signal(list)

    def __init__(self, keyword: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keyword = keyword
        self.movie_list: list[InfoMovie] = MovieCache.get_by_keyword(keyword)

        self.l_name = MyButton(keyword)
        self.list_movie = MyButton("List", self.action_list_movie)

        layout = MyHBox().addAll(self.l_name, self.list_movie)
        self.setLayout(layout)

    @Slot()
    def action_list_movie(self):
        out = list(map(lambda m: [m.movie_id, m.get_front_img_path(), m.path], self.movie_list))
        self.lite_movie.emit(out)


class EditActorDialog(QDialog):
    def __init__(self, actor: List[str], movie_id: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.movie_id = movie_id
        self.txt = []
        layout = MyVBox()
        for i in range(6):
            e1 = QLineEdit()
            e2 = QLineEdit()
            but1 = MyButton("C", self.action_clear, param=[i * 2])
            but2 = MyButton("C", self.action_clear, param=[i * 2 + 1])
            h = MyHBox().addAll(e1, but1, e2, but2)
            self.txt.append(e1)
            self.txt.append(e2)
            layout.add(h)

        for i, name in enumerate(actor):
            self.txt[i].setText(name)

        self.suggest = []

        self.txt_word = QLineEdit()
        self.b_hint = MyButton("Hints", self.action_hint)
        self.b_search = MyButton("Search", self.action_search_actor)
        self.b_search_web = MyButton("Web", self.action_search_actor_web)
        h_1 = MyHBox().addAll(self.txt_word, self.b_hint, self.b_search, self.b_search_web)
        layout.add(h_1)

        for i in range(6):
            h1 = QLineEdit()
            h2 = QLineEdit()
            but1 = MyButton("U", self.action_use, param=[i * 2])
            but2 = MyButton("U", self.action_use, param=[i * 2 + 1])
            h = MyHBox().addAll(h1, but1, h2, but2)
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
    def action_clear(self, line):
        self.txt[line].setText("")

    @Slot()
    def action_use(self, line):
        s_list = []
        for i in self.suggest:
            s_list.append(i.text())
        for i in self.txt:
            if i.text() == "":
                i.setText(s_list[line])
                s_list[line] = ""
                break
        for i, name in enumerate(s_list):
            if name == "":
                s_list.pop(i)
        for i, name in enumerate(self.suggest):
            if i < len(s_list):
                name.setText(s_list[i])
            else:
                name.setText("")

    @Slot()
    def action_hint(self):
        if self.txt_word.text():
            check = actor_suggest(self.txt_word.text())
            for i, txt in enumerate(self.suggest):
                txt.setText("")
                if len(check) > i:
                    txt.setText(check[i])

    @Slot()
    def action_search_actor(self):
        results = actor_parse(self.movie_id)
        actors = []
        for a in results:
            check = actor_suggest(a)
            if check:
                actors.extend(check)
            else:
                actors.append(a)

        for i, a in enumerate(actors):
            self.suggest[i].setText(a)

    @Slot()
    def action_search_actor_web(self):
        url = f"http://sougouwiki.com/search?keywords={self.movie_id}"
        webbrowser.open(url)


class MovieWidget(QFrame):
    on_save = Signal(InfoMovie)
    on_actor = Signal(str)
    on_keyword = Signal(str)

    def __init__(self, movie: InfoMovie, local=False, loaded_f=None, loaded_b=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.movie = movie

        self.txt_title = QLineEdit(movie.title)
        f = self.txt_title.font()
        f.setPointSize(20)
        self.txt_title.setFont(f)
        self.txt_title.setFixedHeight(50)

        self.setFrameStyle(QFrame.WinPanel | QFrame.Raised)
        self.setLineWidth(2)
        self.setMaximumWidth(1500)

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
        self.but_play_mp4 = MyButton("Play", self.action_play_mp4)
        self.but_play_mp4.setFixedWidth(90)
        h_box_maker = MyHBox().addAll(self.but_label, self.but_maker, self.but_edit_maker, self.but_play_mp4)

        self.but_edit_actor = MyButton("Actor", self.action_edit_actor)
        self.but_edit_actor.setFixedWidth(90)

        self.txt_series = QLineEdit(movie.series)
        but_open = MyButton("Open", self.action_open_url)
        but_open.setFixedWidth(90)
        h_box_series = MyHBox().addAll(self.txt_series, self.but_edit_actor, but_open)

        if loaded_f:
            self.cover = MyImageBox(image=loaded_b)
        else:
            try:
                if movie.back_img_path:
                    self.cover = MyImageBox.from_path(movie.back_img_path)
                else:
                    self.cover = MyImageBox.from_path(movie.back_img_url)
            except Exception as e:
                print(e)
                self.cover = None

        if loaded_b:
            self.thumb = MyImageBox(image=loaded_f)
        else:
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
            self.h_box_actor.add(MyButton(actor, self.action_actor_click, [actor]))

        h_box_keyword = MyHBox()
        for keyword in movie.keywords:
            if keyword not in InfoKeyword.FILTER:
                h_box_keyword.add(MyButton(keyword, self.action_keyword_click, [keyword]))

        self.but_save = MyButton("Save", self.action_save)
        self.but_save.setFixedWidth(90)
        if local:
            self.but_save.setText("Modify")

        h_box1 = MyHBox().addAll(self.txt_id, self.txt_date, self.txt_director,
                                 self.txt_len)

        if movie.path and movie.path[-4:-3] != ".":
            h_box1.add(self.but_save)
        else:
            self.but_play_mp4.setEnabled(False)

        v_box1 = MyVBox().addAll(h_box1,
                                 h_box_maker,
                                 h_box_series,
                                 self.h_box_actor,
                                 h_box_keyword)
        h_box3 = MyHBox().addAll(self.thumb, v_box1)
        v_box2 = MyVBox().addAll(self.txt_title, h_box3, self.cover)
        self.setLayout(v_box2)

    @Slot()
    def action_actor_click(self, actor):
        self.on_actor.emit(actor)

    @Slot()
    def action_keyword_click(self, keyword):
        self.on_keyword.emit(keyword)

    @Slot()
    def action_play_mp4(self):
        for file in os.listdir(self.movie.path):
            if file.lower().endswith(".mp4"):
                os.startfile(os.path.join(self.movie.path, file))
                break

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
                    name = actor.text()
                    self.movie.actors.append(name)
                    self.h_box_actor.add(MyButton(name, self.action_actor_click, [name]))

    @Slot()
    def action_open_url(self):
        if self.movie.link:
            webbrowser.open(self.movie.link)

    @Slot()
    def action_save(self):
        MovieCache.remove(self.movie)
        if self.movie.path:
            self.movie.movie_id = self.txt_id.text()
            self.movie.maker = self.but_maker.text()
            self.movie.label = self.but_label.text()
            self.movie.title = self.txt_title.text()
            self.movie.length = int(self.txt_len.text())
            self.movie.series = self.txt_series.text()
            self.movie.save()
            self.on_save.emit(self.movie)
            MovieCache.put(self.movie)


class MovieLiteWidget(QFrame):
    on_view = Signal(str, str)

    # info mid cover
    def __init__(self, info, cover=None, path=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.t_id = QLineEdit(info['mid'])
        self.path = path

        if path:
            self.setStyleSheet("background-color: #ff1493;")
            self.t_id.setStyleSheet("color: white;")

        if cover:
            self.cover = MyImageBox(image=cover)
        else:
            self.cover = MyImageBox.from_path(info['cover'])

        self.cover.clicked.connect(self.action_view)

        self.setFrameStyle(QFrame.WinPanel | QFrame.Raised)
        self.setLineWidth(2)

        layout = MyVBox().addAll(self.t_id, self.cover)  # , self.t_title)
        # layout.setContentsMargins(3, 3, 3, 3)
        self.setLayout(layout)
        self.setMaximumWidth(200)

    @Slot()
    def action_view(self):
        self.on_view.emit(self.t_id.text(), self.path)
