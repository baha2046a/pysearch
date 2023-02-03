import asyncio
import random
import string
import sys
import time
import traceback
import weakref
from asyncio import AbstractEventLoop
from concurrent.futures import Future
from typing import Callable, Any, Optional

from PySide6 import QtCore
from PySide6.QtCore import Slot, Signal, QObject, QThread, QRunnable, QThreadPool, Qt, QCoreApplication, QEvent


def random_name(n):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


class MyRun(QRunnable):
    done = Signal()
    error = Signal(tuple)
    result = Signal(object)

    def __init__(self, future: Future, func: Callable[[Any], Any], *args, **kwargs):
        super().__init__()
        self.future = future
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
        except Exception as e:
            print(e)
            self.future.set_exception(e)
        else:
            self.future.set_result(result)


class Worker(QObject):
    done = Signal()
    error = Signal(tuple)
    result = Signal(object)

    def __init__(self, fun: Callable[[Any], Any], *args, **kwargs):
        super().__init__()

        self.fun = fun
        self.args = args
        self.kwargs = kwargs

    @Slot(result=None)
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

    @staticmethod
    def size() -> int:
        return len(MyThread.thread_pool)

    def __init__(self, name=None):
        if not name:
            name = random_name(8)
            print(name)
        self.name = name
        self.thread = QThread()
        self.worker = None
        self.run_before = None
        self.run_finish = None
        self.cancel_restart = None
        # self.text_out.connect(TextOut.out)

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

    @Slot(result=None)
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


class MyThreadPool:
    watch_list = {}
    cancel_list = []
    pending_list = {}
    map_result = {}

    @staticmethod
    def asyncio(func_to_run: Callable[[Any], Any], param: list = None):
        print("async start")
        if param is None:
            param = []
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        param.insert(0, loop)
        result = loop.run_until_complete(func_to_run(*param))
        loop.stop()
        loop.close()
        return result

    @staticmethod
    async def gather(*tasks, **kwargs):
        tasks = [task if isinstance(task, asyncio.Task) else asyncio.create_task(task) for task in tasks]
        try:
            return await asyncio.gather(*tasks, **kwargs)
        except Exception as e:
            print(e)
            for task in tasks:
                task.cancel()
            return True

    @staticmethod
    def size() -> int:
        return QThreadPool.globalInstance().activeThreadCount()
        # return len(MyThreadPool.watch_list)

    @staticmethod
    def map(name: Optional[str], in_list: list, func_to_run: Callable[[Any], Any]) -> list:
        if not name:
            name = random_name(12)
            while name in MyThreadPool.map_result:
                name = random_name(12)

        if name in MyThreadPool.map_result:
            return []

        MyThreadPool.map_result[name] = []

        def p_result(r):
            MyThreadPool.map_result[name].append(r)

        for data in in_list:
            MyThreadPool.start(None, None, p_result, p_result, func_to_run, data,
                               priority=QtCore.QThread.Priority.LowPriority)

        while len(MyThreadPool.map_result[name]) < len(in_list):
            QCoreApplication.processEvents()
            time.sleep(0.1)

        return MyThreadPool.map_result.pop(name)

    @staticmethod
    def start(name: Optional[str],
              on_start, on_result, on_error,
              func_to_run: Callable[[Any], Any],
              *args,
              can_cancel: bool = False,
              pending_when_exist: bool = True,
              priority=QtCore.QThread.Priority.NormalPriority,
              **kwargs):
        if not name:
            name = random_name(12)
            while name in MyThreadPool.watch_list:
                name = random_name(12)

        if not pending_when_exist and name in MyThreadPool.watch_list:
            return None

        f = Future()
        if can_cancel:
            def is_cancelled() -> bool:
                return name in MyThreadPool.cancel_list

            task = MyRun(f, func_to_run, *args, **kwargs, check_cancel=is_cancelled)
        else:
            task = MyRun(f, func_to_run, *args, **kwargs)

        w = FutureWatcher(name, future=f)

        if name in MyThreadPool.watch_list:
            MyThreadPool.pending_list[name] = lambda: MyThreadPool.__start(name, w, task, on_start, on_result, on_error)
            MyThreadPool.cancel_list.append(name)
        else:
            MyThreadPool.__start(name, w, task, on_start, on_result, on_error, priority)
        return w

    @staticmethod
    def cancel(name: str):
        if name in MyThreadPool.watch_list:
            MyThreadPool.cancel_list.append(name)

    @staticmethod
    def __start(name, w, task: QRunnable, on_start, on_result, on_error,
                priority: QtCore.QThread.Priority = QtCore.QThread.Priority.NormalPriority):
        MyThreadPool.watch_list[name] = w

        def done():
            MyThreadPool.watch_list.pop(name)
            if name in MyThreadPool.cancel_list:
                MyThreadPool.cancel_list.remove(name)
            w.deleteLater()
            if name in MyThreadPool.pending_list:
                MyThreadPool.pending_list.pop(name)()

        w.done.connect(lambda: done(), Qt.QueuedConnection)

        if on_start:
            on_start()

        if on_result:
            w.resultReady.connect(on_result, Qt.QueuedConnection)

        if on_error:
            w.exceptionReady.connect(on_error, Qt.QueuedConnection)

        QThreadPool.globalInstance().start(task)  # , priority=priority)


