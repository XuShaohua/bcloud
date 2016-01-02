
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import math
import os
import sqlite3

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud.const import UploadState as State
from bcloud.const import ValidatePathState
from bcloud.const import ValidatePathStateText
from bcloud.FolderBrowserDialog import FolderBrowserDialog
from bcloud.Uploader import Uploader
from bcloud import gutil
from bcloud.log import logger
from bcloud import pcs
from bcloud import util

(FID_COL, NAME_COL, SOURCEPATH_COL, PATH_COL, SIZE_COL,
    CURRSIZE_COL, STATE_COL, STATENAME_COL, HUMANSIZE_COL,
    PERCENT_COL, TOOLTIP_COL, THRESHOLD_COL) = list(range(12))
TASK_FILE = 'upload.sqlite'

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

    icon_name = 'folder-upload-symbolic'
    disname = _('Upload')
    name = 'UploadPage'
    tooltip = _('Uploading files')
    first_run = True
    workers = {}  # {`fid`: (worker, row)}
    commit_count = 0

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
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

            upload_box = Gtk.Box()
            upload_box_context = upload_box.get_style_context()
            upload_box_context.add_class(Gtk.STYLE_CLASS_RAISED)
            upload_box_context.add_class(Gtk.STYLE_CLASS_LINKED)
            self.headerbar.pack_start(upload_box)

            upload_file_button = Gtk.Button()
            upload_file_img = Gtk.Image.new_from_icon_name(
                    'folder-upload-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
            upload_file_button.set_image(upload_file_img)
            upload_file_button.set_tooltip_text(_('Upload files'))
            upload_file_button.connect('clicked',
                                       self.on_upload_file_button_clicked)
            upload_box.pack_start(upload_file_button, False, False, 0)

            upload_folder_button = Gtk.Button()
            upload_folder_img = Gtk.Image.new_from_icon_name(
                    'folder-upload-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
            upload_folder_button.set_image(upload_folder_img)
            upload_folder_button.set_tooltip_text(_('Upload folders'))
            upload_folder_button.connect('clicked',
                                         self.on_upload_folder_button_clicked)
            upload_box.pack_start(upload_folder_button, False, False, 0)

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
            right_box.pack_start(remove_finished_button, False, False, 0)
        else:
            control_box = Gtk.Box()
            self.pack_start(control_box, False, False, 0)

            start_button = Gtk.Button.new_with_label(_('Start'))
            start_button.connect('clicked', self.on_start_button_clicked)
            control_box.pack_start(start_button, False, False, 0)

            pause_button = Gtk.Button.new_with_label(_('Pause'))
            pause_button.connect('clicked', self.on_pause_button_clicked)
            control_box.pack_start(pause_button, False, False, 0)

            upload_file_button = Gtk.Button.new_with_label(_('Upload Files'))
            upload_file_button.set_tooltip_text(_('Upload files'))
            upload_file_button.connect('clicked',
                                       self.on_upload_file_button_clicked)
            control_box.pack_start(upload_file_button, False, False, 0)

            upload_folder_button = Gtk.Button.new_with_label(
                    _('Upload Folders'))
            upload_folder_button.set_tooltip_text(_('Upload folders'))
            upload_folder_button.connect('clicked',
                                         self.on_upload_folder_button_clicked)
            control_box.pack_start(upload_folder_button, False, False, 0)

            open_folder_button = Gtk.Button.new_with_label(_('Open Directory'))
            open_folder_button.connect('clicked',
                                       self.on_open_folder_button_clicked)
            open_folder_button.props.margin_left = 40
            control_box.pack_start(open_folder_button, False, False, 0)

            remove_finished_button = Gtk.Button.new_with_label(
                    _('Remove completed tasks'))
            remove_finished_button.connect('clicked',
                    self.on_remove_finished_button_clicked)
            control_box.pack_end(remove_finished_button, False, False, 0)

            remove_button = Gtk.Button.new_with_label(_('Remove'))
            remove_button.connect('clicked', self.on_remove_button_clicked)
            control_box.pack_end(remove_button, False, False, 0)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)
        
        # fid, source_name, source_path, path, size,
        # currsize, state, statename, humansize, percent, tooltip
        # slice size
        self.liststore = Gtk.ListStore(GObject.TYPE_INT, str, str, str,
                                       GObject.TYPE_INT64, GObject.TYPE_INT64,
                                       int, str, str, GObject.TYPE_INT, str,
                                       GObject.TYPE_INT64)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_headers_clickable(True)
        self.treeview.set_reorderable(True)
        self.treeview.set_search_column(NAME_COL)
        self.treeview.set_tooltip_column(TOOLTIP_COL)
        self.selection = self.treeview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
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

    def check_first(self):
        if self.first_run:
            self.first_run = False
            self.load()

    def on_page_show(self):
        if Config.GTK_GE_312:
            self.app.window.set_titlebar(self.headerbar)
            self.headerbar.show_all()

    def load(self):
        self.show_all()
        self.init_db()
        self.load_tasks_from_db()

    def init_db(self):
        cache_path = os.path.join(Config.CACHE_DIR,
                                  self.app.profile['username'])
        if not os.path.exists(cache_path):
            os.makedirs(cache_path, exist_ok=True)
        db = os.path.join(cache_path, TASK_FILE)
        self.conn = sqlite3.connect(db)
        self.cursor = self.conn.cursor()
        sql = '''CREATE TABLE IF NOT EXISTS upload (
        fid INTEGER PRIMARY KEY,
        name CHAR NOT NULL,
        source_path CHAR NOT NULL,
        path CHAR NOT NULL,
        size INTEGER NOT NULL,
        curr_size INTEGER NOT NULL,
        state INTEGER NOT NULL,
        state_name CHAR NOT NULL,
        human_size CHAR NOT NULL,
        percent INTEGER NOT NULL,
        tooltip CHAR,
        threshold INTEGER NOT NULL
        )
        '''
        self.cursor.execute(sql)
        sql = '''CREATE TABLE IF NOT EXISTS slice (
        fid INTEGER NOT NULL,
        slice_end INTEGER NOT NULL,
        md5 CHAR NOT NULL
        )
        '''
        self.cursor.execute(sql)

    def reload(self):
        pass

    def load_tasks_from_db(self):
        sql = 'SELECT * FROM upload'
        req = self.cursor.execute(sql)
        for task in req:
            self.liststore.append(task)

    def check_commit(self, force=False):
        '''当修改数据库超过50次后, 就自动commit数据.'''
        self.commit_count = self.commit_count + 1
        if force or self.commit_count >= 50:
            self.commit_count = 0
            self.conn.commit()

    def add_task_db(self, task, force=True):
        '''向数据库中写入一个新的任务记录, 并返回它的fid'''
        sql = '''INSERT INTO upload (
        name, source_path, path, size, curr_size, state, state_name,
        human_size, percent, tooltip, threshold)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        req = self.cursor.execute(sql, task)
        self.check_commit(force=force)
        return req.lastrowid

    def add_slice_db(self, fid, slice_end, md5):
        '''在数据库中加入上传任务分片信息'''
        sql = 'INSERT INTO slice VALUES(?, ?, ?)'
        self.cursor.execute(sql, (fid, slice_end, md5))
        self.check_commit()

    def get_task_db(self, source_path):
        '''从数据库中查询source_path的信息.
        
        如果存在的话, 就返回这条记录;
        如果没有的话, 就返回None
        '''
        sql = 'SELECT * FROM upload WHERE source_path=?'
        req = self.cursor.execute(sql, [source_path, ])
        if req:
            return req.fetchone()
        else:
            None

    def get_slice_db(self, fid):
        '''从数据库中取得fid的所有分片.
        
        返回的是一个list, 里面是按顺序排好的md5的值
        '''
        sql = 'SELECT md5 FROM slice WHERE fid=?'
        req = self.cursor.execute(sql, [fid, ])
        if req:
            return [r[0] for r in req]
        else:
            return None

    def update_task_db(self, row, force=False):
        '''更新数据库中的任务信息'''
        sql = '''UPDATE upload SET 
        curr_size=?, state=?, state_name=?, human_size=?, percent=?
        WHERE fid=?
        '''
        self.cursor.execute(sql, [
            row[CURRSIZE_COL], row[STATE_COL], row[STATENAME_COL],
            row[HUMANSIZE_COL], row[PERCENT_COL], row[FID_COL]
        ])
        self.check_commit(force=force)

    def remove_task_db(self, fid, force=False):
        '''将任务从数据库中删除'''
        self.remove_slice_db(fid)
        sql = 'DELETE FROM upload WHERE fid=?'
        self.cursor.execute(sql, [fid, ])
        self.check_commit(force=force)

    def remove_slice_db(self, fid):
        '''将上传任务的分片从数据库中删除'''
        sql = 'DELETE FROM slice WHERE fid=?'
        self.cursor.execute(sql, [fid, ])
        self.check_commit()

    def on_destroy(self, *args):
        if not self.first_run:
            self.conn.commit()
            for row in self.liststore:
                self.pause_task(row, scan=False)
            self.conn.commit()
            self.conn.close()

    # Open API
    def add_file_task(self, dir_name=None):
        '''添加上传任务, 会弹出一个选择文件的对话框'''
        file_dialog = Gtk.FileChooserDialog(_('Choose Files..'),
                self.app.window, Gtk.FileChooserAction.OPEN,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OK, Gtk.ResponseType.OK))
        file_dialog.set_modal(True)
        file_dialog.set_select_multiple(True)
        file_dialog.set_default_response(Gtk.ResponseType.OK)
        response = file_dialog.run()
        if response != Gtk.ResponseType.OK:
            file_dialog.destroy()
            return
        source_paths = file_dialog.get_filenames()
        file_dialog.destroy()
        if source_paths:
            self.upload_files(source_paths, dir_name)

    def add_folder_task(self, dir_name=None):
        '''添加上传任务, 会弹出一个选择文件夹的对话框'''
        folder_dialog = Gtk.FileChooserDialog(_('Choose Folders..'),
                self.app.window, Gtk.FileChooserAction.SELECT_FOLDER,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OK, Gtk.ResponseType.OK))
        folder_dialog.set_modal(True)
        folder_dialog.set_select_multiple(True)
        folder_dialog.set_default_response(Gtk.ResponseType.OK)
        folder_dialog.set_current_folder(Config.HOME_DIR)
        response = folder_dialog.run()
        if response != Gtk.ResponseType.OK:
            folder_dialog.destroy()
            return
        source_paths = folder_dialog.get_filenames()
        folder_dialog.destroy()
        if source_paths:
            self.upload_files(source_paths, dir_name)

    def add_bg_task(self, source_path, dest_path):
        GLib.idle_add(self.bg_upload_file,  source_path, dest_path)

    def bg_upload_file(self, source_path, dest_path):

        self.check_first()
        self.upload_file(source_path, dest_path)
        self.scan_tasks()

    # Open API
    def upload_files(self, source_paths, dir_name=None):
        '''批量创建上传任务, 会扫描子目录并依次上传.

        source_path - 本地文件的绝对路径
        dir_name    - 文件在服务器上的父目录, 如果为None的话, 会弹出一个
                      对话框让用户来选择一个目录.
        '''
        def scan_folders(folder_path):
            file_list = os.listdir(folder_path)
            source_paths = [os.path.join(folder_path, f) for f in file_list]
            self.upload_files(source_paths,
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
        invalid_paths = []
        for source_path in source_paths:
            if util.validate_pathname(source_path) != ValidatePathState.OK:
                invalid_paths.append(source_path)
                continue
            if (os.path.split(source_path)[1].startswith('.') and
                    not self.app.profile['upload-hidden-files']):
                continue
            if os.path.isfile(source_path):
                self.upload_file(source_path, dir_name)
            elif os.path.isdir(source_path):
                scan_folders(source_path)

        self.app.blink_page(self)
        self.scan_tasks()

        if not invalid_paths:
            return
        dialog = Gtk.Dialog(_('Invalid Filepath'), self.app.window,
                            Gtk.DialogFlags.MODAL,
                            (Gtk.STOCK_CLOSE, Gtk.ResponseType.OK))
        dialog.set_default_size(640, 480)
        dialog.set_border_width(10)
        box = dialog.get_content_area()

        scrolled_window = Gtk.ScrolledWindow()
        box.pack_start(scrolled_window, True, True, 0)
        text_buffer = Gtk.TextBuffer()
        textview = Gtk.TextView.new_with_buffer(text_buffer)
        scrolled_window.add(textview)
        for invalid_path in invalid_paths:
            text_buffer.insert_at_cursor(invalid_path)
            text_buffer.insert_at_cursor('\n')

        infobar = Gtk.InfoBar()
        infobar.set_message_type(Gtk.MessageType.ERROR)
        box.pack_end(infobar, False, False, 0)
        info_label= Gtk.Label()
        infobar.get_content_area().pack_start(info_label, False, False, 0)
        info_label.set_label(''.join([
            '* ', ValidatePathStateText[1], '\n',
            '* ', ValidatePathStateText[2], '\n',
            '* ', ValidatePathStateText[3], '\n',
        ]))

        box.show_all()
        dialog.run()
        dialog.destroy()

    def upload_file(self, source_path, dir_name):
        '''上传一个文件'''
        row = self.get_task_db(source_path)
        source_dir, filename = os.path.split(source_path)
        
        path = os.path.join(dir_name, filename)
        size = os.path.getsize(source_path)
        total_size = util.get_human_size(size)[0]
        tooltip = gutil.escape(_('From {0}\nTo {1}').format(source_path, path))
        if size < 2 ** 27:           # 128M 
            threshold = 2 ** 17      # 128K
        elif size < 2 ** 29:         # 512M
            threshold =  2 ** 19     # 512K
        elif size < 10 * (2 ** 30):  # 10G
            threshold = math.ceil(size / 1000)
        else:
            self.app.toast(_('{0} is too large to upload (>10G).').format(path))
            return
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
            tooltip,
            threshold,
        ]
        row_id = self.add_task_db(task, force=False)
        task.insert(0, row_id)
        self.liststore.append(task)

    def start_task(self, row, scan=True):
        '''启动上传任务.

        将任务状态设定为Uploading, 如果没有超过最大任务数的话;
        否则将它设定为Waiting.
        '''
        if row[STATE_COL] in RUNNING_STATES :
            self.scan_tasks()
            return
        row[STATE_COL] = State.WAITING
        row[STATENAME_COL] = StateNames[State.WAITING]
        self.update_task_db(row)
        if scan:
            self.scan_tasks()

    # Open API
    def pause_tasks(self):
        '''暂停所有上传任务'''
        if self.first_run:
            return
        for row in self.liststore:
            self.pause_task(row, scan=False)

    def pause_task(self, row, scan=True):
        '''暂停下载任务'''
        if row[STATE_COL] == State.UPLOADING:
            self.remove_worker(row[FID_COL], stop=False)
        if row[STATE_COL] in (State.UPLOADING, State.WAITING):
            row[STATE_COL] = State.PAUSED
            row[STATENAME_COL] = StateNames[State.PAUSED]
            self.update_task_db(row)
            if scan:
                self.scan_tasks()

    def remove_task(self, row, scan=True):
        '''删除下载任务'''
        if row[STATE_COL] == State.UPLOADING:
            self.remove_worker(row[FID_COL], stop=True)
        self.remove_task_db(row[FID_COL])
        tree_iter = row.iter
        if tree_iter:
            self.liststore.remove(tree_iter)
        if scan:
            self.scan_tasks()

    def scan_tasks(self):
        if len(self.workers.keys()) >= self.app.profile['concurr-upload']:
            return
        for row in self.liststore:
            if len(self.workers.keys()) >= self.app.profile['concurr-upload']:
                break
            if row[STATE_COL] == State.WAITING:
                self.start_worker(row)
        return True

    def start_worker(self, row):
        def on_worker_slice_sent(worker, fid, slice_end, md5):
            GLib.idle_add(do_worker_slice_sent, fid, slice_end, md5)

        def do_worker_slice_sent(fid, slice_end, md5):
            if fid not in self.workers:
                return
            row = self.get_row_by_fid(fid)
            if not row:
                return
            row[CURRSIZE_COL] = slice_end
            total_size = util.get_human_size(row[SIZE_COL])[0]
            curr_size = util.get_human_size(slice_end, False)[0]
            row[PERCENT_COL] = int(slice_end / row[SIZE_COL] * 100)
            row[HUMANSIZE_COL] = '{0} / {1}'.format(curr_size, total_size)
            self.update_task_db(row)
            self.add_slice_db(fid, slice_end, md5)

        def on_worker_merge_files(worker, fid):
            GLib.idle_add(do_worker_merge_files, fid)

        def do_worker_merge_files(fid):
            def on_create_superfile(pcs_file, error=None):
                if error or not pcs_file:
                    self.app.toast(_('Failed to upload, please try again'))
                    logger.error('UploadPage.do_worker_merge_files: %s, %s' %
                                 (pcs_file, error))
                    do_worker_error(fid)
                    return
                else:
                    self.remove_slice_db(fid)
                    do_worker_uploaded(fid)

            block_list = self.get_slice_db(fid)
            if fid not in self.workers:
                return
            row = self.get_row_by_fid(fid)
            if not row:
                return
            if not block_list:
                # TODO:
                pass
            else:
                gutil.async_call(pcs.create_superfile, self.app.cookie,
                                 row[PATH_COL], block_list,
                                 callback=on_create_superfile)

        def on_worker_uploaded(worker, fid):
            GLib.idle_add(do_worker_uploaded, fid)

        def do_worker_uploaded(fid):
            if fid not in self.workers:
                return
            row = self.get_row_by_fid(fid)
            if not row:
                return
            row[PERCENT_COL] = 100
            total_size = util.get_human_size(row[SIZE_COL])[0]
            row[HUMANSIZE_COL] = '{0} / {1}'.format(total_size, total_size)
            row[STATE_COL] = State.FINISHED
            row[STATENAME_COL] = StateNames[State.FINISHED]
            self.update_task_db(row, force=True)
            self.workers.pop(fid, None)
            self.app.toast(_('{0} uploaded').format(row[NAME_COL]))
            self.app.home_page.reload()
            self.scan_tasks()

        def on_worker_disk_error(worker, fid):
            GLib.idle_add(do_worker_error, fid)

        def on_worker_network_error(worker, fid):
            GLib.idle_add(do_worker_error, fid)

        def do_worker_error(fid):
            row = self.get_row_by_fid(fid)
            if not row:
                return
            row[STATE_COL] = State.ERROR
            row[STATENAME_COL] = StateNames[State.ERROR]
            self.update_task_db(row)
            self.remove_worker(fid, stop=False)
            self.scan_tasks()

        if row[FID_COL] in self.workers:
            return
        row[STATE_COL] = State.UPLOADING
        row[STATENAME_COL] = StateNames[State.UPLOADING]
        worker = Uploader(self, row, self.app.cookie, self.app.tokens)
        self.workers[row[FID_COL]] = (worker, row)
        # For slice upload
        worker.connect('slice-sent', on_worker_slice_sent)
        worker.connect('merge-files', on_worker_merge_files)
        # For upload_small_files/rapid_upload
        worker.connect('uploaded', on_worker_uploaded)
        worker.connect('disk-error', on_worker_disk_error)
        worker.connect('network-error', on_worker_network_error)
        worker.start()

    def remove_worker(self, fid, stop=True):
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
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        fids = []
        for tree_path in tree_paths:
            fids.append(model[tree_path][FID_COL])
        for fid in fids:
            row = self.get_row_by_fid(fid)
            if row:
                operator(row)

    def on_start_button_clicked(self, button):
        self.operate_selected_rows(self.start_task)

    def on_pause_button_clicked(self, button):
        self.operate_selected_rows(self.pause_task)

    def on_remove_button_clicked(self, button):
        self.operate_selected_rows(self.remove_task)

    def on_remove_finished_button_clicked(self, button):
        tree_iters = []
        for row in self.liststore:
            if row[STATE_COL] == State.FINISHED:
                tree_iters.append(self.liststore.get_iter(row.path))
        for tree_iter in tree_iters:
            if tree_iter:
                self.remove_task_db(self.liststore[tree_iter][FID_COL], False)
                self.liststore.remove(tree_iter)
        self.check_commit()

    def on_open_folder_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths or len(tree_paths) != 1:
            return
        tree_path = tree_paths[0]
        path = model[tree_path][PATH_COL]
        dir_name = os.path.split(path)[0]
        self.app.home_page.load(dir_name)
        self.app.switch_page(self.app.home_page)

    def on_upload_file_button_clicked(self, button):
        self.add_file_task()

    def on_upload_folder_button_clicked(self, button):
        self.add_folder_task()
