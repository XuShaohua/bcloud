
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

CHUNK_SIZE = 16384      # 16K
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

    fh = None
    red_url = ''
    flush_count = 0

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
        GObject.GObject.__init__(self)

        self.parent = parent
        self.cookie = cookie
        self.tokens = tokens
        self.row = row[:]  # 复制一份

    def init_files(self):
        row = self.row
        if not os.path.exists(self.row[SAVEDIR_COL]):
            os.makedirs(row[SAVEDIR_COL], exist_ok=True)
        self.filepath = os.path.join(row[SAVEDIR_COL], row[SAVENAME_COL]) 
        if os.path.exists(self.filepath):
            curr_size = os.path.getsize(self.filepath)
            if curr_size == row[SIZE_COL]:
                self.finished()
                return
            elif curr_size < row[SIZE_COL]:
                if curr_size == row[CURRSIZE_COL]:
                    self.fh = open(self.filepath, 'ab')
                elif curr_size < row[CURRSIZE_COL]:
                    self.fh = open(self.filepath, 'ab')
                    row[CURRSIZE_COL] = curr_size
                else:
                    if 0 < row[CURRSIZE_COL]:
                        self.fh = open(self.filepath, 'ab')
                        self.fh.seek(row[CURRSIZE_COL])
                    else:
                        self.fh = open(self.filepath, 'wb')
                        self.row[CURRSIZE_COL] = 0
            else:
                self.fh = open(self.filepath, 'wb')
                self.row[CURRSIZE_COL] = 0
        else:
            self.fh = open(self.filepath, 'wb')
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
        meta = pcs.get_metas(self.cookie, self.tokens, self.row[PATH_COL])
        if not meta or meta['errno'] != 0 or 'info' not in meta:
            self.network_error()
            return
        pcs_files = meta['info']
        if not pcs_files:
            print('pcs_files in meta is empty, abort')
            self.network_error()
            return
        pcs_file = pcs_files[0]
        if str(pcs_file['fs_id']) != self.row[FSID_COL]:
            print('FSID not match, abort.')
            self.network_error()
            return
        dlink = pcs_file['dlink']
        red_url, req_id = pcs.get_download_link(self.cookie, dlink)
        if not req_id:
            self.network_error()
        else:
            self.red_url = red_url
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
            except OSError as e:
                print(e)
                if i == (RETRIES - 1):
                    self.network_error()
                    return
            else:
                break

        range_from = self.row[CURRSIZE_COL]
        range_to = range_from
        filesize_dl = 0
        start_time = time.time()

        while self.row[STATE_COL] == State.DOWNLOADING:
            try:
                buff = req.read(CHUNK_SIZE)
            except Exception as e:
                self.network_error()
                return
            if not buff:
                self.finished()
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
        self.close_file()

    def pause(self):
        '''暂停下载任务'''
        self.row[STATE_COL] = State.PAUSED
        self.close_file()

    def stop(self):
        '''停止下载, 并删除之前下载的片段'''
        self.row[STATE_COL] = State.CANCELED
        self.close_file()
        os.remove(self.filepath)

    def close_file(self):
        if self.fh and not self.fh.closed:
            self.fh.flush()
            self.fh.close()
            self.fh = None

    def finished(self):
        self.row[STATE_COL] = State.FINISHED
        self.emit('downloaded', self.row[FSID_COL])
        self.close_file()

    def network_error(self):
        self.row[STATE_COL] = State.ERROR
        self.emit('network-error', self.row[FSID_COL])
        self.close_file()

GObject.type_register(Downloader)
