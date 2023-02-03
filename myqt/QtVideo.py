import datetime
import os
import subprocess
import threading
import time
from typing import Optional, AnyStr, Union

from PySide6 import QtMultimedia, QtCore
from PySide6.QtCore import Signal, QSize, Qt, Slot, QThread, QCoreApplication, QObject
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData, QMediaFormat, QVideoSink, QVideoFrame
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QSlider, QLabel, QProgressBar

from MyCommon import join_path, list_dir, save_json, find_main_widget
from myqt.MyQtCommon import fa_icon, MyButton, QtHBox, QtVBox, QtDialogAutoClose
from myqt.MyQtFlow import MyQtScrollableFlow
from myqt.MyQtWorker import MyThread
from myqt.QtImage import MyImageSource, MyImageBox


class QtVideoDialog(QtDialogAutoClose):
    FORMAT_VIDEO = [".wmv", ".avi", ".mp4", ".mpeg", ".mov"]
    FORMAT_AUDIO = [".wav", ".mp3"]
    AUDIO_LEVEL = 0.3

    available = True

    @staticmethod
    def dialog_create_preview(parent: QObject, paths: Union[str, list], track_offset: int = 0):
        if QtVideoDialog.available:
            if isinstance(paths, str):
                paths = QtVideoDialog.list_movie(paths)
            if paths:
                return MyVideoConvert(parent, paths, track_offset)
        return None

    @staticmethod
    def dialog_player(parent: QObject, paths: Union[str, list],
                      full_screen: bool = False, audio_only: bool = False, track_offset: int = 0):
        if QtVideoDialog.available:
            if isinstance(paths, str):
                paths = QtVideoDialog.list_movie(paths)
            if paths:
                return MyVideoDialog(parent, paths, full_screen, audio_only, track_offset)
        return None

    @staticmethod
    def has_movie(folder: AnyStr) -> bool:
        if folder:
            for file in list_dir(folder):
                ext = os.path.splitext(file)[1]
                if ext != "":
                    if ext.lower() in QtVideoDialog.FORMAT_VIDEO:
                        return True
        return False

    @staticmethod
    def list_movie(folder: AnyStr) -> list:
        result = []
        if folder:
            for file in list_dir(folder):
                ext = os.path.splitext(file)[1]
                if ext != "":
                    if ext.lower() in QtVideoDialog.FORMAT_VIDEO:
                        result.append(join_path(folder, file))
        return result

    @staticmethod
    def has_preview(folder) -> Optional[str]:
        frames_folder = join_path(folder, MyVideoConvert.FOLDER)
        if os.path.isdir(frames_folder):
            return frames_folder
        return None

    def __init__(self, parent, play_list: list, track_offset: int, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        QtVideoDialog.available = False

        self.current_track = 0
        self.track_offset = track_offset
        self.play_list = play_list

        self.folder = os.path.dirname(play_list[0])

        self.player = QMediaPlayer(self)
        self.but_audio_codec = MyButton("")
        self.but_codec = MyButton("")

    def current_file(self) -> str:
        return self.play_list[self.current_track]

    def closeEvent(self, arg__1):
        QtVideoDialog.available = True
        super().closeEvent(arg__1)

    @Slot()
    def action_external(self):
        os.startfile(self.windowTitle())

    @Slot()
    def action_explorer(self):
        folder = os.path.dirname(self.windowTitle()).replace('/', '\\')
        subprocess.Popen(f"explorer {folder}")

    def show_audio_codec(self):
        val = self.player.metaData().value(QMediaMetaData.AudioCodec)
        if val:
            self.but_audio_codec.setText(QMediaFormat.AudioCodec(val).name)
        else:
            self.but_audio_codec.setText("")

    def show_codec(self):
        val = self.player.metaData().value(QMediaMetaData.VideoCodec)
        if val:
            self.but_codec.setText(QMediaFormat.VideoCodec(val).name)
        else:
            self.but_codec.setText("")


class MyVideoDialog(QtVideoDialog):
    image_signal = Signal(str, QSize, MyImageSource)
    play_signal = Signal()

    def __init__(self, parent, play_list: list,
                 full_screen: bool = False,
                 audio_only: bool = False,
                 track_offset: int = 0,
                 *args, **kwargs):
        super().__init__(parent, play_list, track_offset, *args, **kwargs)

        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self.setWindowIcon(fa_icon('fa5s.file-video', "black"))

        if not audio_only:
            self.video = QVideoWidget()
            self.player.setVideoOutput(self.video)

        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)

        self.but_next = MyButton(fa_icon('fa.step-forward'), self.load_track, [1])
        self.but_prev = MyButton(fa_icon('fa.step-backward'), self.load_track, [-1])
        self.but_next.setEnabled(False)
        self.but_prev.setEnabled(False)

        self.player.audioOutput().setVolume(QtVideoDialog.AUDIO_LEVEL)
        self.volume_bar = QSlider(self, orientation=Qt.Orientation.Horizontal)
        self.volume_bar.setMinimum(0)
        self.volume_bar.setMaximum(10)
        self.volume_bar.setFixedWidth(200)
        self.volume_bar.setValue(QtVideoDialog.AUDIO_LEVEL * 10)
        self.volume_bar.setTickInterval(5)
        self.volume_bar.setTickPosition(QSlider.TicksAbove)
        self.volume_bar.sliderReleased.connect(self.__volume_release)

        self.player.mediaStatusChanged.connect(self.media_state)
        self.player.durationChanged.connect(self.duration)
        self.player.playbackRateChanged.connect(self.rate)
        self.player.positionChanged.connect(self.time)

        self.seek_bar = QSlider(self, orientation=Qt.Orientation.Horizontal)
        self.seek_bar.setMinimum(0)
        self.seek_bar.setMaximum(200)
        self.seek_bar.sliderPressed.connect(self.__bar_press)
        self.seek_bar.sliderReleased.connect(self.__bar_release)
        self.seek_bar.setTracking(True)
        self.seek_bar.setEnabled(False)

        self.__bar_no_update = False

        self.total_time = 0
        self.current_time = 0

        self.txt_current = QLabel("")
        self.txt_total = QLabel("")

        if full_screen or audio_only:
            self.v_size = QSize(0, 0)
        else:
            self.v_size = QSize(1280, 720)
            self.video.setMaximumSize(QSize(1280, 720))
        self.v_full = QSize(1280, 720)
        self.setFixedHeight(self.v_size.height() + 130)

        self.but_external = MyButton(fa_icon('fa5s.sign-out-alt'), self.action_external)
        self.but_explorer = MyButton(fa_icon("ph.folder-open-fill"), self.action_explorer)

        self.but_play = MyButton(fa_icon('fa.play'), self.__play)
        self.but_pause = MyButton(fa_icon('fa.pause'), self.__pause, [True])
        self.but_stop = MyButton(fa_icon('fa.stop'), self.__stop)
        self.but_r1 = MyButton("x1", self.action_set_rate, [1.0])
        self.but_r2 = MyButton("x2", self.action_set_rate, [2.0])
        self.but_r4 = MyButton("x4", self.action_set_rate, [4.0])
        self.but_r8 = MyButton("x8", self.action_set_rate, [8.0])
        self.but_r1.setEnabled(False)
        self.but_res = MyButton("", self.action_set_size)

        self.but_play.setEnabled(False)
        self.but_stop.setEnabled(False)

        self.image_flow = MyQtScrollableFlow()
        self.image_flow.setMinimumWidth(180)
        self.image_flow.setMaximumWidth(180)
        self.image_flow.setContentsMargins(20, 5, 0, 5)

        bar = QtHBox().addAll(self.but_external, self.but_explorer, self.but_prev, self.but_next,
                              self.but_play, self.but_pause, self.but_stop,
                              self.but_res, self.but_codec, self.but_audio_codec,
                              self.but_r1, self.but_r2, self.but_r4, self.but_r8)

        txt_volume = QLabel(self)
        txt_volume.setPixmap(fa_icon('fa5s.volume-up').pixmap(QSize(16, 16)))
        txt_volume.setContentsMargins(20, 0, 5, 0)

        tracks = QtHBox().addAll(self.txt_current, self.seek_bar, self.txt_total, txt_volume, self.volume_bar)

        self.play_signal.connect(self.__play, Qt.QueuedConnection)

        if audio_only:
            self.folder = None
            self.setMinimumWidth(1300)
            self.but_res.setVisible(False)
            self.but_codec.setVisible(False)
            self.setLayout(QtVBox().addAll(tracks, bar))
        elif full_screen:
            self.folder = None
            self.setMinimumWidth(1300)
            self.video.setAttribute(Qt.WA_DeleteOnClose)
            self.video.setFullScreen(True)
            self.setLayout(QtVBox().addAll(tracks, bar))
            self.video.show()
        else:
            self.setMinimumWidth(1500)
            if play_list:
                self.image_signal.connect(self.show_image, Qt.QueuedConnection)
            self.video.setFixedSize(self.v_full)
            self.setLayout(QtVBox().addAll(QtHBox().addAll(self.video, self.image_flow), tracks, bar))

        if play_list:
            self.load_track(0)

    def closeEvent(self, arg__1):
        self.image_signal = None
        super().closeEvent(arg__1)

    def action_set_rate(self, rate: float):
        self.__pause()
        self.player.setPlaybackRate(rate)
        self.play_signal.emit()

    @Slot()
    def action_set_size(self):
        if self.but_res.text() != "":
            if self.video.size() == self.v_full and self.v_size.height() < self.v_full.height():
                self.video.setFixedHeight(self.v_size.height())
            else:
                self.video.setFixedHeight(self.v_full.height())
            self.setFixedHeight(self.video.size().height() + 130)

    @Slot()
    def __bar_press(self):
        self.__bar_no_update = True

    @Slot()
    def __bar_release(self):
        seek_pos = self.seek_bar.value()
        if 0 < seek_pos < self.seek_bar.maximum():
            pos = seek_pos / self.seek_bar.maximum()
            t = int(self.total_time * pos)
            self.seek_time(t)

    def seek_time(self, t):
        self.__pause()
        self.current_time = t
        self.play_signal.emit()

    def show_preview_images(self) -> None:
        if self.folder:
            frames = self.has_preview(self.folder)
            if frames:
                # apply_stylesheet(self, theme="dark_lightgreen.xml")
                run_thread = MyThread("movie_image_flow")
                run_thread.set_run(self.async_load_preview_images, frames, QSize(140, 100))
                run_thread.on_finish(on_before=self.image_flow.clearAll)
                run_thread.start()
            # else:
            # apply_stylesheet(self, theme="dark_pink.xml")

    def async_load_preview_images(self, folder, as_size, thread):
        files = list_dir(folder, f"{self.current_track + self.track_offset}*.jpg")

        for f in files:
            file: str = f.replace("\\", "/")
            img = MyImageSource(file, as_size)
            if self.image_signal:
                self.image_signal.emit(file, as_size, img)
            else:
                break
            if QThread.isInterruptionRequested(thread):
                break
            time.sleep(0.01)
        return True

    @Slot()
    def show_image(self, _, as_size, img: MyImageSource) -> None:
        self.image_flow.show_img(as_size, img, self.seek_by_image)
        QCoreApplication.processEvents()

    @Slot()
    def seek_by_image(self, path: str, _1, _2):
        if self.seek_bar.isEnabled():
            try:
                t = path.rsplit("/", 1)[-1].replace(".jpg", "")[1:]
                t = int(t) * 60000
                self.seek_time(t)
            except Exception as e:
                print(e)

    @Slot()
    def __volume_release(self):
        QtVideoDialog.AUDIO_LEVEL = self.volume_bar.value() / 10
        self.player.audioOutput().setVolume(QtVideoDialog.AUDIO_LEVEL)

    @Slot()
    def __pause(self, set_but: bool = False):
        self.__bar_no_update = True
        if set_but:
            self.but_play.setEnabled(True)
            self.but_pause.setEnabled(False)
        self.player.pause()

    @Slot()
    def __stop(self):
        self.__bar_no_update = True
        self.player.stop()
        self.current_time = 0
        self.seek_bar.setValue(0)

    @Slot()
    def __play(self):
        self.player.setPosition(self.current_time + 1)
        self.but_play.setEnabled(False)
        self.but_pause.setEnabled(True)
        timer = threading.Timer(1.0, self.__resume)
        timer.start()

    def __resume(self):
        self.player.play()
        self.__bar_no_update = False

    @Slot()
    def load_track(self, track_change: int):
        if track_change != 0:
            self.__stop()

        self.current_track = self.current_track + track_change
        if self.current_track < 0:
            self.current_track = 0
        elif self.current_track >= len(self.play_list):
            self.current_track = len(self.play_list) - 1

        self.setWindowTitle(self.current_file())
        self.player.setSource(self.current_file())
        if self.current_track == 0:
            self.but_prev.setEnabled(False)
        else:
            self.but_prev.setEnabled(True)
        if (self.current_track + 1) >= len(self.play_list):
            self.but_next.setEnabled(False)
        else:
            self.but_next.setEnabled(True)

        self.show_preview_images()

    @Slot()
    def rate(self, rate):
        print(rate)
        if rate == 1.0:
            self.but_r1.setEnabled(False)
            self.but_r2.setEnabled(True)
            self.but_r4.setEnabled(True)
            self.but_r8.setEnabled(True)
        elif rate == 2.0:
            self.but_r1.setEnabled(True)
            self.but_r2.setEnabled(False)
            self.but_r4.setEnabled(True)
            self.but_r8.setEnabled(True)
        elif rate == 4.0:
            self.but_r1.setEnabled(True)
            self.but_r2.setEnabled(True)
            self.but_r4.setEnabled(False)
            self.but_r8.setEnabled(True)
        elif rate == 8.0:
            self.but_r1.setEnabled(True)
            self.but_r2.setEnabled(True)
            self.but_r4.setEnabled(True)
            self.but_r8.setEnabled(False)
        else:
            self.but_r1.setEnabled(False)
            self.but_r2.setEnabled(False)
            self.but_r4.setEnabled(False)
            self.but_r8.setEnabled(False)

    @Slot()
    def duration(self, duration: int):
        if duration == 0:
            self.txt_total.setText("")
        else:
            self.total_time = duration
            self.txt_total.setText(str(datetime.timedelta(seconds=round(duration / 1000))))

    @Slot()
    def time(self, current_play_time: int):
        if current_play_time == 0:
            self.txt_current.setText("")
        else:
            self.current_time = current_play_time
            if not self.__bar_no_update:
                per = int((self.current_time / self.total_time) * self.seek_bar.maximum())
                if self.seek_bar.value() != per:
                    self.seek_bar.setValue(per)
            self.txt_current.setText(str(datetime.timedelta(seconds=round(self.current_time / 1000))))
            self.txt_total.setText(str(datetime.timedelta(seconds=round((self.total_time - self.current_time) / 1000))))

    @Slot()
    def media_state(self, state: QtMultimedia.QMediaPlayer.MediaStatus):
        print(state, self.player.duration())
        if state is QtMultimedia.QMediaPlayer.MediaStatus.LoadedMedia:
            self.but_play.setEnabled(True)
            self.but_pause.setEnabled(False)
            self.but_stop.setEnabled(False)
            self.seek_bar.setEnabled(False)
            if self.player.hasVideo():
                self.v_size: QSize = self.player.metaData().value(QMediaMetaData.Resolution)
                self.but_res.setText(self.player.metaData().stringValue(QMediaMetaData.Resolution))
                print(self.player.metaData().stringValue(QMediaMetaData.VideoBitRate))
                self.show_codec()
                self.show_audio_codec()
            # if len(self.play_list) == 1:
            self.play_signal.emit()
        elif state is QtMultimedia.QMediaPlayer.MediaStatus.BufferedMedia:
            self.but_stop.setEnabled(True)
            self.seek_bar.setEnabled(True)
        elif state is QtMultimedia.QMediaPlayer.MediaStatus.EndOfMedia:
            self.but_play.setEnabled(True)
            self.but_pause.setEnabled(False)
            self.but_stop.setEnabled(False)
            self.__stop()
            if self.but_next.isEnabled():
                self.load_track(1)
            # else:
            #    self.player.setPosition(0)
        elif state is QtMultimedia.QMediaPlayer.MediaStatus.InvalidMedia:
            self.but_play.setEnabled(True)
            self.but_pause.setEnabled(False)
            self.but_stop.setEnabled(False)
            self.__stop()
            self.load_track(0)
        else:
            self.but_play.setEnabled(False)
            self.but_pause.setEnabled(False)
            self.but_stop.setEnabled(False)
            self.seek_bar.setEnabled(False)
            self.txt_total.setText("")


