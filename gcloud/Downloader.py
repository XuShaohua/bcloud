
from threading import Thread
import urllib.parse

import urllib3

class Downloader(Thread):
    '''后台下载的线程, 每个任务应该对应一个Downloader对象.

    当程序退出时, 下载线程会保留现场, 以后可以继续下载.
    断点续传功能基于HTTP/1.1 的Range, 百度网盘对它有很好的支持.
    '''

    def __init__(self, cookie, tokens, targ_path, url):
        url_info = urllib.parse.urlparse(url)
        self.pool = urllib3.HTTPConnectionPool(url_info.netloc)

    def run(self):
        pass

    def pause(self):
        '''暂停下载任务'''
        pass

    def resume(self):
        pass

    def stop(self):
        pass

    def remove(self):
        '''删除这个下载任务以及已经下载好的文件'''
        pass
