
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os
import sys
import threading

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from bcloud.const import UploadState as State
from bcloud.const import UploadMode
from bcloud.log import logger
from bcloud import pcs

(FID_COL, NAME_COL, SOURCEPATH_COL, PATH_COL, SIZE_COL,
    CURRSIZE_COL, STATE_COL, STATENAME_COL, HUMANSIZE_COL,
    PERCENT_COL, TOOLTIP_COL, THRESHOLD_COL) = list(range(12))


SLICE_THRESHOLD = 2 ** 18  # 256k, 小于这个值, 不允许使用分片上传


class Uploader(threading.Thread, GObject.GObject):

    __gsignals__ = {
        # 一个新的文件分片完成上传
        # fid, slice_end, md5 
        'slice-sent': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                       (GObject.TYPE_INT, GObject.TYPE_INT64, str)),
        # 请求UploadPage来合并文件分片
        'merge-files': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                        (GObject.TYPE_INT, )),
        # 上传完成, 这个信号只有rapid_upload/upload_small_file才使用
        'uploaded': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                     (GObject.TYPE_INT, )),
        'disk-error': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                       (GObject.TYPE_INT, )),
        'network-error': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                          (GObject.TYPE_INT, )),
    }

    is_slice_upload = False

    def __init__(self, parent, row, cookie, tokens):
        '''
        parent    - UploadPage
        row       - UploadPage.liststore中的一个记录
        '''
        threading.Thread.__init__(self)
        GObject.GObject.__init__(self)
        self.daemon = True

        self.parent = parent
        self.cookie = cookie
        self.tokens = tokens
        self.upload_mode = self.parent.app.profile['upload-mode']

        self.row = row[:]

    def run(self):
        if self.check_exists() and self.upload_mode == UploadMode.IGNORE:
            self.emit('uploaded', self.row[FID_COL])
            return

        # 检查上传的目录是否存在, 不存在创建
        self.mkdir(os.path.dirname(self.row[PATH_COL]))

        # 如果文件大小小于4M, 就直接上传, 不支持断点续传(没必要).
        # 否则先尝试快速上传模式, 如果没有中的话, 就再进行分片上传.
        # 分片上传, 是最费事的, 也最占带宽.
        # 分片上传, 支持断点续传.
        if self.row[SIZE_COL] > SLICE_THRESHOLD:
            self.rapid_upload()
        else:
            self.upload()

    # Open API
    def pause(self):
        self.row[STATE_COL] = State.PAUSED

    # Open API
    def stop(self):
        self.row[STATE_COL] = State.CANCELED

    def check_exists(self):
        meta = pcs.get_metas(self.cookie, self.tokens, self.row[PATH_COL])
        return meta and meta.get('errno', 12) == 0

    def check_dir_exists(self, remotepath):
        meta = pcs.get_metas(self.cookie, self.tokens, remotepath)
        return meta.get('errno', 12) == 0

    def mkdir(self, remotepath):
        if not self.check_dir_exists(remotepath):
            return pcs.mkdir(self.cookie, self.tokens, remotepath)

    def upload(self):
        '''一般上传模式.

        使用这种方式上传, 不可以中断上传过程, 但因为只用它来上传小的文件, 所以
        最终的影响不会很大.'''
        info = pcs.upload(self.cookie, self.row[SOURCEPATH_COL],
                          self.row[PATH_COL], self.upload_mode)
        if info:
            self.emit('uploaded', self.row[FID_COL])
        else:
            self.emit('network-error', self.row[FID_COL])

    def rapid_upload(self):
        '''快速上传.

        如果失败, 就自动调用分片上传.
        '''
        info = pcs.rapid_upload(self.cookie, self.tokens,
                                self.row[SOURCEPATH_COL], self.row[PATH_COL],
                                self.upload_mode)
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
