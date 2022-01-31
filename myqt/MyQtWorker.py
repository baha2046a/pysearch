import random
import string
import sys
import traceback
from typing import Callable, Any

from PySide6.QtCore import *


def random_name(n):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


class Worker(QObject):
    done = Signal()
    error = Signal(tuple)
    result = Signal(object)

    def __init__(self, fun: Callable[[Any], Any], *args, **kwargs):
        super().__init__(None)

        self.fun = fun
        self.args = args
        self.kwargs = kwargs

    @Slot(None, result=None)
    def run(self) -> None:
        try:
            result = self.fun(*self.args, **self.kwargs)
            if result is not None:
                self.result.emit(result)
        except Exception as e:
            print(e)
            traceback.print_exc()
            exec_type, value = sys.exc_info()[:2]
            self.error.emit((exec_type, value, traceback.format_exc()))
        finally:
            self.done.emit()


class MyThread:
    thread_pool = {}
    text_out = Signal(str)

    def __init__(self, name):
        if not name:
            name = random_name(8)
            print(name)
        self.name = name
        self.thread = QThread()
        self.worker = None
        self.run_before = None
        self.run_finish = None
        self.cancel_restart = None
        #self.text_out.connect(TextOut.out)

    def set_run(self, fun: Callable[[Any], Any], *args, **kwargs):
        self.worker = Worker(fun, *args, **kwargs, thread=self.thread)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self.worker.deleteLater)
        self.worker.done.connect(self.done)

    def on_finish(self,
                  on_finish: Callable[[], Any] = None,
                  on_result: Callable[[Any], Any] = None,
                  on_before: Callable[[], Any] = None):
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

    @Slot(None, result=None)
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
