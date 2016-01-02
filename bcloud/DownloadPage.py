
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import json
import os
import sqlite3
import threading
import time

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud.Downloader import Downloader, get_tmp_filepath
from bcloud import gutil
from bcloud import pcs
from bcloud import util
from bcloud.const import State
from bcloud.Shutdown import Shutdown


TASK_FILE = 'tasks.sqlite'
RUNNING_STATES = (State.FINISHED, State.DOWNLOADING, State.WAITING)
(NAME_COL, PATH_COL, FSID_COL, SIZE_COL, CURRSIZE_COL, LINK_COL,
    ISDIR_COL, SAVENAME_COL, SAVEDIR_COL, STATE_COL, STATENAME_COL,
    HUMANSIZE_COL, PERCENT_COL, TOOLTIP_COL) = list(range(14))

StateNames = (
    _('DOWNLOADING'),
    _('WAITING'),
    _('PAUSED'),
    _('FINISHED'),
    _('CANCELED'),
    _('ERROR'),
)


class ConfirmDialog(Gtk.MessageDialog):

    def __init__(self, app, multiple_files):
        if multiple_files:
            text = _('Do you want to remove unfinished tasks?')
        else:
            text = _('Do you want to remove unfinished task?')
        super().__init__(app.window, Gtk.DialogFlags.MODAL,
                         Gtk.MessageType.WARNING, Gtk.ButtonsType.YES_NO,
                         text)
        self.app = app
        box = self.get_message_area()
        remember_button = Gtk.CheckButton(_('Do not ask again'))
        remember_button.set_active(
                not self.app.profile['confirm-download-deletion'])
        remember_button.connect('toggled', self.on_remember_button_toggled)
        box.pack_start(remember_button, False, False, 0)
        box.show_all()

    def on_remember_button_toggled(self, button):
        self.app.profile['confirm-download-deletion'] = not button.get_active()


