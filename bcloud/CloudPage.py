
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud import decoder
from bcloud.BTBrowserDialog import BTBrowserDialog
from bcloud.FolderBrowserDialog import FolderBrowserDialog
from bcloud.VCodeDialog import VCodeDialog
from bcloud import gutil
from bcloud import pcs
from bcloud import util


(TASKID_COL, NAME_COL, PATH_COL, SOURCEURL_COL, SIZE_COL,
    FINISHED_COL, STATUS_COL, PERCENT_COL, HUMANSIZE_COL) = list(range(9))

Status = (0, 1, )
StatusNames = (_('FINISHED'), _('DOWNLOADING'), )


class CloudPage(Gtk.Box):

    icon_name = 'cloud-symbolic'
    disname = _('Cloud')
    tooltip = _('Cloud Download')
    first_run = True

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        control_box = Gtk.Box()
        self.pack_start(control_box, False, False, 0)

        link_button = Gtk.Button.new_with_label(_('New Link Task'))
        link_button.connect('clicked', self.on_link_button_clicked)
        control_box.pack_start(link_button, False, False, 0)

        reload_button = Gtk.Button.new_with_label(_('Reload'))
        reload_button.props.margin_left = 40
        reload_button.connect('clicked', self.on_reload_button_clicked)
        control_box.pack_start(reload_button, False, False, 0)

        open_button = Gtk.Button.new_with_label(_('Open Directory'))
        open_button.connect('clicked', self.on_open_button_clicked)
        control_box.pack_start(open_button, False, False, 0)

        cancel_button = Gtk.Button.new_with_label(_('Cancel'))
        cancel_button.set_tooltip_text(_('Cancel selected tasks'))
        cancel_button.props.margin_left = 40
        cancel_button.connect('clicked', self.on_cancel_button_clicked)
        control_box.pack_start(cancel_button, False, False, 0)

        remove_button = Gtk.Button.new_with_label(_('Remove'))
        remove_button.set_tooltip_text(_('Remove selected tasks'))
        remove_button.connect('clicked', self.on_remove_button_clicked)
        control_box.pack_start(remove_button, False, False, 0)

        clear_button = Gtk.Button.new_with_label(_('Clear'))
        clear_button.set_tooltip_text(_('Clear finished or canceled tasks'))
        clear_button.connect('clicked', self.on_clear_button_clicked)
        control_box.pack_start(clear_button, False, False, 0)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)

        # task_id, name, path, source_url, size, finished_size,
        # status, percent, human_size
        self.liststore = Gtk.ListStore(
                str, str, str, str, GObject.TYPE_INT64,
                GObject.TYPE_INT64, int, int, str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.selection = self.treeview.get_selection()
        name_cell = Gtk.CellRendererText(
                ellipsize=Pango.EllipsizeMode.END, ellipsize_set=True)
        name_col = Gtk.TreeViewColumn(_('Name'), name_cell, text=NAME_COL)
        name_col.set_expand(True)
        self.treeview.append_column(name_col)
        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(
                _('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)
        #size_col.props.sizing = Gtk.TreeViewColumnSizing.AUTOSIZE
        size_col.props.min_width = 145
        percent_cell = Gtk.CellRendererProgress()
        percent_col = Gtk.TreeViewColumn(
                _('Progress'), percent_cell, value=PERCENT_COL)
        self.treeview.append_column(percent_col)
        percent_col.props.min_width = 145
        self.treeview.set_tooltip_column(PATH_COL)
        scrolled_win.add(self.treeview)

    def check_first(self):
        if self.first_run:
            self.first_run = False
            self.load()

    def load(self):
        '''获取当前的离线任务列表'''
        def on_list_task(info, error=None):
            print('on list task() --', info)
            if error or not info:
                print('Error: failed to list cloud tasks')
                return
            if 'error_code' in info and info['error_code'] != 0:
                print('Error: ', info['error_msg'])
                print(info)
                return
            tasks = info['task_info']
            for task in tasks:
                self.liststore.append([
                    task['task_id'],
                    task['task_name'],
                    task['save_path'],
                    task['source_url'],
                    0,
                    0,
                    int(task['status']),
                    0,
                    '0',
                    ])
            self.scan_tasks()

            nonlocal start
            start = start + len(tasks)
            if info['total'] > start:
                gutil.async_call(
                    pcs.cloud_list_task, self.app.cookie, self.app.tokens,
                    start, callback=on_list_task)

        start = 0
        gutil.async_call(
            pcs.cloud_list_task, self.app.cookie, self.app.tokens,
            start, callback=on_list_task)

    def reload(self, *args, **kwds):
        self.liststore.clear()
        self.load()

    def get_row_by_task_id(self, task_id):
        '''返回这个任务的TreeModelRow, 如果不存在, 就返回None.'''
        for row in self.liststore:
            if row[TASKID_COL] == task_id:
                return row
        return None

    def scan_tasks(self):
        '''定期获取离线下载任务的信息, 比如10秒钟'''
        def update_task_status(info, error=None):
            if error or not info:
                print('Error: failed to update task status')
                return
            tasks = info['task_info']
            for row in self.liststore:
                if row[TASKID_COL] not in tasks:
                    continue
                task = tasks[row[TASKID_COL]]
                row[SIZE_COL] = int(task['file_size'])
                row[FINISHED_COL] = int(task['finished_size'])
                row[STATUS_COL] = int(task['status'])
                if row[SIZE_COL]:
                    row[PERCENT_COL] = int(row[FINISHED_COL] / row[SIZE_COL] * 100)
                size = util.get_human_size(row[SIZE_COL])[0]
                finished_size = util.get_human_size(row[FINISHED_COL])[0]
                if row[SIZE_COL] == row[FINISHED_COL]:
                    row[HUMANSIZE_COL] = size
                else:
                    row[HUMANSIZE_COL] = '{0}/{1}'.format(finished_size, size)

        task_ids = [row[TASKID_COL] for row in self.liststore]
        if task_ids:
            gutil.async_call(
                pcs.cloud_query_task, self.app.cookie, self.app.tokens,
                task_ids, callback=update_task_status)


    # Open API
    def add_cloud_bt_task(self, source_url):
        '''从服务器上获取种子, 并建立离线下载任务

        source_url - BT 种子在服务器上的绝对路径, 或者是磁链的地址.
        '''
        def check_vcode(info, error=None):
            if error or not info:
                print('Error in check_vcode:', info)
                return
            if 'error_code' not in info or info['error_code'] == 0:
                self.reload()
                return
            if info['error_code'] == -19:
                vcode_dialog = VCodeDialog(self, self.app, info)
                response = vcode_dialog.run()
                vcode_input = vcode_dialog.get_vcode()
                vcode_dialog.destroy()
                if response != Gtk.ResponseType.OK:
                    return
                gutil.async_call(
                    pcs.cloud_add_bt_task, self.app.cookie,
                    self.app.tokens, source_url, save_path,
                    selected_idx, file_sha1, info['vcode'], vcode_input,
                    callback=check_vcode)
            else:
                print('Unknown error info:', info)

        self.check_first()
        folder_browser = FolderBrowserDialog(
                self, self.app, _('Save to..'))
        response = folder_browser.run()
        if response != Gtk.ResponseType.OK:
            folder_browser.destroy()
            return
        save_path = folder_browser.get_path()
        folder_browser.destroy()

        bt_browser = BTBrowserDialog(
                self, self.app, _('Choose..'), source_url, save_path)
        response = bt_browser.run()
        selected_idx, file_sha1 = bt_browser.get_selected()
        bt_browser.destroy()
        if response != Gtk.ResponseType.OK or not selected_idx:
            return
        gutil.async_call(
            pcs.cloud_add_bt_task, self.app.cookie, self.app.tokens,
            source_url, save_path, selected_idx, file_sha1,
            callback=check_vcode)

    # Open API
    def add_link_task(self):
        self.check_first()
        dialog = Gtk.Dialog(
                _('Add new link task'), self.app.window,
                Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog.set_border_width(10)
        dialog.set_default_size(480, 180)
        box = dialog.get_content_area()
        entry = Gtk.Entry()
        entry.set_placeholder_text(_('Link ..'))
        box.pack_start(entry, False, False, 0)

        infobar = Gtk.InfoBar()
        infobar.set_message_type(Gtk.MessageType.INFO)
        box.pack_start(infobar, False, False, 5)
        info_content = infobar.get_content_area()
        info_label = Gtk.Label.new(
            _('Support http/https/ftp/thunder/qqdl/flashget/eMule/Magnet format'))
        info_content.pack_start(info_label, False, False, 0)

        box.show_all()
        response = dialog.run()
        source_url = entry.get_text()
        dialog.destroy()
        if response != Gtk.ResponseType.OK or not len(source_url):
            return

        if source_url.startswith('magnet'):
            self.add_cloud_bt_task(source_url)
            return

        priv_url = decoder.decode(source_url)
        if priv_url:
            print('private link:', priv_url)
            source_url = priv_url 
        else:
            print('Failed to parse private link:', source_url)
        folder_browser = FolderBrowserDialog(
                self, self.app, _('Save to..'))
        response = folder_browser.run()
        if response != Gtk.ResponseType.OK:
            folder_browser.destroy()
            return
        save_path = folder_browser.get_path()
        folder_browser.destroy()
        gutil.async_call(
            pcs.cloud_add_link_task, self.app.cookie, self.app.tokens,
            source_url, save_path, callback=self.reload)

    def on_bt_button_clicked(self, button):
        self.add_local_bt_task()

    def on_link_button_clicked(self, button):
        self.add_link_task()

    def on_reload_button_clicked(self, button):
        self.reload()

    def on_open_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths or len(tree_paths) != 1:
            return
        tree_path = tree_paths[0]
        path = model[tree_path][PATH_COL]
        dir_name = os.path.split(path)[0]
        self.app.home_page.load(dir_name)
        self.app.switch_page(self.app.home_page)

    def on_cancel_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths or len(tree_paths) != 1:
            return
        tree_path = tree_paths[0]
        task_id = model[tree_path][TASKID_COL]
        gutil.async_call(
            pcs.cloud_cancel_task, self.app.cookie, self.app.tokens,
            task_id, callback=self.reload)

    def on_remove_button_clicked(self, button):
        def on_task_removed(resp, error=None):
            print('on task removed:', resp)
            self.reload()
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths or len(tree_paths) != 1:
            print('on remove button clicked: do nothing:', tree_paths)
            return
        tree_path = tree_paths[0]
        task_id = model[tree_path][TASKID_COL]
        if model[tree_path][STATUS_COL] == Status[0]:
            gutil.async_call(
                pcs.cloud_delete_task, self.app.cookie, self.app.tokens,
                task_id, callback=on_task_removed)
        else:
            gutil.async_call(
                pcs.cloud_cancel_task, self.app.cookie, self.app.tokens,
                task_id, callback=self.reload)

    def on_clear_button_clicked(self, button):
        def on_clear_task(info, error=None):
            self.reload()

        gutil.async_call(
            pcs.cloud_clear_task, self.app.cookie, self.app.tokens,
            callback=on_clear_task)
