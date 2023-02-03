from multiprocessing import Queue
from multiprocessing.managers import BaseManager
from typing import Callable

text_queue = Queue()


class TextOut(object):
    func: Callable[[str], None] = print
    progress_max: Callable[[int], None] = print
    progress: Callable[[int], None] = print

    @classmethod
    def start(cls):
        class TextOutManager(BaseManager):
            pass

        TextOutManager.register('get_queue', callable=lambda: text_queue)
        m = TextOutManager(address=('', 8001), authkey=b'a')
        server = m.get_server()
        server.serve_forever()

    @staticmethod
    def out(message: str) -> None:
        TextOut.func(message)

    @staticmethod
    def progress_start() -> None:
        TextOut.out_progress_max(0)

    @staticmethod
    def progress_end() -> None:
        TextOut.out_progress_max(1)
        TextOut.out_progress(1)

    @staticmethod
    def out_progress_max(max_val: int) -> None:
        # print(max_val, TextOut.progress_max)
        TextOut.progress_max(max_val)

    @staticmethod
    def out_progress(val: int) -> None:
        # print(val, TextOut.progress)
        TextOut.progress(val)