class MyVideoConvert(QtVideoDialog):
    FOLDER = "frames"
    SAVE_FILE = "convert.json"
    THUMB_SIZE = QSize(500, 300)
    FRAME_SEC = 60

    load_signal = Signal()
    next_signal = Signal()
    close_signal = Signal()

    def __init__(self, parent, play_list: list, track_offset: int = 0, *args, **kwargs):
        super().__init__(parent, play_list, track_offset, *args, **kwargs)
        QtVideoDialog.available = False

        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        self.convert_log = []

        self.total_time = 0
        self.current_frame = 0
        self.total_frame = 0
        self.rate = 0

        self.frame_folder = join_path(self.folder, MyVideoConvert.FOLDER)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self.setWindowIcon(fa_icon('fa5s.file-video', "black"))
        self.setWindowTitle(self.folder)

        self.txt_track = QLabel(str(len(play_list)))
        self.txt_total = QLabel("")
        self.but_play = MyButton(fa_icon('fa.play'), self.__play)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumWidth(500)

        self.sink = QVideoSink(self)
        self.sink.videoFrameChanged.connect(self.__frame)

        self.player.mediaStatusChanged.connect(self.media_state)
        self.player.durationChanged.connect(self.duration)

        self.player.setPlaybackRate(1.0)
        self.player.setVideoOutput(self.sink)

        self.preview = MyImageBox(self)
        self.preview.setFixedSize(MyVideoConvert.THUMB_SIZE)

        self.load_signal.connect(self.load_track, Qt.QueuedConnection)
        self.next_signal.connect(self.__next, Qt.QueuedConnection)
        self.close_signal.connect(self.close, Qt.QueuedConnection)

        self.ready = False

        self.setLayout(QtVBox().addAll(QtHBox().addAll(self.txt_track, self.txt_total),
                                       QtHBox().addAll(self.but_codec, self.but_audio_codec,
                                                       self.but_play),
                                       self.progress_bar, self.preview))
        self.load_track()

    def load_track(self):
        self.ready = False
        self.convert_log.append({"name": os.path.basename(self.current_file())})
        self.player.setSource(self.current_file())

    def __play(self):
        if not os.path.exists(self.frame_folder):
            os.mkdir(self.frame_folder)
        self.rate = self.FRAME_SEC * 1000
        frame = int(self.total_time / self.rate)
        # int(int(self.txt_num_frame.text()) / len(self.play_list))
        self.current_frame = -1
        self.total_frame = frame + 1
        self.progress_bar.setMaximum(frame)
        self.progress_bar.setValue(0)
        self.player.play()

    def __next(self):
        self.current_frame = self.current_frame + 1
        print("Next", self.current_track, self.current_frame, self.total_frame)
        if self.current_frame < self.total_frame:
            # t = (self.v_current / self.num_frames) * self.v_total
            t = self.current_frame * self.rate
            self.player.setPosition(t)
        elif self.current_frame == self.total_frame:
            self.ready = False
            self.player.setPlaybackRate(1.0)
            if len(self.play_list) > 0:
                if (self.current_track + 1) < len(self.play_list):
                    self.current_track = self.current_track + 1
                else:
                    self.current_track = 0
                    self.delay_close()
                self.load_signal.emit()
            else:
                self.player.stop()
                self.delay_close()

    def delay_close(self):
        file = join_path(self.folder, MyVideoConvert.SAVE_FILE)
        save_json(file, self.convert_log)

        main = find_main_widget(self.parent())
        if main:
            if main.model.select and main.model.select == self.folder:
                main.model.makeSelect(self.folder, False)

        timer = threading.Timer(1, self.close_signal.emit)
        timer.start()

    def __frame(self, frame: QVideoFrame):
        # print("frame", frame)
        if self.ready:
            if self.current_frame > 0:
                idx = str(self.current_frame).zfill(3)
                out = join_path(self.frame_folder, f"{self.current_track + self.track_offset}{idx}.jpg")
                self.progress_bar.setValue(self.current_frame)

                img = frame.toImage()
                img.save(out)
                if int(self.current_frame % 5) == 0:
                    img_loaded = MyImageSource.from_image(img, out).as_size(MyVideoConvert.THUMB_SIZE)
                    self.preview.on_image.emit(img_loaded)
            # self.next_signal.emit()
            self.__next()

    @Slot()
    def duration(self, duration: int):
        if duration == 0:
            self.txt_total.setText("")
        else:
            self.total_time = duration
            self.txt_total.setText(str(datetime.timedelta(seconds=round(duration / 1000))))
            self.convert_log[self.current_track]["duration"] = self.txt_total.text()

    def __ready(self):
        self.ready = True
        self.__next()

    @Slot()
    def media_state(self, state: QtMultimedia.QMediaPlayer.MediaStatus):
        print(state, self.player.duration())
        if state is QtMultimedia.QMediaPlayer.MediaStatus.LoadedMedia:
            self.but_play.setEnabled(True)
            self.convert_log[self.current_track]["res"] = self.player.metaData().stringValue(QMediaMetaData.Resolution)
            self.convert_log[self.current_track]["bps"] = self.player.metaData().stringValue(QMediaMetaData.VideoBitRate)
            self.show_codec()
            self.show_audio_codec()
            self.convert_log[self.current_track]["codec"] = self.but_codec.text()
            self.convert_log[self.current_track]["a_codec"] = self.but_audio_codec.text()

            if 0 < self.current_track < len(self.play_list):
                self.__play()
        elif state is QtMultimedia.QMediaPlayer.MediaStatus.BufferedMedia:
            self.but_play.setEnabled(False)
            self.player.pause()
            self.player.setPlaybackRate(0.0)
            self.player.setPosition(5000)
            timer = threading.Timer(2, self.__ready)
            timer.start()
        else:
            self.but_play.setEnabled(False)
            self.txt_total.setText("")
