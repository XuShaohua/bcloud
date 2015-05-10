# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import json
import multiprocessing
import os
from queue import Queue
import re
import threading
import time
import traceback

from urllib import request
from gi.repository import GLib
from gi.repository import GObject

from bcloud import const
from bcloud.const import State, DownloadMode
from bcloud import net
from bcloud import pcs
from bcloud import util
from bcloud.log import logger

CHUNK_SIZE = 131072       # 128K
RETRIES = 3               # 连接失败时的重试次数
DOWNLOAD_RETRIES = 10     # 下载线程的重试次数
THRESHOLD_TO_FLUSH = 500  # 磁盘写入数据次数超过这个值时, 就进行一次同步.
SMALL_FILE_SIZE = 1048576 # 1M, 下载小文件时用单线程下载

(NAME_COL, PATH_COL, FSID_COL, SIZE_COL, CURRSIZE_COL, LINK_COL,
    ISDIR_COL, SAVENAME_COL, SAVEDIR_COL, STATE_COL, STATENAME_COL,
    HUMANSIZE_COL, PERCENT_COL) = list(range(13))

BATCH_FINISISHED, BATCH_ERROR = -1, -2

def get_tmp_filepath(dir_name, save_name):
    '''返回最终路径名及临时路径名'''
    filepath = os.path.join(dir_name, save_name)
    return filepath, filepath + '.part', filepath + '.bcloud-stat'


class DownloadBatch(threading.Thread):

    def __init__(self, id_, queue, url, lock, start_size, end_size, fh,
                 timeout):
        super().__init__()
        self.id_ = id_
        self.queue = queue
        self.url = url
        self.lock = lock
        self.start_size = start_size
        self.end_size = end_size
        self.fh = fh
        self.timeout = timeout
        self.stop_flag = False

    def run(self):
        self.download()

    def stop(self):
        self.stop_flag = True

    def get_req(self, start_size, end_size):
        '''打开socket'''
        logger.debug('DownloadBatch.get_req: %s, %s' % (start_size, end_size))
        opener = request.build_opener()
        content_range = 'bytes={0}-{1}'.format(start_size, end_size)
        opener.addheaders = [
            ('Range', content_range),
            ('User-Agent', const.USER_AGENT),
            ('Referer', const.PAN_REFERER),
        ]
        for i in range(RETRIES):
            try:
                return opener.open(self.url, timeout=self.timeout)
            except OSError:
                logger.error(traceback.format_exc())
        else:
            return None

    def download(self):
        offset = self.start_size
        req = self.get_req(offset, self.end_size)
        if not req:
            self.queue.put((self.id_, BATCH_ERROR), block=False)
            return

        while not self.stop_flag:
            for i in range(DOWNLOAD_RETRIES):
                if not req:
                    req = self.get_req(offset, self.end_size)
                    logger.debug('DownloadBatch.download: socket reconnected')
                try:
                    block = req.read(CHUNK_SIZE)
                    if block:
                        break
                except (OSError, AttributeError):
                    logger.error(traceback.format_exc())
                    req = None
            else:
                logger.error('DownloadBatch, block is empty: %s, %s, %s, %s' %
                             (offset, self.start_size, self.end_size, block))
                self.queue.put((self.id_, BATCH_ERROR), block=False)
                return

            with self.lock:
                if self.fh.closed:
                    return
                self.fh.seek(offset)
                self.fh.write(block)
                self.queue.put((self.id_, len(block)), block=False)
            offset = offset + len(block)
            # 下载完成
            if offset >= self.end_size:
                self.queue.put((self.id_, BATCH_FINISISHED), block=False)
                return


