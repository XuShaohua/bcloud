
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import json
import os

from gi.repository import Gtk

from gcloud import Config
_ = Config._
from gcloud.Downloader import Downloader
from gcloud import gutil
from gcloud import pcs
from gcloud import util


TASK_FILE = 'tasks.json'

(NAME_COL, PATH_COL, SIZE_COL, SAVEDIR_COL,
    SAVENAME_COL, STATE_COL, PERCENT_COL) = list(range(7))

class State:
    STARTING = 0
    DOWNLOADING = 1
    WAITING = 2
    PAUSED = 3

    names = [
            _('Starting'),
            _('Downloading'),
            _('Waiting'),
            _('Paused'),
        ]

class DownloadPage(Gtk.Box):
    '''下载任务管理器, 处理下载任务的后台调度.

    * 它是与UI进行交互的接口.
    * 它会保存所有下载任务的状态.
    * 它来为每个下载线程分配任务.
    * 它会自动管理磁盘文件结构, 在必要时会创建必要的目录.
    * 它会自动获取文件的最新的下载链接(这个链接有效时间是8小时).

    每个task包含这些信息:
    fs_id - 服务器上的文件UID
    md5 - 文件MD5校验值
    size - 文件大小
    path - 文件在服务器上的绝对路径
    name - 文件在服务器上的名称
    savePath - 保存到的绝对路径
    saveName - 保存时的文件名
    currRange - 当前下载的进度, 以字节为单位, 在HTTP Header中可用.
    state - 任务状态 
    link - 文件的下载最终URL, 有效期大约是8小时, 超时后要重新获取.
    '''

    icon_name = 'folder-download-symbolic'
    disname = _('Download')
    tooltip = _('Downloading tasks')
    first_run = False
    page_num = 11
    tasks = []

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.connect('destroy', self.on_destroyed)

        self.app = app

        control_box = Gtk.Box()
        self.pack_start(control_box, False, False, 0)

        start_button = Gtk.Button(_('Start'))
        #start_button.connect('clicked', self.on_start_button_clicked)
        control_box.pack_start(start_button, False, False, 0)

        pause_button = Gtk.Button(_('Pause'))
        #pause_button.connect('clicked', self.on_pause_button_clicked)
        control_box.pack_start(pause_button, False, False, 0)

        remove_button = Gtk.Button(_('Remove'))
        #remove_button.connect('clicked', self.on_remove_button_clicked)
        control_box.pack_start(remove_button, False, False, 0)

        open_folder_button = Gtk.Button(_('Open Directory'))
        #open_folder_button.connect(
                #'clicked', self.on_open_folder_button_clicked)
        control_box.pack_end(open_folder_button, False, False, 10)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)

        # name, path, size, saveDir,
        # saveName, state, percent
        self.liststore = Gtk.ListStore(
                str, str, str, str, str, str, int)
        self.treeview = Gtk.TreeView(model=self.liststore)
        scrolled_win.add(self.treeview)
        
        name_cell = Gtk.CellRendererText()
        name_col = Gtk.TreeViewColumn(_('Name'), name_cell, text=NAME_COL)
        name_col.set_expand(True)
        self.treeview.append_column(name_col)

        percent_cell = Gtk.CellRendererProgress()
        percent_col = Gtk.TreeViewColumn(
                _('Progress'), percent_cell, value=PERCENT_COL)
        self.treeview.append_column(percent_col)

        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(_('Size'), size_cell, text=SIZE_COL)
        self.treeview.append_column(size_col)

        state_cell = Gtk.CellRendererText()
        state_col = Gtk.TreeViewColumn(_('State'), state_cell, text=STATE_COL)
        self.treeview.append_column(state_col)

    def load(self):
        print('DownloadPage.load() --')
        cache_path = os.path.join(
                Config.CACHE_DIR, self.app.profile['username'])
        if not os.path.exists(cache_path):
            os.makedirs(cache_path, exist_ok=True)
        self.task_path = os.path.join(cache_path, TASK_FILE)
        self.load_tasks()
        for task in self.tasks:
            self.append_task_to_liststore(task)

    def on_destroyed(self, *args):
        '''Dump tasks schedule to disk'''
        print('DownloadPage.do_destory()')
        self.dump_tasks()

    def dump_tasks(self):
        print('will dump taks:', self.tasks)
        if self.tasks:
            with open(self.task_path, 'w') as fh:
                json.dump(self.tasks, fh)
    
    def load_tasks(self):
        if not os.path.exists(self.task_path):
            self.tasks = []
            return
        try:
            with open(self.task_path) as fh:
                self.tasks = json.load(fh)
        except ValueError:
            self.tasks = []

    def get_task_by_fsid(self, fs_id):
        for task in self.tasks:
            if task['fs_id'] == fs_id:
                return task
        return None

    def add_task(self, pcs_file, saveDir=None, saveName=None):
        '''加入新的下载任务'''
        def _add_task(resp, error=None):
            if error:
                return
            red_url, req_id = resp
            task = {
                'name': pcs_file['server_filename'],
                'path': pcs_file['path'],
                'md5': pcs_file['md5'],
                'fs_id': pcs_file['fs_id'],
                'size': pcs_file['size'],
                'saveDir': saveDir,
                'saveName': saveName,
                'state': State.WAITING,
                'currRange': 0,
                'percent': 0,
                'link': red_url,
                }
            self.tasks.append(task)
            self.append_task_to_liststore(task)

        if pcs_file['isdir']:
            return
        if self.get_task_by_fsid(pcs_file['fs_id']):
            return
        if not saveDir:
            saveDir = self.app.profile['save-dir']
        if not saveName:
            saveName = pcs_file['server_filename']

        gutil.async_call(
                pcs.get_download_link, self.app.cookie, pcs_file['dlink'],
                callback=_add_task)
    def append_task_to_liststore(self, task):
        print('append task to liststore() --')
        print(task)
        human_size, _ = util.get_human_size(task['size'])
        self.liststore.append([
            task['name'], task['path'], human_size, task['saveDir'],
            task['saveName'], State.names[task['state']], task['percent'],
            ])

    def start_task(self, fs_id):
        #info = self.tasks[fs_id]
        pass

    def pause_task(self, fs_id):
        pass

    def remove_task(self, fs_id):
        pass
