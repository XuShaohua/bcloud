
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import json
import os
import threading

from gi.repository import Gtk

from gcloud import Config
_ = Config._
from gcloud.Downloader import Downloader
from gcloud import gutil
from gcloud import pcs
from gcloud import util
from gcloud.const import State


TASK_FILE = 'tasks.json'

(NAME_COL, PATH_COL, SIZE_COL, SAVEDIR_COL,
    SAVENAME_COL, STATE_COL, PERCENT_COL) = list(range(7))

StateNames = (
        _('DOWNLOADING'),
        _('WAITING'),
        _('PAUSED'),
        _('FINISHED'),
        _('CANCELED'),
        )


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
    workers = {}
    active_tasks = 0

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.connect('destroy', self.on_destroyed)

        self.app = app

        control_box = Gtk.Box()
        self.pack_start(control_box, False, False, 0)

        start_button = Gtk.Button(_('Start'))
        start_button.connect('clicked', self.on_start_button_clicked)
        control_box.pack_start(start_button, False, False, 0)

        pause_button = Gtk.Button(_('Pause'))
        pause_button.connect('clicked', self.on_pause_button_clicked)
        control_box.pack_start(pause_button, False, False, 0)

        remove_button = Gtk.Button(_('Remove'))
        remove_button.connect('clicked', self.on_remove_button_clicked)
        control_box.pack_start(remove_button, False, False, 0)

        open_folder_button = Gtk.Button(_('Open Directory'))
        open_folder_button.connect(
                'clicked', self.on_open_folder_button_clicked)
        control_box.pack_end(open_folder_button, False, False, 10)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)

        # name, path, size, saveDir,
        # saveName, state, percent
        self.liststore = Gtk.ListStore(
                str, str, str, str, str, str, int)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.selection = self.treeview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
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
        for worker in self.workers.values():
            worker.destroy()

        self.dump_tasks()

    def dump_tasks(self):
        with open(self.task_path, 'w') as fh:
            json.dump(self.tasks, fh)
    
    def load_tasks(self):
        if not os.path.exists(self.task_path):
            self.tasks = []
            return
        try:
            with open(self.task_path) as fh:
                self.tasks = json.load(fh)
            # 重置下载状态. 在界面启动后, 需要手动启动上次未完成的下载.
            for task in self.tasks:
                if not task['state'] == State.FINISHED:
                    task['state'] = State.PAUSED
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
        human_size, _ = util.get_human_size(task['size'])
        self.liststore.append([
            task['name'], task['path'], human_size, task['saveDir'],
            task['saveName'], StateNames[task['state']], task['percent'],
            ])

    def update_treeview(self, task, tree_iter):
        '''更新主界面上的显示信息'''
        print('update treeview()')
        if not tree_iter or not task:
            return
        tree_path = self.liststore.get_path(tree_iter)
        self.liststore[tree_path][STATE_COL] = StateNames[task['state']]
        self.liststore[tree_path][PERCENT_COL] = task['percent']
        total_size, _ = util.get_human_size(task['size'])
        curr_size, _ = util.get_human_size(task['currRange'])
        self.liststore[tree_path][SIZE_COL] = '{0} / {1}'.format(
                curr_size, total_size)

    def scan_tasks(self):
        '''扫描所有下载任务, 并在需要时启动新的下载'''
        if not len(self.tasks):
            return
        for task in self.tasks:
            if self.active_tasks >= self.app.profile['concurr-tasks']:
                break
            if task['state'] == State.WAITING:
                task['state'] = State.DOWNLOADING
                self.start_worker(task)
                self.active_tasks = self.active_tasks + 1

    def start_worker(self, task):
        '''为task新建一个后台下载线程, 并开始下载.'''
        tree_iter = None
        for row in self.liststore:
            if task['path'] == row[PATH_COL]:
                tree_iter = row.iter
                break
        if not tree_iter:
            return
        worker = Downloader(
                self, task, tree_iter, self.app.cookie, self.app.tokens)
        self.workers[task['fs_id']] = worker
        worker.start()
        
    def pause_worker(self, task):
        try:
            worker = self.workers[task['fs_id']]
            worker.pause()
        except KeyError:
            pass

    def stop_worker(self, task):
        '''停止这个task的后台下载线程'''
        try:
            worker = self.workers[task['fs_id']]
            worker.stop()
        except KeyError:
            pass

    def start_task(self, tree_path):
        '''启动下载任务.

        将任务状态设定为Downloading, 如果没有超过最大任务数的话;
        否则将它设定为Waiting.
        '''
        index = tree_path.get_indices()[0]
        task = self.tasks[index]
        if task['state'] == State.DOWNLOADING:
            return
        task['state'] = State.WAITING
        self.scan_tasks()
        self.liststore[tree_path][STATE_COL] = StateNames[task['state']]

    def pause_task(self, tree_path):
        index = tree_path.get_indices()[0]
        task = self.tasks[index]
        if task['state'] == State.PAUSED:
            return
        if task['state'] == State.DOWNLOADING:
            self.active_tasks = self.active_tasks - 1
            self.pause_worker(task)
            self.scan_tasks()
        task['state'] = State.PAUSED
        self.liststore[tree_path][STATE_COL] = StateNames[task['state']]

    def remove_task(self, tree_path):
        index = tree_path.get_indices()[0]
        task = self.tasks[index]
        # 当删除正在下载的任务时, 直接调用stop_worker(), 它会自动删除本地的
        # 文件片段
        if task['state'] == State.DOWNLOADING:
            self.stop_worker(task)
            self.active_tasks = self.active_tasks - 1
        elif task['currRange'] < task['size']:
        # 当文件没有下载完, 就被暂停, 之后又被删除时, 务必删除本地的文件片段
            filepath = os.path.join(task['saveDir'], task['saveName'])
            if os.path.exists(filepath):
                os.remove(filepath)
        self.tasks = util.list_remove_by_index(self.tasks, index)
        self.liststore.remove(self.liststore.get_iter(tree_path))

    def on_start_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        for tree_path in tree_paths:
            self.start_task(tree_path)

    def on_pause_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        for tree_path in tree_paths:
            self.pause_task(tree_path)

    def on_remove_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        for tree_path in tree_paths:
            self.remove_task(tree_path)

    def on_open_folder_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        for tree_path in tree_paths:
            gutil.xdg_open(self.liststore[tree_path][SAVEDIR_COL])