class Downloader(threading.Thread, GObject.GObject):
    '''管理每个下载任务, 使用了多线程下载.

    当程序退出时, 下载线程会保留现场, 以后可以继续下载.
    断点续传功能基于HTTP/1.1 的Range, 百度网盘对它有很好的支持.
    '''

    __gsignals__ = {
        'started': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (str, )),
        'received': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                     (str, GObject.TYPE_INT64, GObject.TYPE_INT64)),
        'downloaded': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (str, )),
        # FSID, tmp-filepath
        'disk-error': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (str, str)),
        'network-error': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (str, )),
    }

    def __init__(self, parent, row):
        threading.Thread.__init__(self)
        self.daemon = True
        GObject.GObject.__init__(self)

        self.cookie = parent.app.cookie
        self.tokens = parent.app.tokens
        self.default_threads = int(parent.app.profile['download-segments'])
        self.timeout = int(parent.app.profile['download-timeout'])
        self.download_mode = parent.app.profile['download-mode']
        self.row = row[:]

    def download(self):
        row = self.row
        if not os.path.exists(row[SAVEDIR_COL]):
            os.makedirs(row[SAVEDIR_COL], exist_ok=True)
        filepath, tmp_filepath, conf_filepath = get_tmp_filepath(
                row[SAVEDIR_COL], row[SAVENAME_COL]) 

        if os.path.exists(filepath):
            if self.download_mode == DownloadMode.IGNORE:
                self.emit('downloaded', row[FSID_COL])
                logger.debug('File exists, ignored!')
                return
            elif self.download_mode == DownloadMode.NEWCOPY:
                name, ext = os.path.splitext(filepath)
                filepath = '{0}_{1}{2}'.format(name, util.curr_time(), ext)

        url = pcs.get_download_link(self.cookie, self.tokens, row[PATH_COL])
        if not url:
            row[STATE_COL] = State.ERROR
            self.emit('network-error', row[FSID_COL])
            logger.warn('Failed to get url to download')
            return

        if os.path.exists(conf_filepath) and os.path.exists(tmp_filepath):
            with open(conf_filepath) as conf_fh:
                status = json.load(conf_fh)
            threads = len(status)
            file_exists = True
            fh = open(tmp_filepath, 'rb+')
            fh.seek(0)
        else:
            req = net.urlopen_simple(url)
            if not req:
                logger.warn('Failed to get url to download')
                self.emit('network-error', row[FSID_COL])
                return
            content_length = req.getheader('Content-Length')
            # Fixed: baiduPCS using non iso-8859-1 codec in http headers
            if not content_length:
                match = re.search('\sContent-Length:\s*(\d+)', str(req.headers))
                if not match:
                    logger.warn('Failed to get url to download')
                    self.emit('network-error', row[FSID_COL])
                    return
                content_length = match.group(1)
            size = int(content_length)
            if size == 0:
                open(filepath, 'a').close()
                self.emit('downloaded', row[FSID_COL])
                return
            elif size <= SMALL_FILE_SIZE:
                threads = 1
            else:
                threads = self.default_threads
            average_size, pad_size = divmod(size, threads)
            file_exists = False
            status = []
            fh = open(tmp_filepath, 'wb')
            try:
                fh.truncate(size)
            except (OSError, IOError):
                e = truncate.format_exc()
                logger.error(e)
                self.emit('disk-error', row[FSID_COL], tmp_filepath)
                return

        # task list
        tasks = []
        # message queue
        queue = Queue()
        # threads lock
        lock = threading.RLock()
        for id_ in range(threads):
            if file_exists:
                start_size, end_size, received = status[id_]
                if start_size + received >= end_size:
                    # part of file has been downloaded
                    continue
                start_size += received
            else:
                start_size = id_ * average_size
                end_size = start_size + average_size - 1
                if id_ == threads - 1:
                    end_size = end_size + pad_size + 1
                status.append([start_size, end_size, 0])
            task = DownloadBatch(id_, queue, url, lock, start_size, end_size,
                                 fh, self.timeout)
            tasks.append(task)

        for task in tasks:
            task.start()

        try:
            conf_count = 0
            done = 0
            self.emit('started', row[FSID_COL])
            while row[STATE_COL] == State.DOWNLOADING:
                id_, received = queue.get()
                # FINISHED
                if received == BATCH_FINISISHED:
                    done += 1
                    if done == len(tasks):
                        row[STATE_COL] = State.FINISHED
                        break
                    else:
                        continue
                # error occurs
                elif received == BATCH_ERROR:
                    row[STATE_COL] = State.ERROR
                    break
                status[id_][2] += received
                conf_count += 1
                # flush data and status to disk
                if conf_count > THRESHOLD_TO_FLUSH:
                    with lock:
                        if not fh.closed:
                            fh.flush()
                    with open(conf_filepath, 'w') as fh:
                        json.dump(status, fh)
                    conf_count = 0
                received_total = sum(t[2] for t in status)
                self.emit('received', row[FSID_COL], received, received_total)
        except Exception:
            logger.error(traceback.format_exc())
            row[STATE_COL] = State.ERROR
        with lock:
            if not fh.closed:
                fh.close()
        for task in tasks:
            if task.isAlive():
                task.stop()
        with open(conf_filepath, 'w') as fh:
            json.dump(status, fh)

        if row[STATE_COL] == State.CANCELED:
            os.remove(tmp_filepath)
            if os.path.exists(conf_filepath):
                os.remove(conf_filepath)
        elif row[STATE_COL] == State.ERROR:
            self.emit('network-error', row[FSID_COL])
        elif row[STATE_COL] == State.FINISHED:
            self.emit('downloaded', row[FSID_COL])
            os.rename(tmp_filepath, filepath)
            if os.path.exists(conf_filepath):
                os.remove(conf_filepath)

    def destroy(self):
        '''自毁'''
        self.pause()

    def run(self):
        '''实现了Thread的方法, 线程启动入口'''
        self.download()

    def pause(self):
        '''暂停下载任务'''
        self.row[STATE_COL] = State.PAUSED

    def stop(self):
        '''停止下载, 并删除之前下载的片段'''
        self.row[STATE_COL] = State.CANCELED

GObject.type_register(Downloader)
