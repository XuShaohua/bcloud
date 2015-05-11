
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud import gutil
from bcloud.log import logger
from bcloud import pcs
from bcloud import util

CHECK_COL, NAME_COL, SIZE_COL, HUMANSIZE_COL = list(range(4))
MIN_SIZE_TO_CHECK = 2 ** 20  # 1M
CHECK_EXT = ('jpg', 'png', 'gif', 'bitttorrent')

class BTBrowserDialog(Gtk.Dialog):

    file_sha1 = ''

    def __init__(self, parent, app, title, source_url, save_path):
        '''初始化BT种子查询对话框.

        source_url - 如果是BT种子的话, 就是种子的绝对路径.
                      如果是磁链的话, 就是以magent:开头的磁链链接.
        '''
        super().__init__(title, app.window, Gtk.DialogFlags.MODAL,
                         (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_OK, Gtk.ResponseType.OK))

        self.app = app
        self.source_url = source_url
        self.save_path = save_path

        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(520, 480)
        self.set_border_width(10)
        box = self.get_content_area()

        select_all_button = Gtk.ToggleButton.new_with_label(_('Select All'))
        select_all_button.props.halign = Gtk.Align.START
        select_all_button.props.margin_bottom = 5
        select_all_button.connect('toggled', self.on_select_all_toggled)
        box.pack_start(select_all_button, False, False, 0)

        scrolled_win = Gtk.ScrolledWindow()
        box.pack_start(scrolled_win, True, True, 0)

        # check, name, size, humansize
        self.liststore = Gtk.ListStore(bool, str, GObject.TYPE_INT64, str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_tooltip_column(NAME_COL)
        scrolled_win.add(self.treeview)
        check_cell = Gtk.CellRendererToggle()
        check_cell.connect('toggled', self.on_check_cell_toggled)
        check_col = Gtk.TreeViewColumn('', check_cell, active=CHECK_COL)
        self.treeview.append_column(check_col)
        name_cell = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END,
                                         ellipsize_set=True)
        name_col = Gtk.TreeViewColumn(_('Name'), name_cell, text=NAME_COL)
        name_col.set_expand(True)
        self.treeview.append_column(name_col)
        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(_('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)

        box.show_all()
        self.request_data()

    def request_data(self):
        '''在调用dialog.run()之前先调用这个函数来获取数据'''
        def on_tasks_received(info, error=None):
            if error or not info:
                logger.error('BTBrowserDialog.on_tasks_received: %s, %s.' %
                             (info, error))
                return
            if 'magnet_info' in info:
                tasks = info['magnet_info']
            elif 'torrent_info' in info:
                tasks = info['torrent_info']['file_info']
                self.file_sha1 = info['torrent_info']['sha1']
            elif 'error_code' in info:
                logger.error('BTBrowserDialog.on_tasks_received: %s, %s.' %
                             (info, error))
                self.app.toast(info.get('error_msg', ''))
                return
            else:
                logger.error('BTBrowserDialog.on_tasks_received: %s, %s.' %
                             (info, error))
                self.app.toast(_('Unknown error occured: %s') % info)
                return
            for task in tasks:
                size = int(task['size'])
                human_size = util.get_human_size(size)[0]
                select = (size > MIN_SIZE_TO_CHECK or 
                          task['file_name'].endswith(CHECK_EXT))
                self.liststore.append([
                    select,
                    task['file_name'],
                    size,
                    human_size,
                ])

        if self.source_url.startswith('magnet'):
            gutil.async_call(pcs.cloud_query_magnetinfo, self.app.cookie,
                             self.app.tokens, self.source_url, self.save_path,
                             callback=on_tasks_received)
        else:
            gutil.async_call(pcs.cloud_query_sinfo, self.app.cookie,
                             self.app.tokens, self.source_url,
                             callback=on_tasks_received)

    def get_selected(self):
        '''返回选中要下载的文件的编号及sha1值, 从1开始计数.'''
        selected_idx = []
        for i, row in enumerate(self.liststore):
            if row[CHECK_COL]:
                selected_idx.append(i + 1)
        return (selected_idx, self.file_sha1)

    def on_select_all_toggled(self, button):
        status = button.get_active()
        for row in self.liststore:
            row[CHECK_COL] = status

    def on_check_cell_toggled(self, cell, tree_path):
        self.liststore[tree_path][CHECK_COL] = not \
                self.liststore[tree_path][CHECK_COL]
