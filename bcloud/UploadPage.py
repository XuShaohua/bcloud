
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os
import sqlite3

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud.FolderBrowserDialog import FolderBrowserDialog
from bcloud.Uploader import Uploader
from bcloud import gutil
from bcloud import pcs
from bcloud import util

(FID_COL, NAME_COL, SOURCEPATH_COL, PATH_COL, SIZE_COL, CURRSIZE_COL, 
    STATE_COL, STATENAME_COL, HUMANSIZE_COL, PERCENT_COL) = list(range(10))
TASK_FILE = 'upload.sqlite'

class State:
    '''下载状态常量'''
    UPLOADING = 0
    WAITING = 1
    PAUSED = 2
    FINISHED = 3
    CANCELED = 4
    ERROR = 5

StateNames = [
    _('UPLOADING'),
    _('WAITING'),
    _('PAUSED'),
    _('FINISHED'),
    _('CANCELED'),
    _('ERROR'),
    ]

RUNNING_STATES = (State.FINISHED, State.UPLOADING, State.WAITING)


class UploadPage(Gtk.Box):

    icon_name = 'upload-symbolic'
    disname = _('Upload')
    tooltip = _('Uploading tasks')
    first_run = True
    workers = {}  # {`fid`: (worker, row)}
    commit_count = 0

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

    def check_first(self):
        if self.first_run:
            self.first_run = False
            self.load()

    def load(self):
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

        upload_button = Gtk.Button.new_with_label(_('Upload a file'))
        upload_button.connect('clicked', self.on_upload_button_clicked)
        control_box.pack_end(upload_button, False, False, 0)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)
        
        # fid, source_name, source_path, path, size,
        # currsize, state, statename, humansize, percent
        self.liststore = Gtk.ListStore(
            GObject.TYPE_INT, str, str, str, GObject.TYPE_INT64,
            GObject.TYPE_INT64, int, str, str, GObject.TYPE_INT)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.selection = self.treeview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        scrolled_win.add(self.treeview)

        name_cell = Gtk.CellRendererText(
                ellipsize=Pango.EllipsizeMode.END, ellipsize_set=True)
        name_col = Gtk.TreeViewColumn(_('Name'), name_cell, text=NAME_COL)
        name_col.set_expand(True)
        self.treeview.append_column(name_col)
        percent_cell = Gtk.CellRendererProgress()
        percent_col = Gtk.TreeViewColumn(
                _('Progress'), percent_cell, value=PERCENT_COL)
        self.treeview.append_column(percent_col)
        percent_col.props.min_width = 145
        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(
                _('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)
        size_col.props.min_width = 100
        state_cell = Gtk.CellRendererText()
        state_col = Gtk.TreeViewColumn(
                _('State'), state_cell, text=STATENAME_COL)
        self.treeview.append_column(state_col)
        state_col.props.min_width = 100
        self.treeview.set_tooltip_column(PATH_COL)

        self.show_all()
        self.init_db()
        self.load_tasks_from_db()

    def init_db(self):
        cache_path = os.path.join(
                Config.CACHE_DIR, self.app.profile['username'])
        if not os.path.exists(cache_path):
            os.makedirs(cache_path, exist_ok=True)
        db = os.path.join(cache_path, TASK_FILE)
        self.conn = sqlite3.connect(db)
        self.cursor = self.conn.cursor()
        sql = '''CREATE TABLE IF NOT EXISTS tasks(
        fid INTEGER PRIMARY KEY,
        name CHAR NOT NULL,
        source_path CHAR NOT NULL,
        path CHAR NOT NULL,
        size INTEGER NOT NULL,
        curr_size INTEGER NOT NULL,
        state INTEGER NOT NULL,
        state_name CHAR NOT NULL,
        human_size CHAR NOT NULL,
        percent INTEGER NOT NULL
        )
        '''
        self.cursor.execute(sql)
        sql = '''CREATE TABLE IF NOT EXISTS slice(
        fid INTEGER NOT NULL,
        slice_end INTEGER NOT NULL,
        md5 CHAR NOT NULL
        )
        '''
        self.cursor.execute(sql)

    def load_tasks_from_db(self):
        sql = 'SELECT * FROM tasks'
        req = self.cursor.execute(sql)
        for task in req:
            self.liststore.append(task)

    def check_commit(self):
        '''当修改数据库超过5次后, 就自动commit数据.'''
        self.commit_count = self.commit_count + 1
        if self.commit_count >= 5:
            self.commit_count = 0
            self.conn.commit()

    def add_task_db(self, task):
        '''向数据库中写入一个新的任务记录, 并返回它的fid'''
        print('add task db:', task)
        sql = '''INSERT INTO tasks(
        name, source_path, path, size, curr_size, state, state_name,
        human_size, percent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        req = self.cursor.execute(sql, task)
        self.check_commit()
        return req.lastrowid

    def add_slice_db(self, fid, slice_end, md5):
        '''在数据库中加入上传任务分片信息'''
        print('add slice db:', fid, slice_end, md5)
        sql = 'INSERT INTO slice VALUES(?, ?, ?)'
        self.cursor.execute(sql, (fid, slice_end, md5))
        self.check_commit()

    def get_task_db(self, source_path):
        '''从数据库中查询source_path的信息.
        
        如果存在的话, 就返回这条记录;
        如果没有的话, 就返回None
        '''
        print('get task_db:', source_path)
        sql = 'SELECT * FROM tasks WHERE source_path=? LIMIT 1'
        req = self.cursor.execute(sql, [source_path, ])
        if req:
            return req.fetchone()
        else:
            None

    def get_slice_db(self, fid):
        '''从数据库中取得fid的所有分片.
        
        返回的是一个list, 里面是按顺序排好的md5的值
        '''
        print('get slice db:', fid)
        sql = 'SELECT md5 FROM slice WHERE fid=?'
        req = self.cursor.execute(sql, [fid, ])
        if req:
            return [r[0] for r in req]
        else:
            return None

    def update_task_db(self, row):
        '''更新数据库中的任务信息'''
        print('update task_db:', row[:])
        sql = '''UPDATE tasks SET 
        curr_size=?, state=?, state_name=?, human_size=?, percent=?
        WHERE fid=? LIMIT 1;
        '''
        self.cursor.execute(sql, [
            row[CURRSIZE_COL], row[STATE_COL], row[STATENAME_COL],
            row[HUMANSIZE_COL], row[PERCENT_COL], row[FID_COL]
            ])
        self.check_commit()

    def remove_task_db(self, fid):
        '''将任务从数据库中删除'''
        print('remove task_db:', fid)
        self.remove_slice_db(fid)
        sql = 'DELETE FROM tasks WHERE fid=?'
        self.cursor.execute(sql, [fid, ])
        self.check_commit()

    def remove_slice_db(self, fid):
        '''将上传任务的分片从数据库中删除'''
        sql = 'DELETE FROM slice WHERE fid=?'
        self.cursor.execute(sql, [fid, ])

    def do_destroy(self, *args):
        if not self.first_run:
            for row in self.liststore:
                self.pause_task(row)
            self.conn.commit()
            self.conn.close()

    def add_task(self):
        file_dialog = Gtk.FileChooserDialog(
            _('Choose a file..'), self.app.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK))
        file_dialog.set_modal(True)
        file_dialog.set_select_multiple(True)
        response = file_dialog.run()
        if response != Gtk.ResponseType.OK:
            file_dialog.destroy()
            return
        source_paths = file_dialog.get_filenames()
        file_dialog.destroy()
        if source_paths:
            self.add_file_tasks(source_paths)

    # Open API
    def add_file_tasks(self, source_paths, dir_name=None):
        '''批量创建上传任务

        source_path - 本地文件的绝对路径
        dir_name    - 文件在服务器上的父目录, 如果为None的话, 会弹出一个
                      对话框让用户来选择一个目录.
        '''
        def scan_folders(folder_path):
            file_list = os.listdir(folder_path)
            source_paths = [os.path.join(folder_path, f) for f in file_list]
            self.add_file_tasks(
                    source_paths,
                    os.path.join(dir_name, os.path.split(folder_path)[1]))

        self.check_first()
        if not dir_name:
            folder_dialog = FolderBrowserDialog(self, self.app)
            response = folder_dialog.run()
            if response != Gtk.ResponseType.OK:
                folder_dialog.destroy()
                return
            dir_name = folder_dialog.get_path()
            folder_dialog.destroy()
        for source_path in source_paths:
            if os.path.isfile(source_path):
                self.add_file_task(source_path, dir_name)
            elif os.path.isdir(source_path):
                scan_folders(source_path)
        self.app.blink_page(self)
        self.scan_tasks()

    def add_file_task(self, source_path, dir_name):
        '''创建新的上传任务'''
        row = self.get_task_db(source_path)
        if row:
            print('Task is already in uploading schedule, do nothing.')
            return
        source_dir, filename = os.path.split(source_path)
        
        path = os.path.join(dir_name, filename)
        size = os.path.getsize(source_path)
        total_size = util.get_human_size(size)[0]
        task = [
            filename,
            source_path,
            path,
            size,
            0,
            State.WAITING,
            StateNames[State.WAITING],
            '0 / {0}'.format(total_size),
            0,
            ]
        row_id = self.add_task_db(task)
        task.insert(0, row_id)
        self.liststore.append(task)

    def start_task(self, row):
        '''启动上传任务.

        将任务状态设定为Uploading, 如果没有超过最大任务数的话;
        否则将它设定为Waiting.
        '''
        print('start task:', row[:])
        if row[STATE_COL] in RUNNING_STATES :
            self.scan_tasks()
            return
        row[STATE_COL] = State.WAITING
        row[STATENAME_COL] = StateNames[State.WAITING]
        self.update_task_db(row)
        self.scan_tasks()

    def pause_task(self, row):
        '''暂停下载任务'''
        print('pause task:', row[:])
        if row[STATE_COL] == State.UPLOADING:
            self.pause_worker(row)
            row[STATE_COL] = State.PAUSED
            row[STATENAME_COL] = StateNames[State.PAUSED]
            self.update_task_db(row)
            self.scan_tasks()
        elif row[STATE_COL] == State.WAITING:
            row[STATE_COL] = State.PAUSED
            row[STATENAME_COL] = StateNames[State.PAUSED]
            self.update_task_db(row)
            self.scan_tasks()

    def remove_task(self, row):
        '''删除下载任务'''
        print('remove task:', row[:])
        if row[STATE_COL] == State.UPLOADING:
            self.remove_worker(row)
        self.remove_task_db(row[FID_COL])
        tree_iter = row.iter
        if tree_iter:
            self.liststore.remove(tree_iter)

    def scan_tasks(self):
        print('scan tasks()')
        if len(self.workers.keys()) >= self.app.profile['concurr-tasks']:
            return
        for row in self.liststore:
            if len(self.workers.keys()) >= self.app.profile['concurr-tasks']:
                print('max concurrent tasks reached')
                break
            if row[STATE_COL] == State.WAITING:
                self.start_worker(row)
        return True

    def start_worker(self, row):
        print('start worker:', row[:])
        def on_worker_slice_sent(worker, fid, slice_end, md5):
            print('on worker slice sent:', fid, slice_end, md5)
            GLib.idle_add(do_worker_slice_sent, fid, slice_end, md5)

        def do_worker_slice_sent(fid, slice_end, md5):
            self.add_slice_db(fid, slice_end, md5)
            row = self.get_row_by_fid(fid)
            total_size = util.get_human_size(row[SIZE_COL])[0]
            curr_size = util.get_human_size(slice_end)[0]
            row[PERCENT_COL] = int(slice_end / row[SIZE_COL] * 100)
            row[HUMANSIZE_COL] = '{0} / {1}'.format(curr_size, total_size)
            self.update_task_db(row)

        def on_worker_merge_files(worker, fid):
            print('merge_files:', worker, fid)
            GLib.idle_add(do_worker_merge_files, fid)

        def do_worker_merge_files(fid):
            print('do worker merge files:', fid)
            def on_create_superfile(pcs_file, error=None):
                print('on create superfile:', pcs_file, error)
                if error or not pcs_file:
                    print('failed to create super file.')
                    do_worker_error(fid)
                    return
                else:
                    self.remove_slice_db(fid)
                    do_worker_uploaded(fid)

            block_list = self.get_slice_db(fid)
            row = self.get_row_by_fid(fid)
            if not block_list:
                print('Block list is empty while creating super file:', fid)
            else:
                gutil.async_call(
                    pcs.create_superfile, self.app.cookie, row[PATH_COL],
                    block_list, callback=on_create_superfile)

        def on_worker_uploaded(worker, fid):
            GLib.idle_add(do_worker_uploaded, fid)

        def do_worker_uploaded(fid):
            print('do worker uploaded:', fid)
            row = self.get_row_by_fid(fid)
            row[PERCENT_COL] = 100
            total_size = util.get_human_size(row[SIZE_COL])[0]
            row[HUMANSIZE_COL] = '{0} / {1}'.format(total_size, total_size)
            row[STATE_COL] = State.FINISHED
            row[STATENAME_COL] = StateNames[State.FINISHED]
            self.update_task_db(row)
            self.workers.pop(fid, None)
            self.app.toast(_('{0} uploaded').format(row[NAME_COL]))
            self.scan_tasks()

        def on_worker_network_error(worker, fid):
            print('UploadPage.network error')
            GLib.idle_add(do_worker_error, fid)

        def do_worker_error(fid):
            print('do worker error:', fid)
            row = self.get_row_by_fid(fid)
            row[PERCENT_COL] = 0
            row[STATE_COL] = State.ERROR
            row[STATENAME_COL] = StateNames[State.ERROR]
            self.update_task_db(row)
            self.remove_worker(fid)
            self.scan_tasks()

        if row[FID_COL] in self.workers:
            return
        row[STATE_COL] = State.UPLOADING
        row[STATENAME_COL] = StateNames[State.UPLOADING]
        threshold = self.app.profile['upload-threshold'] * (2 ** 20)
        worker = Uploader(self, row, threshold, self.app.cookie, self.app.tokens)
        self.workers[row[FID_COL]] = (worker, row)
        # For slice upload
        worker.connect('slice-sent', on_worker_slice_sent)
        worker.connect('merge-files', on_worker_merge_files)
        # For upload_small_files/rapid_upload
        worker.connect('uploaded', on_worker_uploaded)
        worker.connect('network-error', on_worker_network_error)
        worker.start()

    def pause_worker(self, fid):
        print('UploadPage.pause_worker():', fid)

    def remove_worker(self, fid, stop=True):
        print('remove worker:', fid)
        if fid not in self.workers:
            return
        worker = self.workers[fid][0]
        if stop:
            worker.stop()
        else:
            worker.pause()
        self.workers.pop(fid, None)

    def get_row_by_source_path(self, source_path):
        for row in self.liststore:
            if row[SOURCEPATH_COL] == source_path:
                return row
        return None

    def get_row_by_fid(self, fid):
        for row in self.liststore:
            if row[FID_COL] == fid:
                return row
        return None

    def operate_selected_rows(self, operator):
        '''对选中的条目进行操作.

        operator  - 处理函数
        '''
        print('operate selected rows:', operator)
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        print('tree paths:', tree_paths)
        for tree_path in tree_paths:
            index = tree_path.get_indices()[0]
            row = self.liststore[index]
            operator(row)

    def on_start_button_clicked(self, button):
        print('on start button clicked')
        self.operate_selected_rows(self.start_task)

    def on_pause_button_clicked(self, button):
        print('on pause button clicked')
        self.operate_selected_rows(self.pause_task)

    def on_remove_button_clicked(self, button):
        print('on remove button clicked')
        self.operate_selected_rows(self.remove_task)

    def on_open_folder_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths or len(tree_paths) != 1:
            return
        tree_path = tree_paths[0]
        path = model[tree_path][PATH_COL]
        dir_name = os.path.split(path)[0]
        self.app.home_page.load(dir_name)
        self.app.switch_page(self.app.home_page)

    def on_upload_button_clicked(self, button):
        self.add_task()
