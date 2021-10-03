import sys
import traceback
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot, QThread


class Worker(QObject):
    done = Signal()
    error = Signal(tuple)
    result = Signal(object)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()

        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
            if result:
                self.result.emit(result)
        except:
            traceback.print_exc()
            exec_type, value = sys.exc_info()[:2]
            self.error.emit((exec_type, value, traceback.format_exc()))
        finally:
            self.done.emit()


class MyThread:
    thread_pool = {}

    def __init__(self, name):
        self.name = name
        self.thread = QThread()
        self.worker = None
        self.run_before = None
        self.run_finish = None
        self.cancel_restart = None

    def set_run(self, *args, **kwargs):
        self.worker = Worker(*args, **kwargs, thread=self.thread)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self.worker.deleteLater)
        self.worker.done.connect(self.done)

    def on_finish(self, on_finish=None, on_result=None, on_before=None):
        if self.worker:
            if on_result:
                self.worker.result.connect(on_result)
        self.run_before = on_before
        self.run_finish = on_finish

    def start(self) -> None:
        if self.name in MyThread.thread_pool:
            MyThread.thread_pool[self.name].cancel_restart = self.__start_up
            MyThread.thread_pool[self.name].thread.requestInterruption()
        else:
            self.__start_up()

    def __start_up(self) -> None:
        MyThread.thread_pool[self.name] = self
        if self.run_before:
            self.run_before()
        self.thread.start()

    @Slot()
    def done(self) -> None:
        self.thread.quit()
        self.thread.wait()

        if self.run_finish:
            self.run_finish()

        MyThread.thread_pool.pop(self.name, None)
        self.thread = None
        self.worker = None

        if self.cancel_restart:
            self.cancel_restart()
