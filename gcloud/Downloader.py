
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from http.client import HTTPConnection
import os
import threading
import urllib.parse

from gi.repository import GLib

from gcloud.const import State

CHUNK = 2 ** 16  # 64k


class Downloader(threading.Thread):
    '''后台下载的线程, 每个任务应该对应一个Downloader对象.

    当程序退出时, 下载线程会保留现场, 以后可以继续下载.
    断点续传功能基于HTTP/1.1 的Range, 百度网盘对它有很好的支持.
    '''

    times_to_flush = 0
    threshold_to_flush = 10
    fh = None

    def __init__(self, parent, task, tree_iter, cookie, tokens):
        print('new worker inited:')
        print(task)
        threading.Thread.__init__(self)
        self.parent = parent
        self.cookie = cookie
        self.tokens = tokens
        self.task = task
        self.tree_iter = tree_iter

        url_info = urllib.parse.urlparse(task['link'])
        self.pool = HTTPConnection(url_info.netloc)

        self.init_files()

    def init_files(self):
        print('Downloader.init_files()')
        if not os.path.exists(self.task['saveDir']):
            os.makedirs(task['saveDir'], exist_ok=True)
        self.filepath = os.path.join(
                self.task['saveDir'], self.task['saveName']) 
        truncated = False
        if os.path.exists(self.filepath):
            truncated = True
            if self.task['size'] == self.task['currRange']:
                print('File exists and has same size, quit!')
                self.finished()
                return
        else:
            self.task['currRange'] = 0
        self.fh = open(self.filepath, 'wb')
        if not truncated:
            self.fh.truncate(self.task['size'])
        else:
            self.fh.seek(self.task['currRange'])

    def destroy(self):
        '''自毁'''
        print('Downloader.destroy()')
        self.pause()

    def run(self):
        '''实现了Thread的方法, 线程启动入口'''
        if self.fh:
            self.download()

    def download(self):
        while True:
            if self.task['state'] == State.DOWNLOADING:
                range_ = self.get_range()
                if range_:
                    self.request_bytes(range_)
                continue
            elif (self.task['state'] == State.FINISHED or 
                    self.task['state'] == State.PAUSED):
                self.flush()
                self.close()
                self.fh = None
                break
            elif self.task['state'] == State.CANCELED:
                self.fh.flush()
                self.fh.close()
                self.fh = None
                os.remove(self.filepath)
                break

    def pause(self):
        '''暂停下载任务'''
        print('DOwnloader.pause() --')
        self.task['state'] = State.PAUSED

    def stop(self):
        '''停止下载, 并删除之前下载的片段'''
        self.task['state'] = State.CANCELED

    def finished(self):
        print('Downloader.finished() --')
        self.task['state'] = State.FINISHED

    def get_range(self):
        if self.task['currRange'] >= self.task['size']:
            self.finished()
            return None
        start = self.task['currRange']
        stop = min(start + CHUNK, self.task['size'])
        return (start, stop)

    def request_bytes(self, range_):
        self.pool.request('GET', self.task['link'], headers={
            'Range': 'bytes={0}-{1}'.format(range_[0], range_[1]-1),
            'Connection': 'Keep-Alive',
            #'Cookie': self.cookie.header_output(),
            })
        resp = self.pool.getresponse()
        block = resp.read()
        self.write_bytes(range_, block)

    def write_bytes(self, range_, block):
        print('write bytes:', range_)
        print('block size:', len(block))
        self.task['currRange'] = range_[1]

        self.task['percent'] = int(
                self.task['currRange'] / self.task['size'] * 100)
        GLib.idle_add(
                self.parent.update_treeview,
                self.task, self.tree_iter)
        self.fh.write(block)
        self.times_to_flush = self.times_to_flush + 1
        if self.times_to_flush >= self.threshold_to_flush:
            self.fh.flush()
            self.times_to_flush = 0
