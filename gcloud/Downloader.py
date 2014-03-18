
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from http.client import HTTPConnection
import os
import threading
import urllib.parse

from gi.repository import GLib
from gi.repository import GObject

from gcloud.const import State

CHUNK = 2 ** 18  # 256k 
RETRIES = 3
THRESHOLD_TO_FLUSH = 10

(NAME_COL, PATH_COL, FSID_COL, SIZE_COL, CURRSIZE_COL, LINK_COL,
    ISDIR_COL, SAVENAME_COL, SAVEDIR_COL, STATE_COL, STATENAME_COL,
    HUMANSIZE_COL, PERCENT_COL) = list(range(13))

class Downloader(threading.Thread, GObject.GObject):
    '''后台下载的线程, 每个任务应该对应一个Downloader对象.

    当程序退出时, 下载线程会保留现场, 以后可以继续下载.
    断点续传功能基于HTTP/1.1 的Range, 百度网盘对它有很好的支持.
    '''

    times_to_flush = 0
    fh = None

    __gsignals__ = {
            'received': (GObject.SIGNAL_RUN_LAST,
                # fs-id, current-size
                GObject.TYPE_NONE, (GObject.TYPE_LONG, GObject.TYPE_LONG)),
            'downloaded': (GObject.SIGNAL_RUN_LAST, 
                # fs_id
                GObject.TYPE_NONE, (GObject.TYPE_LONG, )),
            'disk-error': (GObject.SIGNAL_RUN_LAST,
                # fs_id
                GObject.TYPE_NONE, (GObject.TYPE_LONG, )),
            'network-error': (GObject.SIGNAL_RUN_LAST,
                # fs_id
                GObject.TYPE_NONE, (GObject.TYPE_LONG, )),
            }

    def __init__(self, parent, row, cookie, tokens):
        threading.Thread.__init__(self)
        GObject.GObject.__init__(self)
        print('new worker inited:')

        self.parent = parent
        self.cookie = cookie
        self.tokens = tokens

        self.row = row[:]  # 复制一份
        print(self.row)

        url_info = urllib.parse.urlparse(self.row[LINK_COL])
        self.pool = HTTPConnection(url_info.netloc)

    def init_files(self):
        row = self.row
        if not os.path.exists(self.row[SAVEDIR_COL]):
            os.makedirs(row[SAVEDIR_COL], exist_ok=True)
        self.filepath = os.path.join(row[SAVEDIR_COL], row[SAVENAME_COL]) 
        truncated = False
        if os.path.exists(self.filepath):
            truncated = True
            stat = os.stat(self.filepath)
            print(stat)
            print(row)
            if (row[SIZE_COL] == stat.st_size and 
                    stat.st_size == stat.st_blocks * 512):
                print('File exists and has same size, quit!')
                self.finished()
                return
        self.fh = open(self.filepath, 'wb')
        if not truncated:
            self.fh.truncate(row[SIZE_COL])
        else:
            self.fh.seek(row[CURRSIZE_COL])

    def destroy(self):
        '''自毁'''
        print('Downloader.destroy()')
        self.pause()

    def run(self):
        '''实现了Thread的方法, 线程启动入口'''
        print('Downloader.run() --')
        self.init_files()
        if self.fh:
            self.download()

    def download(self):
        print('Downloader.download() ')
        while True:
            if self.row[STATE_COL] == State.DOWNLOADING:
                range_ = self.get_range()
                if range_:
                    self.request_bytes(range_)
                continue
            elif (self.row[STATE_COL] == State.FINISHED or 
                    self.row[STATE_COL] == State.PAUSED):
                self.fh.flush()
                self.fh.close()
                self.fh = None
                break
            elif self.row[STATE_COL] == State.CANCELED:
                self.fh.flush()
                self.fh.close()
                self.fh = None
                os.remove(self.filepath)
                break

    def pause(self):
        '''暂停下载任务'''
        print('Downloader.pause() --')
        self.row[STATE_COL] = State.PAUSED

    def stop(self):
        '''停止下载, 并删除之前下载的片段'''
        print('Downloader.stop() ')
        self.row[STATE_COL] = State.CANCELED

    def finished(self):
        print('Downloader.finished() --')
        self.row[STATE_COL] = State.FINISHED
        print(self.row[FSID_COL], self.row[STATE_COL])
        self.emit('downloaded', self.row[FSID_COL])

    def get_range(self):
        if self.row[CURRSIZE_COL] >= self.row[SIZE_COL]:
            self.finished()
            return None
        start = self.row[CURRSIZE_COL]
        stop = min(start + CHUNK, self.row[SIZE_COL])
        return (start, stop)

    def request_bytes(self, range_):
        self.pool.request('GET', self.row[LINK_COL], headers={
            'Range': 'bytes={0}-{1}'.format(range_[0], range_[1]-1),
            'Connection': 'Keep-Alive',
            #'Cookie': self.cookie.header_output(),
            })
        for _ in range(RETRIES):
            try:
                resp = self.pool.getresponse()
                block = resp.read()
                self.write_bytes(range_, block)
                return
            except OSError as e:
                print(e)
        self.emit('network-error', self.row[FSID_COL])

    def write_bytes(self, range_, block):
        print('write bytes() :', len(block))
        self.row[CURRSIZE_COL] = range_[1]
        self.emit('received', self.row[FSID_COL], self.row[CURRSIZE_COL])
        self.fh.write(block)
        self.times_to_flush = self.times_to_flush + 1
        if self.times_to_flush >= THRESHOLD_TO_FLUSH:
            self.fh.flush()
            self.times_to_flush = 0
GObject.type_register(Downloader)