class DownloadPage(Gtk.Box):
    '''下载任务管理器, 处理下载任务的后台调度.

    * 它是与UI进行交互的接口.
    * 它会保存所有下载任务的状态.
    * 它来为每个下载线程分配任务.
    * 它会自动管理磁盘文件结构, 在必要时会创建必要的目录.
    * 它会自动获取文件的最新的下载链接(这个链接有效时间是8小时).

    每个task(pcs_file)包含这些信息:
    fs_id - 服务器上的文件UID
    md5 - 文件MD5校验值
    size - 文件大小
    path - 文件在服务器上的绝对路径
    name - 文件在服务器上的名称
    savePath - 保存到的绝对路径
    save_name - 保存时的文件名
    currRange - 当前下载的进度, 以字节为单位, 在HTTP Header中可用.
    state - 任务状态 
    link - 文件的下载最终URL, 有效期大约是8小时, 超时后要重新获取.
    '''

    icon_name = 'folder-download-symbolic'
    disname = _('Download')
    name = 'DownloadPage'
    tooltip = _('Downloading files')
    first_run = True
    workers = {}                    # { `fs_id': (worker,row) }
    app_infos = {}                  # { `fs_id': app }
    commit_count = 0
    download_speed_received = 0     # size of received data
    download_speed_sid = 0          # signal id
    DOWNLOAD_SPEED_INTERVAL = 3000  # update download speed every 3s

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.shutdown = Shutdown()

        if Config.GTK_GE_312:
            self.headerbar = Gtk.HeaderBar()
            self.headerbar.props.show_close_button = True
            self.headerbar.props.has_subtitle = False
            self.headerbar.set_title(self.disname)

            control_box = Gtk.Box()
            control_box_context = control_box.get_style_context()
            control_box_context.add_class(Gtk.STYLE_CLASS_RAISED)
            control_box_context.add_class(Gtk.STYLE_CLASS_LINKED)
            self.headerbar.pack_start(control_box)

            start_button = Gtk.Button()
            start_img = Gtk.Image.new_from_icon_name(
                    'media-playback-start-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            start_button.set_image(start_img)
            start_button.set_tooltip_text(_('Start'))
            start_button.connect('clicked', self.on_start_button_clicked)
            control_box.pack_start(start_button, False, False, 0)

            pause_button = Gtk.Button()
            pause_img = Gtk.Image.new_from_icon_name(
                    'media-playback-pause-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            pause_button.set_image(pause_img)
            pause_button.set_tooltip_text(_('Pause'))
            pause_button.connect('clicked', self.on_pause_button_clicked)
            control_box.pack_start(pause_button, False, False, 0)

            open_folder_button = Gtk.Button()
            open_folder_img = Gtk.Image.new_from_icon_name(
                    'document-open-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
            open_folder_button.set_image(open_folder_img)
            open_folder_button.set_tooltip_text(_('Open target directory'))
            open_folder_button.connect('clicked',
                                       self.on_open_folder_button_clicked)
            self.headerbar.pack_start(open_folder_button)

            shutdown_button = Gtk.ToggleButton()
            shutdown_img = Gtk.Image.new_from_icon_name(
                    'system-shutdown-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
            shutdown_button.set_image(shutdown_img)
            shutdown_button.set_tooltip_text(
                    _('Shutdown system after all tasks have finished'))
            shutdown_button.set_sensitive(self.shutdown.can_shutdown)
            shutdown_button.props.margin_start = 5
            self.shutdown_button = shutdown_button
            self.headerbar.pack_start(shutdown_button)

            right_box = Gtk.Box()
            right_box_context = right_box.get_style_context()
            right_box_context.add_class(Gtk.STYLE_CLASS_RAISED)
            right_box_context.add_class(Gtk.STYLE_CLASS_LINKED)
            self.headerbar.pack_end(right_box)

            remove_button = Gtk.Button()
            remove_img = Gtk.Image.new_from_icon_name('list-remove-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            remove_button.set_image(remove_img)
            remove_button.set_tooltip_text(_('Remove selected tasks'))
            remove_button.connect('clicked', self.on_remove_button_clicked)
            right_box.pack_start(remove_button, False, False, 0)

            remove_finished_button = Gtk.Button()
            remove_finished_img = Gtk.Image.new_from_icon_name(
                    'list-remove-all-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
            remove_finished_button.set_image(remove_finished_img)
            remove_finished_button.set_tooltip_text(_('Remove completed tasks'))
            remove_finished_button.connect('clicked',
                    self.on_remove_finished_button_clicked)
            right_box.pack_end(remove_finished_button, False, False, 0)

            self.speed_label = Gtk.Label()
            self.headerbar.pack_end(self.speed_label)
        else:
            control_box = Gtk.Box()
            self.pack_start(control_box, False, False, 0)

            start_button = Gtk.Button.new_with_label(_('Start'))
            start_button.connect('clicked', self.on_start_button_clicked)
            control_box.pack_start(start_button, False, False, 0)

            pause_button = Gtk.Button.new_with_label(_('Pause'))
            pause_button.connect('clicked', self.on_pause_button_clicked)
            control_box.pack_start(pause_button, False, False, 0)

            open_folder_button = Gtk.Button.new_with_label(_('Open Directory'))
            open_folder_button.connect('clicked',
                                       self.on_open_folder_button_clicked)
            open_folder_button.props.margin_left = 40
            control_box.pack_start(open_folder_button, False, False, 0)

            shutdown_button = Gtk.ToggleButton()
            shutdown_button.set_label(_('Shutdown'))
            shutdown_button.set_tooltip_text(
                    _('Shutdown system after all tasks have finished'))
            shutdown_button.set_sensitive(self.shutdown.can_shutdown)
            shutdown_button.props.margin_left = 5
            self.shutdown_button = shutdown_button
            control_box.pack_start(shutdown_button, False, False, 0)

            remove_finished_button = Gtk.Button.new_with_label(
                    _('Remove completed tasks'))
            remove_finished_button.connect('clicked',
                    self.on_remove_finished_button_clicked)
            control_box.pack_end(remove_finished_button, False, False, 0)

            remove_button = Gtk.Button.new_with_label(_('Remove'))
            remove_button.connect('clicked', self.on_remove_button_clicked)
            control_box.pack_end(remove_button, False, False, 0)

            self.speed_label = Gtk.Label()
            control_box.pack_end(self.speed_label, False, False, 5)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)

        # name, path, fs_id, size, currsize, link,
        # isdir, save_dir, save_name, state, statename,
        # humansize, percent, tooltip
        self.liststore = Gtk.ListStore(str, str, str, GObject.TYPE_INT64,
                                       GObject.TYPE_INT64, str,
                                       GObject.TYPE_INT, str, str,
                                       GObject.TYPE_INT, str, str,
                                       GObject.TYPE_INT, str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_tooltip_column(TOOLTIP_COL)
        self.treeview.set_headers_clickable(True)
        self.treeview.set_reorderable(True)
        self.treeview.set_search_column(NAME_COL)
        self.selection = self.treeview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.treeview.connect('button-press-event',
                              self.on_treeview_button_pressed)
        scrolled_win.add(self.treeview)
        
        name_cell = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END,
                                         ellipsize_set=True)
        name_col = Gtk.TreeViewColumn(_('Name'), name_cell, text=NAME_COL)
        name_col.set_expand(True)
        self.treeview.append_column(name_col)
        name_col.set_sort_column_id(NAME_COL)
        self.liststore.set_sort_func(NAME_COL, gutil.tree_model_natsort)

        percent_cell = Gtk.CellRendererProgress()
        percent_col = Gtk.TreeViewColumn(_('Progress'), percent_cell,
                                         value=PERCENT_COL)
        self.treeview.append_column(percent_col)
        percent_col.props.min_width = 145
        percent_col.set_sort_column_id(PERCENT_COL)

        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(_('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)
        size_col.props.min_width = 100
        size_col.set_sort_column_id(SIZE_COL)

        state_cell = Gtk.CellRendererText()
        state_col = Gtk.TreeViewColumn(_('State'), state_cell,
                                       text=STATENAME_COL)
        self.treeview.append_column(state_col)
        state_col.props.min_width = 100
        state_col.set_sort_column_id(PERCENT_COL)

    def on_page_show(self):
        if Config.GTK_GE_312:
            self.app.window.set_titlebar(self.headerbar)
            self.headerbar.show_all()

    def check_first(self):
        if self.first_run:
            self.first_run = False
            self.load()

    def load(self):
        self.init_db()
        self.load_tasks_from_db()
        self.download_speed_init()
        self.show_all()

    def init_db(self):
        '''这个任务数据库只在程序开始时读入, 在程序关闭时导出.

        因为Gtk没有像在Qt中那么方便的使用SQLite, 而必须将所有数据读入一个
        liststore中才行.
        '''
        cache_path = os.path.join(Config.CACHE_DIR,
                                  self.app.profile['username'])
        if not os.path.exists(cache_path):
            os.makedirs(cache_path, exist_ok=True)
        db = os.path.join(cache_path, TASK_FILE)
        self.conn = sqlite3.connect(db)
        self.cursor = self.conn.cursor()
        sql = '''CREATE TABLE IF NOT EXISTS tasks (
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
        percent INT NOT NULL,
        tooltip CHAR
        )
        '''
        self.cursor.execute(sql)

    def on_destroy(self, *args):
        if not self.first_run:
            self.pause_tasks()
            self.conn.commit()
            self.conn.close()
            for worker, row in self.workers.values():
                worker.pause()
                row[CURRSIZE_COL] = worker.row[CURRSIZE_COL]
    
    def load_tasks_from_db(self):
        req = self.cursor.execute('SELECT * FROM tasks')
        for task in req:
            self.liststore.append(task)

    def add_task_db(self, task):
        '''向数据库中写入一个新的任务记录'''
        sql = 'INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
        req = self.cursor.execute(sql, task)
        self.check_commit()

    def get_task_db(self, fs_id):
        '''从数据库中查询fsid的信息.
        
        如果存在的话, 就返回这条记录;
        如果没有的话, 就返回None
        '''
        sql = 'SELECT * FROM tasks WHERE fsid=?'
        req = self.cursor.execute(sql, [fs_id, ])
        if req:
            return req.fetchone()
        else:
            None

    def check_commit(self, force=False):
        '''当修改数据库超过100次后, 就自动commit数据.'''
        self.commit_count = self.commit_count + 1
        if force or self.commit_count >= 100:
            self.commit_count = 0
            self.conn.commit()

    def update_task_db(self, row):
        '''更新数据库中的任务信息'''
        sql = '''UPDATE tasks SET 
        currsize=?, state=?, statename=?, humansize=?, percent=?
        WHERE fsid=?
        '''
        self.cursor.execute(sql, [
            row[CURRSIZE_COL], row[STATE_COL], row[STATENAME_COL],
            row[HUMANSIZE_COL], row[PERCENT_COL], row[FSID_COL]
        ])
        self.check_commit()

    def remove_task_db(self, fs_id):
        '''将任务从数据库中删除'''
        sql = 'DELETE FROM tasks WHERE fsid=?'
        self.cursor.execute(sql, [fs_id, ])
        self.check_commit()

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
        self.app_infos[fs_id] = app_info
        self.add_task(pcs_file)

    def launch_app(self, fs_id):
        if fs_id in self.app_infos:
            row = self.get_row_by_fsid(fs_id)
            if not row:
                return
            app_info = self.app_infos[fs_id]
            filepath = os.path.join(row[SAVEDIR_COL], row[SAVENAME_COL])
            gfile = Gio.File.new_for_path(filepath)
            app_info.launch([gfile, ], None)
            self.app_infos.pop(fs_id, None)

    # Open API
    def add_tasks(self, pcs_files, dirname=''):
        '''建立批量下载任务, 包括目录'''
        def on_list_dir(info, error=None):
            path, pcs_files = info
            if error or not pcs_files:
                dialog = Gtk.MessageDialog(self.app.window,
                        Gtk.DialogFlags.MODAL,
                        Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE,
                        _('Failed to scan folder to download'))
                dialog.format_secondary_text(
                        _('Please download {0} again').format(path))
                dialog.run()
                dialog.destroy()
                return
            self.add_tasks(pcs_files, dirname)

        self.check_first()
        for pcs_file in pcs_files:
            if pcs_file['isdir']:
                gutil.async_call(pcs.list_dir_all, self.app.cookie,
                                 self.app.tokens, pcs_file['path'],
                                 callback=on_list_dir)
            else:
                self.add_task(pcs_file, dirname)
        self.check_commit(force=True)

    def add_task(self, pcs_file, dirname=''):
        '''加入新的下载任务'''
        if pcs_file['isdir']:
            return
        fs_id = str(pcs_file['fs_id'])
        row = self.get_row_by_fsid(fs_id)
        if row:
            self.app.toast(_('Task exists: {0}').format(
                           pcs_file['server_filename']))
            # 如果文件已下载完成, 就直接尝试用本地程序打开
            if row[STATE_COL] == State.FINISHED:
                self.launch_app(fs_id)
            return
        if not dirname:
            dirname = self.app.profile['save-dir']
        save_dir = os.path.dirname(
                os.path.join(dirname, pcs_file['path'][1:]))
        save_name = pcs_file['server_filename']
        human_size = util.get_human_size(pcs_file['size'])[0]
        tooltip = gutil.escape(_('From {0}\nTo {1}').format(pcs_file['path'],
                                                            save_dir))
        task = (
            pcs_file['server_filename'],
            pcs_file['path'],
            fs_id,
            pcs_file['size'],
            0,
            '',  # pcs['dlink' removed in new version.
            pcs_file['isdir'],
            save_name,
            save_dir,
            State.WAITING,
            StateNames[State.WAITING],
            human_size,
            0,
            tooltip,
        )
        self.liststore.append(task)
        self.add_task_db(task)
        self.scan_tasks()

    def scan_tasks(self, ignore_shutdown=False):
        '''扫描所有下载任务, 并在需要时启动新的下载.'''
        for row in self.liststore:
            if len(self.workers.keys()) >= self.app.profile['concurr-download']:
                break
            if row[STATE_COL] == State.WAITING:
                self.start_worker(row)

        if not self.shutdown_button.get_active() or ignore_shutdown:
            return
        # Shutdown system after all tasks have finished
        for row in self.liststore:
            if (row[STATE_COL] not in
                    (State.PAUSED, State.FINISHED, State.CANCELED)):
                return
        self.shutdown.shutdown()

    def start_worker(self, row):
        '''为task新建一个后台下载线程, 并开始下载.'''
        def on_worker_started(worker, fs_id):
            pass

        def on_worker_received(worker, fs_id, received, received_total):
            GLib.idle_add(do_worker_received, fs_id, received, received_total)

        def do_worker_received(fs_id, received, received_total):
            self.download_speed_add(received)
            row = None
            if fs_id in self.workers:
                row = self.workers[fs_id][1]
            else:
                row = self.get_row_by_fsid(fs_id)
            if not row:
                return

            row[CURRSIZE_COL] = received_total
            curr_size = util.get_human_size(row[CURRSIZE_COL], False)[0]
            total_size = util.get_human_size(row[SIZE_COL])[0]
            row[PERCENT_COL] = int(row[CURRSIZE_COL] / row[SIZE_COL] * 100)
            row[HUMANSIZE_COL] = '{0} / {1}'.format(curr_size, total_size)
            self.update_task_db(row)

        def on_worker_downloaded(worker, fs_id):
            GLib.idle_add(do_worker_downloaded, fs_id)

        def do_worker_downloaded(fs_id):
            row = None
            if fs_id in self.workers:
                row = self.workers[fs_id][1]
            else:
                row = self.get_row_by_fsid(fs_id)
            if not row:
                return
            row[CURRSIZE_COL] = row[SIZE_COL]
            row[STATE_COL] = State.FINISHED
            row[PERCENT_COL] = 100
            total_size = util.get_human_size(row[SIZE_COL])[0]
            row[HUMANSIZE_COL] = '{0} / {1}'.format(total_size, total_size)
            row[STATENAME_COL] = StateNames[State.FINISHED]
            self.update_task_db(row)
            self.check_commit(force=True)
            self.workers.pop(row[FSID_COL], None)
            self.app.toast(_('{0} downloaded'.format(row[NAME_COL])))
            self.launch_app(fs_id)
            self.scan_tasks()

        def on_worker_network_error(worker, fs_id):
            GLib.idle_add(do_worker_network_error, fs_id)

        def do_worker_network_error(fs_id):
            row = self.workers.get(fs_id, None)
            if row:
                row = row[1]
            else:
                row = self.get_row_by_fsid(fs_id)
                if not row:
                    return
            row[STATE_COL] = State.ERROR
            row[STATENAME_COL] = StateNames[State.ERROR]
            self.update_task_db(row)
            self.remove_worker(row[FSID_COL], stop=False)
            if self.app.profile['retries-each']:
                GLib.timeout_add(self.app.profile['retries-each'] * 60000,
                                 self.restart_task, row)
            else:
                self.app.toast(_('Error occurs will downloading {0}').format(
                               row[NAME_COL]))
            self.scan_tasks()

        def do_worker_disk_error(fs_id, tmp_filepath):
            # do not retry on disk-error
            self.app.toast(_('Disk Error: failed to read/write {0}').format(
                           tmp_filepath))

        def on_worker_disk_error(worker, fs_id, tmp_filepath):
            GLib.idle_add(do_worker_disk_error, fs_id, tmp_filepath)

        if not row or row[FSID_COL] in self.workers:
            return
        row[STATE_COL] = State.DOWNLOADING
        row[STATENAME_COL] = StateNames[State.DOWNLOADING]
        worker = Downloader(self, row)
        self.workers[row[FSID_COL]] = (worker, row)
        worker.connect('started', on_worker_started)
        worker.connect('received', on_worker_received)
        worker.connect('downloaded', on_worker_downloaded)
        worker.connect('network-error', on_worker_network_error)
        worker.connect('disk-error', on_worker_disk_error)
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

    def restart_task(self, row):
        '''重启下载任务.

        当指定的下载任务出现错误时(通常是网络连接超时), 如果用户允许, 就会在
        指定的时间间隔之后, 重启这个任务.
        '''
        self.start_task(row)

    def start_task(self, row, scan=True):
        '''启动下载任务.

        将任务状态设定为Downloading, 如果没有超过最大任务数的话;
        否则将它设定为Waiting.
        '''
        if not row or row[STATE_COL] in RUNNING_STATES :
            return
        row[STATE_COL] = State.WAITING
        row[STATENAME_COL] = StateNames[State.WAITING]
        self.update_task_db(row)
        if scan:
            self.scan_tasks()

    # Open API
    def pause_tasks(self):
        '''暂停所有下载任务'''
        if self.first_run:
            return
        for row in self.liststore:
            self.pause_task(row, scan=False)

    def pause_task(self, row, scan=True):
        if not row:
            return
        if row[STATE_COL] == State.DOWNLOADING:
            self.pause_worker(row)
        if row[STATE_COL] in (State.DOWNLOADING, State.WAITING):
            row[STATE_COL] = State.PAUSED
            row[STATENAME_COL] = StateNames[State.PAUSED]
            self.update_task_db(row)
            if scan:
                self.scan_tasks()

    def remove_task(self, row, scan=True):
        # 当删除正在下载的任务时, 直接调用stop_worker(), 它会自动删除本地的
        # 文件片段
        if not row:
            return

        # 如果任务尚未下载完, 弹出一个对话框, 让用户确认删除
        if row[STATE_COL] != State.FINISHED:
            if self.app.profile['confirm-download-deletion']:
                dialog = ConfirmDialog(self.app, False)
                response = dialog.run()
                dialog.destroy()
                if response != Gtk.ResponseType.YES:
                    return

        if row[STATE_COL] == State.DOWNLOADING:
            self.stop_worker(row)
        elif row[CURRSIZE_COL] < row[SIZE_COL]:
            filepath, tmp_filepath, conf_filepath = get_tmp_filepath(
                    row[SAVEDIR_COL], row[SAVENAME_COL])
            if os.path.exists(tmp_filepath):
                os.remove(tmp_filepath)
            if os.path.exists(conf_filepath):
                os.remove(conf_filepath)
        self.app_infos.pop(row[FSID_COL], None)
        self.remove_task_db(row[FSID_COL])
        tree_iter = row.iter
        if tree_iter:
            self.liststore.remove(tree_iter)
        if scan:
            self.scan_tasks()

    # handle download speed
    def download_speed_init(self):
        if not self.download_speed_sid:
            # update speed label at each 5s
            self.download_speed_sid = GLib.timeout_add(
                    self.DOWNLOAD_SPEED_INTERVAL, self.download_speed_interval)
        self.speed_label.set_text('0 kB/s')

    def download_speed_add(self, size):
        self.download_speed_received += size

    def download_speed_interval(self):
        speed = self.download_speed_received // self.DOWNLOAD_SPEED_INTERVAL
        self.speed_label.set_text('%s kB/s' % speed)
        # reset received data size
        self.download_speed_received = 0
        return True

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
            if not row:
                return
            operator(row, scan=False)
        self.check_commit(force=True)
        self.scan_tasks(ignore_shutdown=True)

    def on_start_button_clicked(self, button):
        self.operate_selected_rows(self.start_task)

    def on_pause_button_clicked(self, button):
        self.operate_selected_rows(self.pause_task)

    def on_remove_button_clicked(self, button):
        self.operate_selected_rows(self.remove_task)

    def on_remove_finished_button_clicked(self, button):
        for row in self.liststore:
            if row[STATE_COL] == State.FINISHED:
                self.remove_task(row, scan=False)
        self.check_commit(force=True)
        self.scan_tasks()

    def on_open_folder_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        for tree_path in tree_paths:
            gutil.xdg_open(self.liststore[tree_path][SAVEDIR_COL])

    def on_treeview_button_pressed(self, treeview, event):
        def on_choose_app_activated(menu_item):
            dialog = Gtk.AppChooserDialog.new_for_content_type(self.app.window,
                    Gtk.DialogFlags.MODAL, file_type)
            response = dialog.run()
            app_info = dialog.get_app_info()
            dialog.destroy()
            if response != Gtk.ResponseType.OK:
                return
            do_launch_app(app_info)

        def do_launch_app(app_info):
            row = self.get_row_by_fsid(fs_id)
            if not row:
                return
            filepath = os.path.join(row[SAVEDIR_COL], row[SAVENAME_COL])
            gfile = Gio.File.new_for_path(filepath)
            app_info.launch([gfile, ], None)

        def build_app_menu(menu, menu_item, app_info):
            menu_item.set_always_show_image(True)
            img = self.app.mime.get_app_img(app_info)
            if img:
                menu_item.set_image(img)
            menu_item.connect('activate', lambda *args: do_launch_app(app_info))
            menu.append(menu_item)

        if (event.type != Gdk.EventType.BUTTON_PRESS or
                event.button != Gdk.BUTTON_SECONDARY):
            return False
        selection = self.selection.get_selected_rows()
        if not selection or len(selection[1]) != 1:
            return False
        selected_path = selection[1][0]
        row = self.liststore[int(str(selected_path))]
        if row[STATE_COL] != State.FINISHED:
            return
        fs_id = row[FSID_COL]
        file_type = self.app.mime.get(row[PATH_COL], False, icon_size=64)[1]

        menu = Gtk.Menu()
        self.menu = menu

        default_app_info = Gio.AppInfo.get_default_for_type(file_type, False)
        app_infos = Gio.AppInfo.get_recommended_for_type(file_type)
        if app_infos:
            app_infos = [info for info in app_infos if \
                    info.get_name() != default_app_info.get_name()]
        if len(app_infos) > 1:
            launch_item = Gtk.ImageMenuItem.new_with_label(
                _('Open With {0}').format(default_app_info.get_display_name()))
            build_app_menu(menu, launch_item, default_app_info)

            more_app_item = Gtk.MenuItem.new_with_label(_('Open With'))
            menu.append(more_app_item)
            sub_menu = Gtk.Menu()
            more_app_item.set_submenu(sub_menu)

            for app_info in app_infos:
                launch_item = Gtk.ImageMenuItem.new_with_label(
                        app_info.get_display_name())
                build_app_menu(sub_menu, launch_item, app_info)
            sep_item = Gtk.SeparatorMenuItem()
            sub_menu.append(sep_item)
            choose_app_item = Gtk.MenuItem.new_with_label(
                    _('Other Application...'))
            choose_app_item.connect('activate', on_choose_app_activated)
            sub_menu.append(choose_app_item)
        else:
            if app_infos:
                app_infos = (default_app_info, app_infos[0])
            elif default_app_info:
                app_infos = (default_app_info, )
            for app_info in app_infos:
                launch_item = Gtk.ImageMenuItem.new_with_label(
                    _('Open With {0}').format(app_info.get_display_name()))
                build_app_menu(menu, launch_item, app_info)
            choose_app_item = Gtk.MenuItem.new_with_label(
                    _('Open With Other Application...'))
            choose_app_item.connect('activate', on_choose_app_activated)
            menu.append(choose_app_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)

        remove_item = Gtk.MenuItem.new_with_label(_('Remove'))
        remove_item.connect('activate', lambda *args: self.remove_task(row))
        menu.append(remove_item)

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)
