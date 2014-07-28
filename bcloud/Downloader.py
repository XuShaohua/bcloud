
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import multiprocessing
import os
import threading
import time

from urllib import request
from gi.repository import GLib
from gi.repository import GObject

from bcloud.const import State
from bcloud.net import ForbiddenHandler
from bcloud import pcs

CHUNK_SIZE = 131072 # 128K
RETRIES = 5             # 下载数据出错时重试的次数
TIMEOUT = 20
THRESHOLD_TO_FLUSH = 100  # 磁盘写入数据次数超过这个值时, 就进行一次同步.

(NAME_COL, PATH_COL, FSID_COL, SIZE_COL, CURRSIZE_COL, LINK_COL,
    ISDIR_COL, SAVENAME_COL, SAVEDIR_COL, STATE_COL, STATENAME_COL,
    HUMANSIZE_COL, PERCENT_COL) = list(range(13))


class Downloader(threading.Thread, GObject.GObject):
    '''后台下载的线程, 每个任务应该对应一个Downloader对象.

    当程序退出时, 下载线程会保留现场, 以后可以继续下载.
    断点续传功能基于HTTP/1.1 的Range, 百度网盘对它有很好的支持.
    '''

    __gsignals__ = {
            'started': (GObject.SIGNAL_RUN_LAST,
                # fs_id
                GObject.TYPE_NONE, (str, )),
            'received': (GObject.SIGNAL_RUN_LAST,
                # fs-id, current-size
                GObject.TYPE_NONE, (str, GObject.TYPE_INT64)),
            'downloaded': (GObject.SIGNAL_RUN_LAST, 
                # fs_id
                GObject.TYPE_NONE, (str, )),
            'disk-error': (GObject.SIGNAL_RUN_LAST,
                # fs_id
                GObject.TYPE_NONE, (str, )),
            'network-error': (GObject.SIGNAL_RUN_LAST,
                # fs_id
                GObject.TYPE_NONE, (str, )),
            }

    def __init__(self, parent, row, cookie, tokens):
        threading.Thread.__init__(self)
        self.daemon = True
        GObject.GObject.__init__(self)

        self.parent = parent
        self.cookie = cookie
        self.tokens = tokens
        self.row = row[:]  # 复制一份
        self.fh = None
        self.red_url = ''
        self.flush_count = 0

    def init_files(self):
        row = self.row
        if not os.path.exists(self.row[SAVEDIR_COL]):
            os.makedirs(row[SAVEDIR_COL], exist_ok=True)
        self.filepath = os.path.join(row[SAVEDIR_COL], row[SAVENAME_COL]) 
        self.tmp_filepath = self.filepath + '.part'
        if os.path.exists(self.filepath):
            curr_size = os.path.getsize(self.filepath)
            # file exists and size matches
            if curr_size == row[SIZE_COL]:
                self.finished(move=False)
            # overwrite existing file
            else:
                os.remove(self.filepath)
                self.fh = open(self.tmp_filepath, 'wb')
                self.row[CURRSIZE_COL] = 0
        elif os.path.exists(self.tmp_filepath):
            self.fh = open(self.tmp_filepath, 'ab')
        else:
            self.fh = open(self.tmp_filepath, 'wb')
            self.row[CURRSIZE_COL] = 0

    def destroy(self):
        '''自毁'''
        self.pause()

    def run(self):
        '''实现了Thread的方法, 线程启动入口'''
        self.init_files()
        if self.fh:
            self.get_download_link()

    def get_download_link(self):
        self.red_url = pcs.get_download_link(
                self.cookie, self.tokens, self.row[PATH_COL])
        if not self.red_url:
            print('Failed to get download link')
            self.network_error()
        self.download()

    def download(self):
        self.emit('started', self.row[FSID_COL])
        content_range = 'bytes={0}-{1}'.format(
                self.row[CURRSIZE_COL], self.row[SIZE_COL]-1)
        opener = request.build_opener(ForbiddenHandler)
        opener.addheaders = [('Range', content_range)]
        for i in range(RETRIES):
            try:
                req = opener.open(self.red_url)
                break
            except OSError as e:
                print(e)
                if i == (RETRIES - 1):
                    self.network_error()
                    return

        range_from = self.row[CURRSIZE_COL]
        range_to = range_from
        filesize_dl = 0
        start_time = time.time()

        while self.row[STATE_COL] == State.DOWNLOADING:
            try:
                buff = req.read(CHUNK_SIZE)
            except Exception as e:
                print(e)
                self.network_error()
                break
            if not buff:
                if self.row[CURRSIZE_COL] == self.row[SIZE_COL]:
                    self.finished()
                else:
                    self.network_error()
                break
            range_from, range_to = range_to, range_to + len(buff)
            if not self.fh or self.row[STATE_COL] != State.DOWNLOADING:
                break
            self.emit('received', self.row[FSID_COL], range_to)
            self.fh.write(buff)
            self.flush_count = self.flush_count + 1
            if self.flush_count > THRESHOLD_TO_FLUSH:
                self.fh.flush()
                self.flush_count = 0
            self.row[CURRSIZE_COL] += len(buff)
        self.close_file()

    def pause(self):
        '''暂停下载任务'''
        self.row[STATE_COL] = State.PAUSED
        self.close_file()

    def stop(self):
        '''停止下载, 并删除之前下载的片段'''
        self.row[STATE_COL] = State.CANCELED
        self.close_file()
        os.remove(self.tmp_filepath)

    def close_file(self):
        if self.fh and not self.fh.closed:
            self.fh.flush()
            self.fh.close()
            self.fh = None

    def finished(self, move=True):
        self.row[STATE_COL] = State.FINISHED
        self.emit('downloaded', self.row[FSID_COL])
        self.close_file()
        if move and os.path.exists(self.tmp_filepath):
            os.rename(self.tmp_filepath, self.filepath)

    def network_error(self):
        self.row[STATE_COL] = State.ERROR
        self.emit('network-error', self.row[FSID_COL])
        self.close_file()

GObject.type_register(Downloader)
