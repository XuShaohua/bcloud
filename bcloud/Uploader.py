
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os
import sys
import threading

from gi.repository import GLib
from gi.repository import GObject

from bcloud import pcs

(FID_COL, NAME_COL, SOURCEPATH_COL, PATH_COL, SIZE_COL,
    CURRSIZE_COL, STATE_COL, STATENAME_COL, HUMANSIZE_COL,
    PERCENT_COL, TOOLTIP_COL, THRESHOLD_COL) = list(range(12))

class State:
    '''下载状态常量'''
    UPLOADING = 0
    WAITING = 1
    PAUSED = 2
    FINISHED = 3
    CANCELED = 4
    ERROR = 5

SLICE_THRESHOLD = 2 ** 18  # 256k, 小于这个值, 不允许使用分片上传


class Uploader(threading.Thread, GObject.GObject):

    __gsignals__ = {
            # 一个新的文件分片完成上传
            'slice-sent': (GObject.SIGNAL_RUN_LAST,
                # fid, slice_end, md5 
                GObject.TYPE_NONE, (GObject.TYPE_INT, GObject.TYPE_INT64, str)),
            # 请求UploadPage来合并文件分片
            'merge-files': (GObject.SIGNAL_RUN_LAST,
                # fid
                GObject.TYPE_NONE, (GObject.TYPE_INT, )),
            # 上传完成, 这个信号只有rapid_upload/upload_small_file才使用
            'uploaded': (GObject.SIGNAL_RUN_LAST, 
                # fid
                GObject.TYPE_NONE, (GObject.TYPE_INT, )),
            'disk-error': (GObject.SIGNAL_RUN_LAST,
                # fid
                GObject.TYPE_NONE, (GObject.TYPE_INT, )),
            'network-error': (GObject.SIGNAL_RUN_LAST,
                # fid
                GObject.TYPE_NONE, (GObject.TYPE_INT, )),
            }

    is_slice_upload = False

    def __init__(self, parent, row, cookie, tokens):
        '''
        parent    - UploadPage
        row       - UploadPage.liststore中的一个记录
        '''
        threading.Thread.__init__(self)
        GObject.GObject.__init__(self)

        self.parent = parent
        self.cookie = cookie
        self.tokens = tokens

        self.row = row[:]

    def run(self):
        #self.check_exists()
        # 如果文件大小小于4M, 就直接上传, 不支持断点续传(没必要).
        # 否则先尝试快速上传模式, 如果没有中的话, 就再进行分片上传.
        # 分片上传, 是最费事的, 也最占带宽.
        # 分片上传, 支持断点续传.
        if self.row[SIZE_COL] > SLICE_THRESHOLD:
            self.rapid_upload()
        else:
            self.slice_upload()

    # Open API
    def pause(self):
        self.row[STATE_COL] = State.PAUSED
        #if self.is_slice_upload:

    # Open API
    def stop(self):
        self.row[STATE_COL] = State.CANCELED

    def check_exists(self):
        meta = pcs.get_metas(self.row[PATH_COL])

    def rapid_upload(self):
        '''快速上传.

        如果失败, 就自动调用分片上传.
        '''
        info = pcs.rapid_upload(
            self.cookie, self.tokens,
            self.row[SOURCEPATH_COL], self.row[PATH_COL])
        if info and info['md5'] and info['fs_id']:
            self.emit('uploaded', self.row[FID_COL])
        else:
            self.slice_upload()

    def slice_upload(self):
        '''分片上传'''
        self.is_slice_upload = True
        fid = self.row[FID_COL]
        slice_start = self.row[CURRSIZE_COL]
        slice_end = self.row[CURRSIZE_COL]
        file_size = os.path.getsize(self.row[SOURCEPATH_COL])
        if file_size < slice_start:
            self.emit('disk-error', fid)
            return
        elif file_size == slice_start and slice_start == self.row[SIZE_COL]:
            self.emit('uploaded', fid)
            return
        fh = open(self.row[SOURCEPATH_COL], 'rb')
        fh.seek(slice_start)
        while self.row[STATE_COL] == State.UPLOADING:
            if slice_end >= file_size:
                self.emit('merge-files', self.row[FID_COL])
                break
            slice_start = slice_end
            slice_end = min(slice_start + self.row[THRESHOLD_COL], file_size)
            data = fh.read(slice_end - slice_start)
            slice_end = slice_start + len(data)
            info = pcs.slice_upload(self.cookie, data)
            if info and 'md5' in info:
                self.emit('slice-sent', fid, slice_end, info['md5'])
            else:
                self.emit('network-error', fid)
                break
        if not fh.closed:
            fh.close()
        return

GObject.type_register(Uploader)
