
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
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
from bcloud.log import logger
from bcloud import pcs
from bcloud import util


(TASKID_COL, NAME_COL, PATH_COL, SOURCEURL_COL, SIZE_COL, FINISHED_COL,
    STATUS_COL, PERCENT_COL, HUMANSIZE_COL, TOOLTIP_COL) = list(range(10))

Status = (0, 1, )
StatusNames = (_('FINISHED'), _('DOWNLOADING'), )


class CloudPage(Gtk.Box):

    icon_name = 'cloud-symbolic'
    disname = _('Cloud')
    name = 'CloudPage'
    tooltip = _('Cloud download')
    first_run = True

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        if Config.GTK_GE_312:
            self.headerbar = Gtk.HeaderBar()
            self.headerbar.props.show_close_button = True
            self.headerbar.props.has_subtitle = False
            self.headerbar.set_title(self.disname)

            # link button
            link_button = Gtk.Button()
            link_img = Gtk.Image.new_from_icon_name('document-new-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            link_button.set_image(link_img)
            link_button.set_tooltip_text(_('Create new cloud task'))
            link_button.connect('clicked', self.on_link_button_clicked)
            self.headerbar.pack_start(link_button)

            # open button
            open_button = Gtk.Button()
            open_img = Gtk.Image.new_from_icon_name('document-open-symbolic',
                Gtk.IconSize.SMALL_TOOLBAR)
            open_button.set_image(open_img)
            open_button.set_tooltip_text(_('Open target directory'))
            open_button.connect('clicked', self.on_open_button_clicked)
            self.headerbar.pack_start(open_button)

            # remove box
            right_box = Gtk.Box()
            right_box_context = right_box.get_style_context()
            right_box_context.add_class(Gtk.STYLE_CLASS_RAISED)
            right_box_context.add_class(Gtk.STYLE_CLASS_LINKED)
            self.headerbar.pack_end(right_box)

            remove_button = Gtk.Button()
            delete_img = Gtk.Image.new_from_icon_name('list-remove-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            remove_button.set_image(delete_img)
            remove_button.set_tooltip_text(_('Remove selected tasks'))
            remove_button.connect('clicked', self.on_remove_button_clicked)
            right_box.pack_start(remove_button, False, False, 0)

            clear_button = Gtk.Button()
            clear_img = Gtk.Image.new_from_icon_name('list-remove-all-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            clear_button.set_image(clear_img)
            clear_button.set_tooltip_text(_('Remove completed cloud tasks'))
            clear_button.connect('clicked', self.on_clear_button_clicked)
            right_box.pack_start(clear_button, False, False, 0)

            reload_button = Gtk.Button()
            reload_img = Gtk.Image.new_from_icon_name('view-refresh-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            reload_button.set_image(reload_img)
            reload_button.set_tooltip_text(_('Reload (F5)'))
            reload_button.connect('clicked', self.on_reload_button_clicked)
            self.headerbar.pack_end(reload_button)

            # show loading process
            self.loading_spin = Gtk.Spinner()
            self.headerbar.pack_end(self.loading_spin)
        else:
            control_box = Gtk.Box()
            self.pack_start(control_box, False, False, 0)

            link_button = Gtk.Button.new_with_label(_('New Link Task'))
            link_button.connect('clicked', self.on_link_button_clicked)
            control_box.pack_start(link_button, False, False, 0)

            reload_button = Gtk.Button.new_with_label(_('Reload (F5)'))
            reload_button.props.margin_left = 40
            reload_button.connect('clicked', self.on_reload_button_clicked)
            control_box.pack_start(reload_button, False, False, 0)

            open_button = Gtk.Button.new_with_label(_('Open Directory'))
            open_button.connect('clicked', self.on_open_button_clicked)
            control_box.pack_start(open_button, False, False, 0)

            clear_button = Gtk.Button.new_with_label(_('Clear'))
            clear_button.set_tooltip_text(_('Remove completed cloud tasks'))
            clear_button.connect('clicked', self.on_clear_button_clicked)
            control_box.pack_end(clear_button, False, False, 0)

            remove_button = Gtk.Button.new_with_label(_('Remove'))
            remove_button.set_tooltip_text(_('Remove'))
            remove_button.connect('clicked', self.on_remove_button_clicked)
            control_box.pack_end(remove_button, False, False, 0)

            # show loading process
            self.loading_spin = Gtk.Spinner()
            self.loading_spin.props.margin_right = 5
            control_box.pack_end(self.loading_spin, False, False, 0)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)

        # task_id, name, path, source_url, size, finished_size,
        # status, percent, human_size, tooltip
        self.liststore = Gtk.ListStore(str, str, str, str, GObject.TYPE_INT64,
                                       GObject.TYPE_INT64, int, int, str, str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_headers_clickable(True)
        self.treeview.set_reorderable(True)
        self.treeview.set_search_column(NAME_COL)
        self.treeview.set_tooltip_column(TOOLTIP_COL)
        self.selection = self.treeview.get_selection()
        scrolled_win.add(self.treeview)

        name_cell = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END,
                                         ellipsize_set=True)
        name_col = Gtk.TreeViewColumn(_('Name'), name_cell, text=NAME_COL)
        name_col.set_expand(True)
        self.treeview.append_column(name_col)
        name_col.set_sort_column_id(NAME_COL)
        self.liststore.set_sort_func(NAME_COL, gutil.tree_model_natsort)

        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(_('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)
        size_col.props.min_width = 145
        size_col.set_sort_column_id(SIZE_COL)

        percent_cell = Gtk.CellRendererProgress()
        percent_col = Gtk.TreeViewColumn(_('Progress'), percent_cell,
                                         value=PERCENT_COL)
        self.treeview.append_column(percent_col)
        percent_col.props.min_width = 145
        percent_col.set_sort_column_id(PERCENT_COL)

    def on_page_show(self):
        if Config.GTK_GE_312:
            self.app.window.set_titlebar(self.headerbar)
            self.headerbar.show_all()

    def check_first(self):
        if self.first_run:
            self.first_run = False
            self.load()

    def load(self):
        '''获取当前的离线任务列表'''
        def on_list_task(info, error=None):
            self.loading_spin.stop()
            self.loading_spin.hide()
            if not info:
                self.app.toast(_('Network error, info is empty'))
            if error or not info:
                logger.error('CloudPage.load: %s, %s' % (info, error))
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
                    gutil.escape(task['save_path'])
                ])
            self.scan_tasks()

            nonlocal start
            start = start + len(tasks)
            if info['total'] > start:
                gutil.async_call(pcs.cloud_list_task, self.app.cookie,
                                 self.app.tokens, start, callback=on_list_task)

        self.loading_spin.start()
        self.loading_spin.show_all()
        start = 0
        gutil.async_call(pcs.cloud_list_task, self.app.cookie, self.app.tokens,
                         start, callback=on_list_task)

    def reload(self, *args, **kwds):
        self.liststore.clear()
        self.load()

    def get_row_by_task_id(self, task_id):
        '''返回这个任务的TreeModelRow, 如果不存在, 就返回None.'''
        for row in self.liststore:
            if row and row[TASKID_COL] == task_id:
                return row
        return None

    def scan_tasks(self):
        '''定期获取离线下载任务的信息, 比如10秒钟'''
        def update_task_status(info, error=None):
            if error or not info:
                logger.error('CloudPage.scan_tasks: %s, %s' % (info, error))
                return
            tasks = info['task_info']
            for row in self.liststore:
                if not row or row[TASKID_COL] not in tasks:
                    continue
                task = tasks[row[TASKID_COL]]
                row[SIZE_COL] = int(task['file_size'])
                row[FINISHED_COL] = int(task['finished_size'])
                row[STATUS_COL] = int(task['status'])
                if row[SIZE_COL]:
                    row[PERCENT_COL] = int(
                            row[FINISHED_COL] / row[SIZE_COL] * 100)
                size = util.get_human_size(row[SIZE_COL])[0]
                finished_size = util.get_human_size(row[FINISHED_COL])[0]
                if row[SIZE_COL] == row[FINISHED_COL]:
                    row[HUMANSIZE_COL] = size
                else:
                    row[HUMANSIZE_COL] = '{0}/{1}'.format(finished_size, size)

        task_ids = [row[TASKID_COL] for row in self.liststore]
        if task_ids:
            gutil.async_call(pcs.cloud_query_task, self.app.cookie,
                             self.app.tokens, task_ids,
                             callback=update_task_status)


    # Open API
    def add_cloud_bt_task(self, source_url, save_path=None):
        '''从服务器上获取种子, 并建立离线下载任务

        source_url - BT 种子在服务器上的绝对路径, 或者是磁链的地址.
        save_path  - 要保存到的路径, 如果为None, 就会弹出目录选择的对话框
        '''
        def check_vcode(info, error=None):
            if error or not info:
                logger.error('CloudPage.check_vcode: %s, %s' % (info, error))
                return
            if info.get('error_code', -1) != 0:
                logger.error('CloudPage.check_vcode: %s, %s' % (info, error))

            if 'task_id' in info or info['error_code'] == 0:
                self.reload()
            elif info['error_code'] == -19:
                vcode_dialog = VCodeDialog(self, self.app, info)
                response = vcode_dialog.run()
                vcode_input = vcode_dialog.get_vcode()
                vcode_dialog.destroy()
                if response != Gtk.ResponseType.OK:
                    return
                gutil.async_call(pcs.cloud_add_bt_task, self.app.cookie,
                                 self.app.tokens, source_url, save_path,
                                 selected_idx, file_sha1, info['vcode'],
                                 vcode_input, callback=check_vcode)
            else:
                self.app.toast(_('Error: {0}').format(info['error_msg']))

        self.check_first()

        if not save_path:
            folder_browser = FolderBrowserDialog(self, self.app, _('Save to..'))
            response = folder_browser.run()
            save_path = folder_browser.get_path()
            folder_browser.destroy()
            if response != Gtk.ResponseType.OK:
                return
        if not save_path:
            return

        bt_browser = BTBrowserDialog(self, self.app, _('Choose..'),
                                     source_url, save_path)
        response = bt_browser.run()
        selected_idx, file_sha1 = bt_browser.get_selected()
        bt_browser.destroy()
        if response != Gtk.ResponseType.OK or not selected_idx:
            return
        gutil.async_call(pcs.cloud_add_bt_task, self.app.cookie,
                         self.app.tokens, source_url, save_path, selected_idx,
                         file_sha1, callback=check_vcode)
        self.app.blink_page(self.app.cloud_page)

    # Open API
    def add_link_task(self):
        '''新建普通的链接任务'''
        def do_add_link_task(source_url):
            def on_link_task_added(info, error=None):
                if error or not info:
                    logger.error('CloudPage.do_add_link_task: %s, %s' %
                                 (info, error))
                    self.app.toast(_('Failed to parse download link'))
                    return
                if info.get('error_code', -1) != 0:
                    logger.error('CloudPage.do_add_link_task: %s, %s' %
                                 (info, error))

                if 'task_id' in info or info['error_code'] == 0:
                    self.reload()
                elif info['error_code'] == -19:
                    vcode = info['vcode']
                    vcode_dialog = VCodeDialog(self, self.app, info)
                    response = vcode_dialog.run()
                    vcode_input = vcode_dialog.get_vcode()
                    vcode_dialog.destroy()
                    if response != Gtk.ResponseType.OK:
                        return
                    gutil.async_call(pcs.cloud_add_link_task, self.app.cookie,
                                     self.app.tokens, source_url, save_path,
                                     vcode, vcode_input,
                                     callback=on_link_task_added)
                else:
                    self.app.toast(_('Error: {0}').format(info['error_msg']))
            gutil.async_call(pcs.cloud_add_link_task, self.app.cookie,
                             self.app.tokens, source_url, save_path,
                             callback=on_link_task_added)

        self.check_first()
        dialog = Gtk.Dialog(_('Add new link tasks'), self.app.window,
                            Gtk.DialogFlags.MODAL,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                            Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog.set_border_width(10)
        dialog.set_default_size(480, 300)
        dialog.set_default_response(Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        scrolled_win = Gtk.ScrolledWindow()
        box.pack_start(scrolled_win, True, True, 0)
        links_buf = Gtk.TextBuffer()
        links_tv = Gtk.TextView.new_with_buffer(links_buf)
        links_tv.set_tooltip_text(_('Paste links here, line by line'))
        scrolled_win.add(links_tv)

        infobar = Gtk.InfoBar()
        infobar.set_message_type(Gtk.MessageType.INFO)
        box.pack_start(infobar, False, False, 5)
        info_content = infobar.get_content_area()
        info_label = Gtk.Label.new(
            _('Support http/https/ftp/thunder/qqdl/flashget/eMule/Magnet format'))
        info_content.pack_start(info_label, False, False, 0)

        box.show_all()
        response = dialog.run()
        contents = gutil.text_buffer_get_all_text(links_buf)
        dialog.destroy()
        if response != Gtk.ResponseType.OK or not contents:
            return
        link_tasks = []
        bt_tasks = []
        for source_url in contents.split('\n'):
            source_url = source_url.strip()
            if not source_url:
                continue
            if source_url.startswith('magnet'):
                bt_tasks.append(source_url)
            else:
                priv_url = decoder.decode(source_url)
                if priv_url:
                    link_tasks.append(priv_url)
                else:
                    link_tasks.append(source_url)

        folder_browser = FolderBrowserDialog(self, self.app, _('Save to..'))
        response = folder_browser.run()
        save_path = folder_browser.get_path()
        folder_browser.destroy()
        if response != Gtk.ResponseType.OK or not save_path:
            return
        for source_url in link_tasks:
            do_add_link_task(source_url)
        for source_url in bt_tasks:
            self.add_cloud_bt_task(source_url, save_path)


    def on_bt_button_clicked(self, button):
        self.add_local_bt_task()

    def on_link_button_clicked(self, button):
        self.add_link_task()

    def on_reload_button_clicked(self, button):
        self.reload()

    def on_open_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        # tree_paths might be None or a list
        if not tree_paths or len(tree_paths) != 1:
            return
        tree_path = tree_paths[0]
        path = model[tree_path][PATH_COL]
        dir_name = os.path.split(path)[0]
        self.app.home_page.load(dir_name)
        self.app.switch_page(self.app.home_page)

    def on_remove_button_clicked(self, button):
        def on_task_removed(resp, error=None):
            self.reload()
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths or len(tree_paths) != 1:
            return
        tree_path = tree_paths[0]
        task_id = model[tree_path][TASKID_COL]
        self.loading_spin.start()
        self.loading_spin.show_all()
        if model[tree_path][STATUS_COL] == Status[0]:
            gutil.async_call(pcs.cloud_delete_task, self.app.cookie,
                             self.app.tokens, task_id, callback=on_task_removed)
        else:
            gutil.async_call(pcs.cloud_cancel_task, self.app.cookie,
                             self.app.tokens, task_id, callback=self.reload)

    def on_clear_button_clicked(self, button):
        def on_clear_task(info, error=None):
            self.reload()

        gutil.async_call(pcs.cloud_clear_task, self.app.cookie,
                         self.app.tokens, callback=on_clear_task)
