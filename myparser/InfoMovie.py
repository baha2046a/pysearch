from myparser.MovieNameFix import movie_name_fix


class InfoMovie:
    FILE = "info.txt"
    FRONT_IMG = "front.jpg"
    BACK_IMG = "back.jpg"

    def __init__(self,
                 movie_id: str,
                 path: str,
                 back_img_url: str,
                 front_img_url: str,
                 title: str,
                 maker,
                 label,
                 date,
                 series,
                 length,
                 desc,
                 director,
                 actors,
                 keywords,
                 movie_files):
        self.movie_id = movie_id
        self.path = path
        self.back_img_url = back_img_url
        self.front_img_url = front_img_url
        self.title = movie_name_fix(title)
        self.maker = maker
        self.label = label
        self.date = date
        self.series = series
        self.length = length
        self.desc = desc
        self.director = director
        self.actors = actors
        self.keywords = keywords
        self.movie_files = movie_files

