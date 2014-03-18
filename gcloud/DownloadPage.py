
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import json
import os
import sqlite3
import threading

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk

from gcloud import Config
_ = Config._
from gcloud.Downloader import Downloader
from gcloud import gutil
from gcloud import pcs
from gcloud import util
from gcloud.const import State


TASK_FILE = 'tasks.sqlite'
RUNNING_STATES = (State.FINISHED, State.DOWNLOADING, State.WAITING)
(NAME_COL, PATH_COL, FSID_COL, SIZE_COL, CURRSIZE_COL, LINK_COL,
    ISDIR_COL, SAVENAME_COL, SAVEDIR_COL, STATE_COL, STATENAME_COL,
    HUMANSIZE_COL, PERCENT_COL) = list(range(13))

StateNames = (
        _('DOWNLOADING'),
        _('WAITING'),
        _('PAUSED'),
        _('FINISHED'),
        _('CANCELED'),
        _('ERROR'),
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
    workers = {} # { `fs_id': worker }
    app_infos = {} # { `fs_id': app }

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.connect('destroy', self.on_destroyed)
        self.app = app

    def load(self):
        app = self.app
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

        # name, path, fs_id, size, currsize, link,
        # isdir, saveDir, saveName, state, statename,
        # humansize, percent
        self.liststore = Gtk.ListStore(
                str, str, GObject.TYPE_LONG, GObject.TYPE_LONG,
                GObject.TYPE_LONG, str,
                int, str, str, int, str,
                str, int)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_tooltip_column(PATH_COL)
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
        size_col = Gtk.TreeViewColumn(
                _('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)

        state_cell = Gtk.CellRendererText()
        state_col = Gtk.TreeViewColumn(
                _('State'), state_cell, text=STATENAME_COL)
        self.treeview.append_column(state_col)

        self.init_db()
        self.load_tasks()
        self.show_all()

    def init_db(self):
        '''这个任务数据库只在程序开始时读入, 在程序关闭时导出.

        因为Gtk没有像在Qt中那么方便的使用SQLite, 而必须将所有数据读入一个
        liststore中才行.
        '''
        cache_path = os.path.join(
                Config.CACHE_DIR, self.app.profile['username'])
        if not os.path.exists(cache_path):
            os.makedirs(cache_path, exist_ok=True)
        db = os.path.join(cache_path, TASK_FILE)
        self.conn = sqlite3.connect(db)
        self.cursor = self.conn.cursor()
        sql = '''CREATE TABLE IF NOT EXISTS queue (
        name CHAR NOT NULL,
        path CHAR NOT NULL,
        fsid INTEGER NOT NULL,
        size INTEGER NOT NULL,
        currsize INTEGER NOT NULL,
        link CHAR,
        isdir INTEGER,
        savename CHAR NOT NULL,
        savedir CHAR NOT NULL,
        state INT NOT NULL,
        statename CHAR NOT NULL,
        humansize CHAR NOT NULL,
        percent INT NOT NULL
        )
        '''
        self.cursor.execute(sql)

    def on_destroyed(self, *args):
        for worker, task in self.workers.values():
            worker.destroy()
        self.dump_tasks()
        self.conn.commit()
        self.conn.close()
    
    def load_tasks(self):
        req = self.cursor.execute('SELECT * FROM queue')
        for task in req:
            self.liststore.append(task)
        self.scan_tasks()

    def dump_tasks(self):
        sql = 'DELETE FROM queue'
        self.cursor.execute(sql)
        sql = 'INSERT INTO queue VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)'
        for row in self.liststore:
            if (row[STATE_COL] == State.DOWNLOADING or 
                    row[STATE_COL] == State.WAITING):
                row[STATE_COL] = State.PAUSED
                row[STATENAME_COL] = StateNames[State.PAUSED]
            self.cursor.execute(sql, row[:])

    def get_task_by_fsid(self, fs_id):
        '''确认在Liststore中是否存在这条任务. 如果存在, 返回TreeModelRow,
        否则就返回None'''
        for row in self.liststore:
            if row[FSID_COL] == fs_id:
                return row
        return None

    # Open API
    def add_launch_task(self, pcs_file, app_info, saveDir=None,
                        saveName=None):
        if pcs_file['fs_id'] in self.app_infos:
            return
        self.app_infos[pcs_file['fs_id']] = app_info
        self.add_task(pcs_file, saveDir, saveName)

    def launch_app(self, fs_id):
        print('launch app() ')
        if fs_id in self.app_infos:
            print('will launch app')
            row = self.get_task_by_fsid(fs_id)
            app_info = self.app_infos[fs_id]
            filepath = os.path.join(row[SAVEDIR_COL], row[SAVENAME_COL])
            print('file path:', filepath)
            gfile = Gio.File.new_for_path(filepath)
            print('g file:', gfile)
            app_info.launch([gfile, ], None)
        else:
            print('fs id not in self.app_infos')

    # Open API
    def add_task(self, pcs_file, saveDir=None, saveName=None):
        '''加入新的下载任务'''
        print('add_task() --', pcs_file)
        def _add_task(resp, error=None):
            print('_add task')
            if error:
                print('Error occured will adding task:', resp)
                return
            red_url, req_id = resp
            print('resp:', resp)
            human_size, _ = util.get_human_size(pcs_file['size'])
            task = (
                pcs_file['server_filename'],
                pcs_file['path'],
                pcs_file['fs_id'],
                pcs_file['size'],
                0,
                red_url,
                pcs_file['isdir'],
                saveName,
                saveDir,
                State.WAITING,
                StateNames[State.WAITING],
                human_size,
                0,
                )
            self.liststore.append(task)
            self.scan_tasks()

        # 目前还不支持下载目录.
        if pcs_file['isdir']:
            return
        # 如果已经存在于下载列表中, 就忽略.
        row = self.get_task_by_fsid(pcs_file['fs_id'])
        if row:
            print('fs id already exists in task list')
            print(row[STATENAME_COL])
            if row[STATE_COL] == State.FINISHED:
                self.launch_app(pcs_file['fs_id'])
            elif row[STATE_COL] not in RUNNING_STATES:
                print(row[STATENAME_COL])
                row[STATE_COL] = State.WAITING
                self.scan_tasks()
            return
        if not saveDir:
            saveDir, _ = os.path.split(
                    self.app.profile['save-dir'] + pcs_file['path'])
        if not saveName:
            saveName = pcs_file['server_filename']

        gutil.async_call(
                pcs.get_download_link, self.app.cookie, pcs_file['dlink'],
                callback=_add_task)

    def scan_tasks(self):
        '''扫描所有下载任务, 并在需要时启动新的下载'''
        print('scan_tasks() -- ')
        for row in self.liststore:
            if len(self.workers.keys()) >= self.app.profile['concurr-tasks']:
                print('max concurrent tasks reached:', self.workers.keys(),
                        self.app.profile['concurr-tasks'])
                break
            if row[STATE_COL] == State.WAITING:
                self.start_worker(row)
            else:
                print('state is not waiting:', row[STATENAME_COL])
        return True

    def start_worker(self, row):
        '''为task新建一个后台下载线程, 并开始下载.'''
        print('start_worker() --', row[:])
        def on_worker_received(worker, fs_id, current_size):
            row = self.get_task_by_fsid(fs_id)
            _, row = self.workers[fs_id]
            row[CURRSIZE_COL] = current_size
            total_size, _ = util.get_human_size(row[SIZE_COL])
            curr_size, _ = util.get_human_size(row[CURRSIZE_COL])
            row[PERCENT_COL] = int(row[CURRSIZE_COL] / row[SIZE_COL] * 100)
            row[HUMANSIZE_COL] = '{0} / {1}'.format(curr_size, total_size)

        def on_worker_downloaded(worker, fs_id):
            row = self.get_task_by_fsid(fs_id)
            _, row = self.workers[fs_id]
            row[CURRSIZE_COL] = row[SIZE_COL]
            row[STATE_COL] = State.FINISHED
            row[PERCENT_COL] = 100
            total_size, _ = util.get_human_size(row[SIZE_COL])
            row[HUMANSIZE_COL] = '{0} / {1}'.format(total_size, total_size)
            row[STATENAME_COL] = StateNames[State.FINISHED]
            self.launch_app(fs_id)

        def on_worker_network_error(worker, fs_id):
            row = self.get_task_by_fsid(fs_id)
            _, row = self.workers[fs_id]
            row[STATE_COL] = State.ERROR
            row[STATENAME_COL] = StateNames[State.ERROR]

        if row[FSID_COL] in self.workers:
            return
        row[STATE_COL] = State.DOWNLOADING
        row[STATENAME_COL] = StateNames[State.DOWNLOADING]
        tree_iter = row.iter
        worker = Downloader(self, row, self.app.cookie, self.app.tokens)
        self.workers[row[FSID_COL]] = (worker, row)
        print(self.workers.keys())
        worker.connect('received', on_worker_received)
        worker.connect('downloaded', on_worker_downloaded)
        worker.connect('network-error', on_worker_network_error)
        worker.start()

    def on_task_downloaded(self, worker, fs_id):
        '''下载完成后要更新界面'''
        pass
        
    def pause_worker(self, row):
        try:
            worker, _ = self.workers[row[FSID_COL]]
            worker.pause()
        except KeyError:
            pass

    def stop_worker(self, row):
        '''停止这个task的后台下载线程'''
        try:
            worker, _ = self.workers[row[FSID_COL]]
            worker.stop()
        except KeyError:
            pass

    def start_task(self, row):
        '''启动下载任务.

        将任务状态设定为Downloading, 如果没有超过最大任务数的话;
        否则将它设定为Waiting.
        '''
        print('start_task() --')
        if row[STATE_COL] == State.DOWNLOADING:
            return
        row[STATE_COL] = State.WAITING
        self.scan_tasks()

    def pause_task(self, row):
        print('pause_task() --')
        if row[STATE_COL] == State.PAUSED:
            return
        elif row[STATE_COL] == State.DOWNLOADING:
            self.pause_worker(row)
            row[STATE_COL] = State.PAUSED
            self.scan_tasks()
        row[STATE_COL] = State.PAUSED
        row[STATENAME_COL] = StateNames[State.PAUSED]

    def remove_task(self, tree_iter):
        print('remove_task() --')
        tree_path = self.liststore.get_path(tree_iter)
        index = tree_path.get_indices()[0]
        print('index:', index)
        row = self.liststore[index]
        print('row:', row[:])
        # 当删除正在下载的任务时, 直接调用stop_worker(), 它会自动删除本地的
        # 文件片段
        if row[STATE_COL] == State.DOWNLOADING:
            self.stop_worker(row)
            del self.workers[row[FSID_COL]]
            print('worker deleted:', self.workers.keys())
        elif row[CURRSIZE_COL] < row[SIZE_COL]:
        # 当文件没有下载完, 就被暂停, 之后又被删除时, 务必删除本地的文件片段
            filepath = os.path.join(row[SAVEDIR_COL], row[SAVENAME_COL])
            if os.path.exists(filepath):
                os.remove(filepath)
        if row[FSID_COL] in self.app_infos:
            del self.app_infos[row[FSID_COL]]
        tree_iter = row.iter
        if tree_iter:
            self.liststore.remove(tree_iter)

    def on_start_button_clicked(self, button):
        print('on_start_button_clicked() --')
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            print('tree_paths is none')
            return
        for tree_path in tree_paths:
            index = tree_path.get_indices()[0]
            row = self.liststore[index]
            if row[STATE_COL] not in RUNNING_STATES:
                self.start_task(row)

    def on_pause_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        for tree_path in tree_paths:
            index = tree_path.get_indices()[0]
            row = self.liststore[index]
            if row[STATE_COL] == State.FINISHED:
                continue
            self.pause_task(row)

    def on_remove_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        tree_iters = []
        for tree_path in tree_paths:
            tree_iters.append(model.get_iter(tree_path))
        for tree_iter in tree_iters:
            self.remove_task(tree_iter)

    def on_open_folder_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        for tree_path in tree_paths:
            gutil.xdg_open(self.liststore[tree_path][SAVEDIR_COL])
