import asyncio

from myparser.ParserCommon import get_html_js
from myqt.MyQtWorker import MyThread, MyThreadPool

from myparser.cosplay import CosplayParserBase
from myparser.cosplay import xinmeitulu, nhentai, eyecoser, jphentai, v2ph, wnacg, ip162, xiannvtu, xsnvshen, asiapretty


class CosplayParser(object):

    def __init__(self):
        print(CosplayParserBase.subclasses)
        for i in CosplayParserBase.subclasses:
            print(i.tag)

    @staticmethod
    def parse(url: str, *args, **kwargs):
        for i in CosplayParserBase.subclasses:
            if url.startswith(i.tag):
                MyThreadPool.start(None, None, None, None, i.parse, url, *args, **kwargs, can_cancel=True)
                # run_thread = MyThread(None)
                # run_thread.set_run(i.parse, url, *args, **kwargs)
                # run_thread.start()
                break
