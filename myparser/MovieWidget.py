from PySide6.QtWidgets import QWidget, QLineEdit

from myparser.InfoMovie import InfoMovie
from myqt.MyQtCommon import MyHBox, MyVBox
from myqt.MyQtImage import MyImageBox


class MovieWidget(QWidget):
    def __init__(self, movie: InfoMovie, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.txt_id = QLineEdit(movie.movie_id)
        self.txt_date = QLineEdit(movie.date)
        self.txt_director = QLineEdit(movie.director)

        self.txt_label = QLineEdit(movie.label)
        self.txt_maker = QLineEdit(movie.maker)

        self.txt_title = QLineEdit(movie.title)
        self.cover = MyImageBox.from_path(movie.back_img_url)
        self.thumb = MyImageBox.from_path(movie.front_img_url)

        self.txt_actor = QLineEdit(str(movie.actors))
        self.txt_keyword = QLineEdit(str(movie.keywords))

        h_box1 = MyHBox().addAll(self.txt_id, self.txt_date, self.txt_director)
        h_box2 = MyHBox().addAll(self.txt_label, self.txt_maker)
        v_box1 = MyVBox().addAll(h_box1, h_box2, self.txt_title,
                                 self.txt_actor, self.txt_keyword)
        h_box3 = MyHBox().addAll(self.thumb, v_box1)
        v_box2 = MyVBox().addAll(h_box3, self.cover)
        self.setLayout(v_box2)