class FutureWatcher(QObject):
    done = Signal(Future)

    #: Emitted when the future is finished (i.e. returned a result
    #: or raised an exception)
    finished = Signal(Future)

    #: Emitted when the future was cancelled
    cancelled = Signal(Future)

    #: Emitted with the future's result when successfully finished.
    resultReady = Signal(object)

    #: Emitted with the future's exception when finished with an exception.
    exceptionReady = Signal(BaseException)

    # A private event type used to notify the watcher of a Future's completion
    __FutureDone = QEvent.registerEventType()

    def __init__(self, name: str, parent=None, future: Future = None, **kwargs):
        super(FutureWatcher, self).__init__(parent)
        self.__future = None
        self.name = name
        if future is not None:
            self.setFuture(future)

    def setFuture(self, future):
        """
        Set the future to watch.
        Raise a `RuntimeError` if a future is already set.
        Parameters
        ----------
        future : Future
        """
        if self.__future is not None:
            raise RuntimeError("Future already set")

        self.__future = future
        self_weak_ref = weakref.ref(self)

        def on_done(f):
            assert f is future
            self_ref = self_weak_ref()

            if self_ref is None:
                return

            try:
                QCoreApplication.postEvent(
                    self_ref, QEvent(QEvent.Type(FutureWatcher.__FutureDone)))
            except RuntimeError:
                # Ignore RuntimeErrors (when C++ side of QObject is deleted)
                # (? Use QObject.destroyed and remove the done callback ?)
                pass

        future.add_done_callback(on_done)

    def future(self):
        """
        Return the future.
        """
        return self.__future

    def result(self):
        """
        Return the future's result.
        Note
        ----
        This method is non-blocking. If the future has not yet completed
        it will raise an error.
        """
        try:
            return self.__future.result(timeout=0)
        except TimeoutError:
            raise RuntimeError()

    def exception(self):
        """
        Return the future's exception.
        """
        return self.__future.exception(timeout=0)

    def __emitSignals(self):
        assert self.__future is not None
        assert self.__future.done()

        if self.__future.cancelled():
            self.cancelled.emit(self.__future)
            self.done.emit(self.__future)
        elif self.__future.done():
            self.finished.emit(self.__future)
            self.done.emit(self.__future)
            if self.__future.exception():
                self.exceptionReady.emit(self.__future.exception())
            else:
                self.resultReady.emit(self.__future.result())
        else:
            assert False

    def customEvent(self, event):
        # Reimplemented.
        if event.type() == FutureWatcher.__FutureDone:
            self.__emitSignals()
        super(FutureWatcher, self).customEvent(event)
