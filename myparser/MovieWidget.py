import datetime
import os.path
import webbrowser
from typing import List

from PySide6.QtCore import Slot, Signal, QStringListModel, QSize
from PySide6.QtWidgets import QLineEdit, QFrame, QListView, QAbstractItemView, QWidget, QCheckBox
from qt_material import apply_stylesheet

from MyCommon import join_path, load_json
from myparser import get_soup
from myparser.InfoMovie import InfoMovie, InfoKeyword, InfoActor, InfoLabel, InfoMaker
from myparser.MovieCache import MovieCache
from myqt.CommonDialog import InputDialog
from myqt.EditDict import EditDictDialog
from myqt.MyQtCommon import QtHBox, QtVBox, MyButton, fa_icon, QtPasteEdit, QtDialog
from myqt.MyQtWorker import MyThread
from myqt.QtImage import MyImageBox
from myqt.QtVideo import MyVideoConvert, QtVideoDialog


class EditMakerDialog(QtDialog):
    def __init__(self, parent, label: str, maker: str, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.t_l = QtPasteEdit(label)
        self.t_m = QtPasteEdit(maker)
        self.b_map_l = MyButton("Map Label", self.map_label)

        layout = QtVBox().addAll(self.t_l, self.t_m,
                                 self.b_map_l,
                                 self._bar_ok_cancel())
        self.setLayout(layout)
        self.resize(600, 200)
        self.setWindowTitle("Edit")

    @Slot()
    def map_label(self):
        dial = EditDictDialog(InfoLabel.modify, self.t_l.text())
        if dial.exec():
            InfoLabel.modify = dial.get_result()
            self.t_l.setText(InfoLabel.add(self.t_l.text()))


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

    def __init__(self, actor: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = None
        self.selected = None
        self.movie_list: list[InfoMovie] = []

        self.photo = MyImageBox(self, QSize(125, 125))
        self.profile = QListView()
        self.profile_model = QStringListModel(self)
        self.profile.setModel(self.profile_model)
        self.profile.setFixedHeight(130)
        self.profile.setEditTriggers(QAbstractItemView.NoEditTriggers)

        profile_h_box = QtHBox().addAll(self.photo, self.profile)
        self.profile_update = MyButton("Update 1", self.action_get_profile)
        self.profile_update2 = MyButton("Update 2", self.action_get_profile2)

        self.view = QListView()
        self.model = QStringListModel(self)
        self.view.setModel(self.model)
        self.view.setMinimumWidth(600)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.clicked.connect(self.action_list_click)

        self.l_name = QLineEdit()
        self.l_name.setMinimumWidth(230)
        but_other_name = MyButton(fa_icon("fa5s.venus-double"), self.action_other_name)
        but_other_name.setFixedWidth(40)
        but_search_xcity = MyButton(fa_icon("mdi6.web-plus"), self.action_search_xcity)
        but_search_xcity.setFixedWidth(40)
        self.but_search_fanza = MyButton(fa_icon("mdi6.web-plus"), self.action_fanza)
        self.but_search_fanza.setFixedWidth(40)
        self.but_fanza = MyButton("F", self.action_fanza)
        self.but_fanza.setFixedWidth(40)
        self.l_ruby = QLineEdit()
        self.l_ruby.setMinimumWidth(230)
        self.l_age = QLineEdit()
        self.l_age.setFixedWidth(50)
        top = QtHBox().addAll(self.l_name, but_search_xcity, self.but_search_fanza, but_other_name,
                              self.but_fanza, self.l_ruby, self.l_age)

        self.list_movie = MyButton("Video", self.action_list_movie)

        self.edit_profile = MyButton("Edit", self.action_edit_actor)
        self.set_link = MyButton("Link", self.action_link_actor)

        left = QtVBox().addAll(top, profile_h_box,
                               QtHBox().addAll(self.profile_update, self.profile_update2, self.list_movie,
                                               self.edit_profile, self.set_link))

        layout = QtHBox().addAll(left, self.view)
        self.setLayout(layout)

        self.set_actor(actor)

    def set_actor(self, actor: str):
        if actor is not None and actor != "":
            self.actor = actor
            self.selected = None

            self.l_name.setText(actor)

            self.show_profile()
            self.action_get_movies()

    def show_profile(self, data: dict = None):
        if data is None:
            name, data = InfoActor.get(self.actor)
        if "profile" in data:
            photo, profile = data["profile"]
            self.photo.set_path_async(photo)
            self.profile_model.setStringList(list(map(lambda k: f"{k[0]} : {k[1]}", profile.items())))
        else:
            self.photo.set_image(None)
            self.profile_model.setStringList([])
        if "ruby" in data:
            self.l_ruby.setText(data["ruby"])
        else:
            self.l_ruby.setText("")
        age = InfoActor.age(self.actor)
        if age:
            self.l_age.setText(str(age))
        else:
            self.l_age.setText("")

        self.but_fanza.setEnabled("fanza" in data)
        self.but_search_fanza.setEnabled("fanza" not in data)

    def show_movie(self, movie_list: list):
        self.movie_list = movie_list
        self.model.setStringList(list(map(lambda m: m.title, self.movie_list)))

    def action_other_name(self):
        url = f"https://etigoya955.blog.fc2.com/?q={self.l_name.text().split('（', 1)[0]}"
        webbrowser.open(url)

    def action_search_xcity(self):
        name = self.l_name.text().split('（', 1)[0]
        url = f"https://xcity.jp/idol/?genre=%2Fidol%2F&q={name}&sg=idol&num=30"
        webbrowser.open(url)

    def action_fanza(self):
        name, data = InfoActor.get(self.actor)
        if "fanza" in data:
            fid = data["fanza"]
            url = f"https://actress.dmm.co.jp/-/detail/=/actress_id={fid}/"
        else:
            url = f"https://actress.dmm.co.jp/-/search/=/searchstr={name}/"
        webbrowser.open(url)

    def action_get_movies(self):
        run_thread = MyThread("ActorUpdateMovie")
        run_thread.set_run(MovieCache.get_by_actor, self.actor)
        run_thread.on_finish(on_result=self.show_movie)
        run_thread.start()

    def action_get_profile(self):
        self.profile_update.setEnabled(False)
        self.profile_update2.setEnabled(False)
        self.edit_profile.setEnabled(False)
        run_thread = MyThread("ActorUpdateProfile")
        run_thread.set_run(InfoActor.update_profile, self.actor)
        run_thread.on_finish(on_result=self.action_get_profile_finish)
        run_thread.start()

    def action_get_profile2(self):
        self.profile_update.setEnabled(False)
        self.profile_update2.setEnabled(False)
        self.edit_profile.setEnabled(False)
        run_thread = MyThread("ActorUpdateProfile")
        run_thread.set_run(InfoActor.update_profile2, self.actor)
        run_thread.on_finish(on_result=self.action_get_profile_finish)
        run_thread.start()

    def action_get_profile_finish(self, data):
        self.profile_update.setEnabled(True)
        self.profile_update2.setEnabled(True)
        self.edit_profile.setEnabled(True)
        if len(data) > 0:
            photo, profile = data

            _, old = InfoActor.get(self.actor)
            if "profile" in old:
                old_photo, old_profile = old["profile"]
                if not photo:
                    photo = old_photo
                if old_profile:
                    for k, v in old_profile.items():
                        if k not in profile:
                            profile[k] = v
            if "ruby" in profile and "ruby" in old:
                if profile["ruby"] == old["ruby"]:
                    profile.pop("ruby")
            self.save_edit_profile(photo, profile)

    @Slot()
    def action_list_movie(self):
        out = list(map(lambda m: [m.movie_id, m.get_front_img_path(), m.path], self.movie_list))
        self.lite_movie.emit(out)

    @Slot()
    def action_link_actor(self):
        dial = InputDialog()

        guess = InfoActor.guess_name(self.actor)
        print(guess)
        if guess:
            dial.txt_input.setText(guess[0])

        if dial.exec():
            new_name = dial.get_result()
            InfoActor.link(self.actor, new_name)
            if new_name != "" and new_name is not None:
                for m in self.movie_list:
                    for i, a in enumerate(m.actors):
                        if a == self.actor:
                            m.actors[i] = new_name

    @Slot()
    def action_edit_actor(self):
        name, data = InfoActor.get(self.actor)
        if "profile" in data:
            photo, profile = data["profile"]
            profile = profile.copy()
        else:
            photo = None
            profile = {}
        if "ruby" in data:
            profile["ruby"] = data["ruby"]
        else:
            profile["ruby"] = ""
        if "fanza" in data:
            profile["fanza"] = str(data["fanza"])
        self.save_edit_profile(photo, profile)

    def save_edit_profile(self, photo, profile):
        profile['photo'] = photo
        if "生年月日" not in profile:
            profile["生年月日"] = ""
        if '身長＆スリーサイズ' not in profile or profile['身長＆スリーサイズ'].strip() == "B W H":
            profile['身長＆スリーサイズ'] = ""
        dial = EditDictDialog(profile)
        if dial.exec():
            profile = dial.get_result()
            if 'photo' in profile:
                photo = profile.pop('photo')
            else:
                photo = None
            if "fanza" in profile:
                try:
                    fanza = int(profile.pop("fanza"))
                    InfoActor.add(self.actor, {"fanza": fanza})
                except Exception as e:
                    print(e)
            if "ruby" in profile:
                ruby = profile.pop("ruby")
                InfoActor.add(self.actor, {"ruby": ruby})
            if '生年月日' in profile:
                birth = profile['生年月日'].split("日", 1)[0].replace("年", "-").replace("月", "-")
                InfoActor.add(self.actor, {"birth": birth})
            if '身長＆スリーサイズ' in profile:
                d = profile['身長＆スリーサイズ'].replace("カップ", "").replace("()", "").replace("/ ", "")
                if d.startswith("T"):
                    d = d[1:]
                    if d[3] == " ":
                        d = d[:3] + "cm" + d[3:]
                profile['身長＆スリーサイズ'] = d

            data = InfoActor.get(self.actor, {"profile": [photo, profile]})
            InfoActor.save()
            self.show_profile(data[1])

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

        self.but_remove = MyButton("Hide", self.action_hide)

        layout = QtHBox().addAll(self.l_name, self.list_movie, self.but_remove)
        self.setLayout(layout)

    @Slot()
    def action_hide(self):
        InfoKeyword.FILTER.append(self.keyword)

    @Slot()
    def action_list_movie(self):
        out = list(map(lambda m: [m.movie_id, m.get_front_img_path(), m.path], self.movie_list))
        self.lite_movie.emit(out)


class EditActorDialog(QtDialog):
    def __init__(self, parent, actor: List[str], movie_id: str, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.movie_id = movie_id
        self.txt = []
        layout = QtVBox()
        for i in range(10):
            e1 = QLineEdit()
            e2 = QLineEdit()
            but1 = MyButton(self._icon_cancel(), self.action_clear, param=[i * 2])
            but2 = MyButton(self._icon_cancel(), self.action_clear, param=[i * 2 + 1])
            h = QtHBox().addAll(e1, but1, e2, but2)
            self.txt.append(e1)
            self.txt.append(e2)
            layout.add(h)

        for i, name in enumerate(actor):
            if i >= len(self.txt):
                break
            self.txt[i].setText(name)

        self.suggest = []

        self.txt_word = QLineEdit()
        self.b_hint = MyButton("Hints", self.action_hint)
        self.b_search = MyButton("Search", self.action_search_actor)
        self.b_search_web = MyButton("Web", self.action_search_actor_web)
        h_1 = QtHBox().addAll(self.txt_word, self.b_hint, self.b_search, self.b_search_web)
        layout.add(h_1)

        for i in range(6):
            h1 = QLineEdit()
            h2 = QLineEdit()
            but1 = MyButton(self._icon_ok(), self.action_use, param=[i * 2])
            but2 = MyButton(self._icon_ok(), self.action_use, param=[i * 2 + 1])
            h = QtHBox().addAll(h1, but1, h2, but2)
            self.suggest.append(h1)
            self.suggest.append(h2)
            layout.add(h)

        self.b_ok = MyButton("Apply", self.accept)
        self.b_cancel = MyButton("Cancel", self.reject)
        layout.addAll(self.b_ok, self.b_cancel)
        self.setLayout(layout)
        self.setWindowTitle("Edit")
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
            if i >= len(self.suggest):
                break
            self.suggest[i].setText(a)

    @Slot()
    def action_search_actor_web(self):
        url = f"http://sougouwiki.com/search?keywords={self.movie_id}"
        webbrowser.open(url)


class MovieWidget(QFrame):
    on_save = Signal(InfoMovie)
    on_actor = Signal(str)
    on_keyword = Signal(str)
    on_dir = Signal(str)

    def __init__(self, parent, movie: InfoMovie, local=False, loaded_f=None, loaded_b=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.movie = movie

        self.txt_title = QLineEdit(movie.title)
        f = self.txt_title.font()
        f.setPointSize(20)
        self.txt_title.setFont(f)
        self.txt_title.setFixedHeight(50)

        self.but_custom = QCheckBox("")
        self.but_custom.setFixedHeight(50)
        if movie.custom1 > 0:
            self.but_custom.setChecked(True)
        h_box_title = QtHBox().addAll(self.txt_title, self.but_custom)

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
        self.but_maker = MyButton(movie.maker, self.action_maker_click, [movie.maker])
        self.but_edit_maker = MyButton(fa_icon("fa5s.edit"), self.action_edit_maker)
        self.but_edit_maker.setFixedWidth(90)
        self.but_play_mp4 = MyButton(fa_icon("fa.youtube-play"), self.action_play_mp4)
        self.but_play_mp4.setFixedWidth(90)
        self.but_build_thumb = MyButton(fa_icon("fa5s.photo-video"), self.action_build_thumb)
        self.but_build_thumb.setFixedWidth(90)
        h_box_maker = QtHBox().addAll(self.but_label, self.but_maker, self.but_edit_maker,
                                      self.but_build_thumb, self.but_play_mp4)

        self.but_edit_actor = MyButton(fa_icon("mdi.human-female-female"), self.action_edit_actor)
        self.but_edit_actor.setFixedWidth(90)

        self.txt_series = QLineEdit(movie.series)
        but_open = MyButton(fa_icon("mdi6.web-plus"), self.action_open_url)
        but_open.setFixedWidth(90)
        h_box_series = QtHBox().addAll(self.txt_series, self.but_edit_actor, but_open)

        if loaded_b:
            self.cover = MyImageBox(self, image=loaded_b)
        else:
            try:
                if movie.back_img_path:
                    self.cover = MyImageBox.from_path(self, movie.back_img_path, asyn=True)
                else:
                    self.cover = MyImageBox.from_path(self, movie.back_img_url, asyn=True)
            except Exception as e:
                print(e)
                self.cover = None

        if loaded_f:
            self.thumb = MyImageBox(self, image=loaded_f)
        else:
            try:
                if movie.front_img_path:
                    self.thumb = MyImageBox.from_path(self, movie.front_img_path, QSize(147, 200), asyn=True)
                else:
                    self.thumb = MyImageBox.from_path(self, movie.front_img_url, QSize(147, 200), asyn=True)
            except Exception as e:
                print(e)
                self.thumb = None

        need_save = False
        for i, b_actor in enumerate(movie.actors):
            actor = InfoActor.get_link(b_actor)
            if b_actor != actor and self.movie.path:
                self.movie.actors[i] = actor
                need_save = True
        if local:
            while self.movie.path.endswith("\\"):
                self.movie.path = self.movie.path[:-1]
                print(self.movie.path)
                need_save = True

        if need_save:
            MovieCache.remove(self.movie)
            self.movie.save()
            MovieCache.put(self.movie)

        m_date = None
        if movie.date:
            try:
                m_date = datetime.datetime.strptime(movie.date, "%Y-%m-%d").date()
            except Exception as e:
                print(e)
                m_date = None

        cus_actor = MyButton("+", self.action_actor_click, [None])
        cus_actor.setFixedWidth(30)
        if len(movie.actors) > 5:
            actor_list = [movie.actors[i:i + 5] for i in range(0, len(movie.actors), 5)]
            self.h_box_actor = QtVBox()
            for row in actor_list:
                h_box = QtHBox()
                for actor in row:
                    actor_lab = actor
                    if m_date:
                        age = InfoActor.age(actor, m_date)
                        if age:
                            actor_lab = f"{actor} ({age})"
                    h_box.add(MyButton(actor_lab, self.action_actor_click, [actor]))
                self.h_box_actor.add(h_box)
        else:
            self.h_box_actor = QtHBox().add(cus_actor)
            for actor in movie.actors:
                actor_lab = actor
                if m_date:
                    age = InfoActor.age(actor, m_date)
                    if age:
                        actor_lab = f"{actor} ({age})"
                self.h_box_actor.add(MyButton(actor_lab, self.action_actor_click, [actor]))

        keywords_list = [k for k in movie.keywords if k not in InfoKeyword.FILTER]
        if len(movie.keywords) > 6:
            keywords_list = [keywords_list[i:i + 6] for i in range(0, len(keywords_list), 6)]
            h_box_keyword = QtVBox()
            for row in keywords_list:
                h_box = QtHBox()
                for keyword in row:
                    h_box.add(MyButton(keyword, self.action_keyword_click, [keyword]))
                h_box_keyword.add(h_box)
        else:
            h_box_keyword = QtHBox()
            for keyword in keywords_list:
                h_box_keyword.add(MyButton(keyword, self.action_keyword_click, [keyword]))

        self.but_save = MyButton("Save", self.action_save)
        self.but_save.setFixedWidth(90)
        if local:
            self.but_save.setText("Modify")
            self.but_custom.setEnabled(True)
        else:
            self.but_custom.setEnabled(False)

        h_box1 = QtHBox().addAll(self.txt_id, self.txt_date, self.txt_director,
                                 self.txt_len)

        v_box1 = QtVBox().addAll(h_box1,
                                 h_box_maker,
                                 h_box_series,
                                 self.h_box_actor,
                                 h_box_keyword)
        h_box_content = QtHBox().addAll(self.thumb, v_box1)
        v_box2 = QtVBox().addAll(h_box_title, h_box_content)

        if movie.path and movie.path[-4:-3] != ".":
            if movie.path.endswith(" V"):
                # apply_stylesheet(self, theme="dark_red.xml")
                v_box2.setStyleSheet("color: #999999; border-color: #999999;")
            else:
                h_box1.add(self.but_save)
                log = join_path(movie.path, MyVideoConvert.SAVE_FILE)
                if os.path.exists(log):
                    convert = load_json(log)
                    for idx, row in enumerate(convert):
                        v1 = MyButton(row["name"], self.action_play_mp4,
                                      [join_path(self.movie.path, row["name"]), idx])
                        v2 = MyButton(row["duration"])
                        v3 = MyButton(row["res"])
                        v4 = MyButton(str(int(int(row["bps"]) / 1000)) + " Kbps")
                        v5 = MyButton(row["codec"])
                        v6 = MyButton(row["a_codec"])
                        v_box2.add(QtHBox().addAll(v1, v2, v3, v4, v5, v6))
                    apply_stylesheet(self.parent(), theme="dark_lightgreen.xml")
                else:
                    apply_stylesheet(self.parent(), theme="dark_pink.xml")
        else:
            apply_stylesheet(self, theme="dark_pink.xml")
            self.but_play_mp4.setEnabled(False)
            self.but_custom.setEnabled(False)

        v_box2.add(self.cover)

        self.setLayout(v_box2)

    @Slot()
    def action_maker_click(self, maker):
        if InfoMaker.movie_base != "" and maker != "":
            path = join_path(InfoMaker.movie_base, InfoMaker.dir(maker))
            if os.path.exists(path):
                self.on_dir.emit(path)

    @Slot()
    def action_actor_click(self, actor):
        if actor is None:
            dial = InputDialog()
            if dial.exec():
                if dial.get_result() != "":
                    self.on_actor.emit(dial.get_result())
        else:
            self.on_actor.emit(actor)

    @Slot()
    def action_keyword_click(self, keyword):
        self.on_keyword.emit(keyword)

    @Slot()
    def action_play_mp4(self, file: str = None, offset: int = 0):
        if file is None:
            dial = QtVideoDialog.dialog_player(self.parent(), self.movie.path)
        else:
            dial = QtVideoDialog.dialog_player(self.parent(), [file], track_offset=offset)
        if dial:
            dial.show()

    @Slot()
    def action_build_thumb(self):
        dial = QtVideoDialog.dialog_create_preview(self.parent(), self.movie.path)
        if dial:
            dial.show()

    @Slot()
    def action_edit_maker(self):
        edit = EditMakerDialog(self, self.but_label.text(), self.but_maker.text())
        if edit.exec():
            self.but_label.setText(edit.t_l.text())
            self.but_maker.setText(edit.t_m.text())

    @Slot()
    def action_edit_actor(self):
        edit = EditActorDialog(self, self.movie.actors, self.movie.movie_id)
        if edit.exec():
            actor_list = edit.txt
            self.movie.actors = []
            self.h_box_actor.clear()
            for actor in actor_list:
                if actor.text():
                    name = actor.text()
                    name = InfoActor.get_link(name)
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
            self.movie.director = self.txt_director.text()
            self.movie.length = int(self.txt_len.text())
            self.movie.series = self.txt_series.text()
            self.movie.date = self.txt_date.text().replace(".", "-").strip()
            if self.but_custom.isChecked():
                self.movie.custom1 = 1
            self.movie.save()
            self.on_save.emit(self.movie)
            MovieCache.put(self.movie)


class MovieLiteWidget(QFrame):
    on_view = Signal(str, str)

    # info mid cover
    def __init__(self, parent, info, cover=None, path=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.t_id = QLineEdit(info['mid'])
        self.path = path

        if path:
            self.setStyleSheet("background-color: #ff1493;")
            self.t_id.setStyleSheet("color: white;")
        elif MovieCache.exist(self.t_id.text()):
            self.setStyleSheet("background-color: #ff0033;")
            self.t_id.setStyleSheet("color: white;")

        if cover:
            self.cover = MyImageBox(self, image=cover)
        else:
            self.cover = MyImageBox.from_path(self, info['cover'], QSize(147, 200))

        self.cover.clicked.connect(self.action_view)

        self.setFrameStyle(QFrame.WinPanel | QFrame.Raised)
        self.setLineWidth(2)

        layout = QtVBox().addAll(self.t_id, self.cover)  # , self.t_title)
        # layout.setContentsMargins(3, 3, 3, 3)
        self.setLayout(layout)
        self.setMaximumWidth(200)

    @Slot()
    def action_view(self):
        self.on_view.emit(self.t_id.text(), self.path)
