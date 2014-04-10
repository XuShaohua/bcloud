
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import json
import os
import sqlite3
import threading

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud.Downloader import Downloader
from bcloud import gutil
from bcloud import pcs
from bcloud import util
from bcloud.const import State


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

    icon_name = 'download-symbolic'
    disname = _('Download')
    tooltip = _('Downloading tasks')
    first_run = True
    workers = {} # { `fs_id': (worker,row) }
    app_infos = {} # { `fs_id': app }

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

    def load(self):
        app = self.app
        control_box = Gtk.Box()
        self.pack_start(control_box, False, False, 0)

        start_button = Gtk.Button.new_with_label(_('Start'))
        start_button.connect('clicked', self.on_start_button_clicked)
        control_box.pack_start(start_button, False, False, 0)

        pause_button = Gtk.Button.new_with_label(_('Pause'))
        pause_button.connect('clicked', self.on_pause_button_clicked)
        control_box.pack_start(pause_button, False, False, 0)

        remove_button = Gtk.Button.new_with_label(_('Remove'))
        remove_button.connect('clicked', self.on_remove_button_clicked)
        control_box.pack_start(remove_button, False, False, 0)

        open_folder_button = Gtk.Button.new_with_label(_('Open Directory'))
        open_folder_button.connect(
                'clicked', self.on_open_folder_button_clicked)
        control_box.pack_end(open_folder_button, False, False, 10)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)

        # name, path, fs_id, size, currsize, link,
        # isdir, saveDir, saveName, state, statename,
        # humansize, percent
        self.liststore = Gtk.ListStore(
                str, str, str, GObject.TYPE_INT64, GObject.TYPE_INT64, str,
                GObject.TYPE_INT, str, str, GObject.TYPE_INT, str,
                str, GObject.TYPE_INT)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_tooltip_column(PATH_COL)
        self.treeview.set_headers_clickable(True)
        self.treeview.set_reorderable(True)
        self.treeview.set_search_column(0)
        self.selection = self.treeview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        scrolled_win.add(self.treeview)
        
        name_cell = Gtk.CellRendererText(
                ellipsize=Pango.EllipsizeMode.END, ellipsize_set=True)
        name_col = Gtk.TreeViewColumn(_('Name'), name_cell, text=NAME_COL)
        name_col.set_expand(True)
        name_col.set_sort_column_id(NAME_COL)
        self.treeview.append_column(name_col)

        percent_cell = Gtk.CellRendererProgress()
        percent_col = Gtk.TreeViewColumn(
                _('Progress'), percent_cell, value=PERCENT_COL)
        self.treeview.append_column(percent_col)
        percent_col.props.min_width = 145
        percent_col.set_sort_column_id(PERCENT_COL)

        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(
                _('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)
        size_col.props.min_width = 100
        size_col.set_sort_column_id(SIZE_COL)

        state_cell = Gtk.CellRendererText()
        state_col = Gtk.TreeViewColumn(
                _('State'), state_cell, text=STATENAME_COL)
        self.treeview.append_column(state_col)
        state_col.props.min_width = 100
        state_col.set_sort_column_id(PERCENT_COL)

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
        sql = '''CREATE TABLE IF NOT EXISTS download (
        name CHAR NOT NULL,
        path CHAR NOT NULL,
        fsid CHAR NOT NULL,
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

    def check_first(self):
        if self.first_run:
            self.first_run = False
            self.load()

    def do_destroy(self, *args):
        if not self.first_run:
            for worker, row in self.workers.values():
                worker.pause()
                row[CURRSIZE_COL] = worker.row[CURRSIZE_COL]
            self.dump_tasks()
            self.conn.commit()
            self.conn.close()
    
    def load_tasks(self):
        req = self.cursor.execute('SELECT * FROM download')
        for task in req:
            self.liststore.append(task)

    def dump_tasks(self):
        sql = 'DELETE FROM download'
        self.cursor.execute(sql)
        sql = 'INSERT INTO download VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)'
        for row in self.liststore:
            if (row[STATE_COL] == State.DOWNLOADING or 
                    row[STATE_COL] == State.WAITING):
                row[STATE_COL] = State.PAUSED
                row[STATENAME_COL] = StateNames[State.PAUSED]
            self.cursor.execute(sql, row[:])

    def dump_tasks_in_background(self, *args):
        if not self.first_run:
            self.dump_tasks()
        return True

    def get_row_by_fsid(self, fs_id):
        '''确认在Liststore中是否存在这条任务. 如果存在, 返回TreeModelRow,
        否则就返回None'''
        for row in self.liststore:
            if row[FSID_COL] == fs_id:
                return row
        return None

    # Open API
    def add_launch_task(self, pcs_file, app_info):
        self.check_first()
        fs_id = str(pcs_file['fs_id'])
        if fs_id in self.app_infos:
            return
        self.app_infos[fs_id] = app_info
        self.add_task(pcs_file)

    def launch_app(self, fs_id):
        if fs_id in self.app_infos:
            row = self.get_row_by_fsid(fs_id)
            app_info = self.app_infos[fs_id]
            filepath = os.path.join(row[SAVEDIR_COL], row[SAVENAME_COL])
            gfile = Gio.File.new_for_path(filepath)
            app_info.launch([gfile, ], None)
            self.app_infos.pop(fs_id, None)

    # Open API
    def add_tasks(self, pcs_files):
        '''建立批量下载任务, 包括目录'''
        def on_list_dir(info, error=None):
            path, pcs_files = info
            if error or not pcs_files:
                dialog = Gtk.MessageDialog(
                        self.app.window, Gtk.DialogFlags.MODAL,
                        Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE,
                        _('Failed to scan folder to download'))
                dialog.format_secondary_text(
                        _('Please download {0} again').format(path))
                dialog.run()
                dialog.destroy()
                return
            self.add_tasks(pcs_files)

        self.check_first()
        for pcs_file in pcs_files:
            if pcs_file['isdir']:
                gutil.async_call(
                        pcs.list_dir_all, self.app.cookie, self.app.tokens,
                        pcs_file['path'], callback=on_list_dir)
            else:
                self.add_task(pcs_file)

    def add_task(self, pcs_file):
        '''加入新的下载任务'''
        if pcs_file['isdir']:
            return
        # 如果已经存在于下载列表中, 就忽略.
        row = self.get_row_by_fsid(pcs_file['fs_id'])
        if row:
            if row[STATE_COL] == State.FINISHED:
                self.launch_app(pcs_file['fs_id'])
            elif row[STATE_COL] not in RUNNING_STATES:
                row[STATE_COL] = State.WAITING
            self.scan_tasks()
            return
        saveDir = os.path.split(
                self.app.profile['save-dir'] + pcs_file['path'])[0]
        saveName = pcs_file['server_filename']

        human_size = util.get_human_size(pcs_file['size'])[0]
        task = (
            pcs_file['server_filename'],
            pcs_file['path'],
            str(pcs_file['fs_id']),
            pcs_file['size'],
            0,
            pcs_file['dlink'],
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

    def scan_tasks(self):
        '''扫描所有下载任务, 并在需要时启动新的下载'''
        if len(self.workers.keys()) >= self.app.profile['concurr-tasks']:
            return
        for row in self.liststore:
            if len(self.workers.keys()) >= self.app.profile['concurr-tasks']:
                break
            if row[STATE_COL] == State.WAITING:
                self.start_worker(row)

    def start_worker(self, row):
        '''为task新建一个后台下载线程, 并开始下载.'''
        def on_worker_received(worker, fs_id, current_size):
            def _on_worker_received():
                row = None
                if fs_id in self.workers:
                    _, row = self.workers[fs_id]
                else:
                    row = self.get_row_by_fsid(fs_id)
                if not row:
                    print('on worker received, row is None:', row)
                    return
                row[CURRSIZE_COL] = current_size
                total_size = util.get_human_size(row[SIZE_COL])[0]
                curr_size = util.get_human_size(row[CURRSIZE_COL])[0]
                row[PERCENT_COL] = int(row[CURRSIZE_COL] / row[SIZE_COL] * 100)
                row[HUMANSIZE_COL] = '{0} / {1}'.format(curr_size, total_size)
            GLib.idle_add(_on_worker_received)

        def on_worker_downloaded(worker, fs_id):
            def _on_worker_downloaded():
                row = self.get_row_by_fsid(fs_id)
                row = self.workers[fs_id][1]
                row[CURRSIZE_COL] = row[SIZE_COL]
                row[STATE_COL] = State.FINISHED
                row[PERCENT_COL] = 100
                total_size = util.get_human_size(row[SIZE_COL])[0]
                row[HUMANSIZE_COL] = '{0} / {1}'.format(total_size, total_size)
                row[STATENAME_COL] = StateNames[State.FINISHED]
                self.workers.pop(row[FSID_COL], None)
                self.app.toast(_('{0} downloaded'.format(row[NAME_COL])))
                self.launch_app(fs_id)
                self.scan_tasks()
            GLib.idle_add(_on_worker_downloaded)

        def on_worker_network_error(worker, fs_id):
            row = self.get_row_by_fsid(fs_id)
            row = self.workers[fs_id][1]
            row[STATE_COL] = State.ERROR
            row[STATENAME_COL] = StateNames[State.ERROR]
            self.remove_worker(row[FSID_COL])

        if row[FSID_COL] in self.workers:
            return
        row[STATE_COL] = State.DOWNLOADING
        row[STATENAME_COL] = StateNames[State.DOWNLOADING]
        worker = Downloader(self, row, self.app.cookie, self.app.tokens)
        self.workers[row[FSID_COL]] = (worker, row)
        worker.connect('received', on_worker_received)
        worker.connect('downloaded', on_worker_downloaded)
        worker.connect('network-error', on_worker_network_error)
        worker.start()

    def pause_worker(self, row):
        self.remove_worker(row[FSID_COL], stop=False)

    def stop_worker(self, row):
        '''停止这个task的后台下载线程'''
        self.remove_worker(row[FSID_COL], stop=True)

    def remove_worker(self, fs_id, stop=True):
        if fs_id not in self.workers:
            return
        worker = self.workers[fs_id][0]
        if stop:
            worker.stop()
        else:
            worker.pause()
        self.workers.pop(fs_id, None)

    def start_task(self, row):
        '''启动下载任务.

        将任务状态设定为Downloading, 如果没有超过最大任务数的话;
        否则将它设定为Waiting.
        '''
        if row[STATE_COL] in RUNNING_STATES :
            return
        row[STATE_COL] = State.WAITING
        row[STATENAME_COL] = StateNames[State.WAITING]
        self.scan_tasks()

    def pause_task(self, row):
        if row[STATE_COL] == State.DOWNLOADING:
            self.pause_worker(row)
            row[STATE_COL] = State.PAUSED
            row[STATENAME_COL] = StateNames[State.PAUSED]
            self.scan_tasks()
        elif row[STATE_COL] == State.WAITING:
            row[STATE_COL] = State.PAUSED
            row[STATENAME_COL] = StateNames[State.PAUSED]
            self.scan_tasks()

    def remove_task(self, row):
        # 当删除正在下载的任务时, 直接调用stop_worker(), 它会自动删除本地的
        # 文件片段
        if row[STATE_COL] == State.DOWNLOADING:
            self.stop_worker(row)
        self.app_infos.pop(row[FSID_COL], None)
        tree_iter = row.iter
        if tree_iter:
            self.liststore.remove(tree_iter)

    def operate_selected_rows(self, operator):
        '''对选中的条目进行操作.

        operator  - 处理函数
        '''
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        fs_ids = []
        for tree_path in tree_paths:
            fs_ids.append(model[tree_path][FSID_COL])
        for fs_id in fs_ids:
            row = self.get_row_by_fsid(fs_id)
            operator(row)

    def on_start_button_clicked(self, button):
        self.operate_selected_rows(self.start_task)

    def on_pause_button_clicked(self, button):
        self.operate_selected_rows(self.pause_task)

    def on_remove_button_clicked(self, button):
        self.operate_selected_rows(self.remove_task)

    def on_open_folder_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        for tree_path in tree_paths:
            gutil.xdg_open(self.liststore[tree_path][SAVEDIR_COL])
