
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os
import sys
import threading

from gi.repository import GLib
from gi.repository import GObject

from bcloud import pcs

(NAME_COL, SOURCEPATH_COL, PATH_COL, SIZE_COL, CURRSIZE_COL, 
    STATE_COL, STATENAME_COL, HUMANSIZE_COL, PERCENT_COL) = list(range(9))
RAPIDUPLOAD_THRESHOLD = 2 ** 22 # 4M

class Uploader(threading.Thread, GObject.GObject):

    __gsignals__ = {
            'slice-sent': (GObject.SIGNAL_RUN_LAST,
                # source_path, current-size
                GObject.TYPE_NONE, (str, GObject.TYPE_LONG)),
            'uploaded': (GObject.SIGNAL_RUN_LAST, 
                # source_path
                GObject.TYPE_NONE, (str, )),
            'disk-error': (GObject.SIGNAL_RUN_LAST,
                # source_path
                GObject.TYPE_NONE, (str, )),
            'network-error': (GObject.SIGNAL_RUN_LAST,
                # source_path
                GObject.TYPE_NONE, (str, )),
            }

    def __init__(self, parent, row, cookie, tokens):
        threading.Thread.__init__(self)
        GObject.GObject.__init__(self)

        self.parent = parent
        self.cookie = cookie
        self.tokens = tokens

        self.row = row[:]
        print('Uploader.__init__(), new worker inited:', self.row)

    def run(self):
        #self.check_exists()
        # 如果文件大小小于4M, 就直接上传, 不支持断点续传(没必要).
        # 否则先尝试快速上传模式, 如果没有中的话, 就再进行分片上传.
        # 分片上传, 是最费事的, 也最占带宽.
        # 分片上传, 支持断点续传.
        if self.row[SIZE_COL] > RAPIDUPLOAD_THRESHOLD:
            self.rapid_upload()
        else:
            self.upload_small_file()

    # Open API
    def pause(self):
        print('Uploader.pause()')

    # Open API
    def stop(self):
        print('Uploader.stop() ')

    def check_exists(self):
        meta = pcs.get_metas(self.row[PATH_COL])
        print(meta)

    def upload_small_file(self):
        print('Uploader.upload_small_file:')
        info = pcs.upload(
            self.cookie, self.row[SOURCEPATH_COL], self.row[PATH_COL])
        if info:
            self.emit('uploaded', self.row[SOURCEPATH_COL])
        else:
            self.emit('network-error', self.row[SOURCEPATH_COL])

    def rapid_upload(self):
        '''快速上传.

        如果失败, 就自动调用分片上传.
        '''
        info = pcs.rapid_upload(
            self.cookie, self.tokens,
            self.row[SOURCEPATH_COL], self.row[PATH_COL])
        if info and info['md5'] and info['fs_id']:
            self.emit('uploaded', self.row[SOURCEPATH_COL])
        else:
            self.slice_upload()

    def slice_upload(self):
        print('Uploader.slice_upload()')
        print('分片上传功能还在开发当中...')

GObject.type_register(Uploader)
