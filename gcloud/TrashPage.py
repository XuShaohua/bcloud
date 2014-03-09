
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import time

from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gtk

from gcloud import Config
_ = Config._
from gcloud import gutil
from gcloud import pcs
from gcloud import util

(ICON_COL, DISNAME_COL, PATH_COL, FSID_COL, TOOLTIP_COL,
    SIZE_COL, DELETING_COL, REMAINING_COL) = list(range(8))
MAX_DAYS = 10  # 10天后会自动从回收站中删除
ICON_SIZE = 24

class TrashPage(Gtk.Box):

    icon_name = 'user-trash-symbolic'
    disname = _('Trash')
    tooltip = _('Files deleted.')
    first_run = True
    page_num = 0
    has_next = False
    filelist = []

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        control_box = Gtk.Box(spacing=0)
        control_box.props.margin_bottom = 10
        self.pack_start(control_box, False, False, 0)

        restore_button = Gtk.Button(_('Restore'))
        restore_button.connect('clicked', self.on_restore_button_clicked)
        control_box.pack_start(restore_button, False, False, 0)

        delete_button = Gtk.Button(_('Delete'))
        delete_button.set_tooltip_text(_('Delete selected files permanently'))
        delete_button.connect('clicked', self.on_delete_button_clicked)
        control_box.pack_start(delete_button, False, False, 0)

        clear_button = Gtk.Button(_('Clear Trash'))
        clear_button.set_tooltip_text(_('Will delete all files in trash'))
        clear_button.connect('clicked', self.on_clear_button_clicked)
        control_box.pack_end(clear_button, False, False, 0)

        reload_button = Gtk.Button(_('Reload'))
        control_box.pack_end(reload_button, False, False, 20)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)

        # icon name, disname, path, fs_id, tooltip,
        # size, deleting time, remaining days
        self.liststore = Gtk.ListStore(
                str, str, str, GObject.TYPE_ULONG, str,
                str, str, str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        selection = self.treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.treeview.set_rubber_banding(True)
        scrolled_win.add(self.treeview)

        icon_cell = Gtk.CellRendererPixbuf()
        name_cell = Gtk.CellRendererText()
        name_col = Gtk.TreeViewColumn()
        name_col.set_title(_('File Name'))
        name_col.pack_start(icon_cell, False)
        name_col.pack_start(name_cell, True)
        name_col.set_attributes(icon_cell, icon_name=ICON_COL)
        name_col.set_attributes(name_cell, text=DISNAME_COL)
        name_col.set_expand(True)
        self.treeview.append_column(name_col)
        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(_('Size'), size_cell, text=SIZE_COL)
        self.treeview.append_column(size_col)
        time_cell = Gtk.CellRendererText()
        time_col = Gtk.TreeViewColumn(
                _('Time'), time_cell, text=DELETING_COL)
        self.treeview.append_column(time_col)
        remaining_cell = Gtk.CellRendererText()
        remaining_col = Gtk.TreeViewColumn(
                _('Remaining'), remaining_cell, text=REMAINING_COL)
        self.treeview.append_column(remaining_col)
        self.treeview.set_tooltip_column(TOOLTIP_COL)

    def load(self):
        self.page_num = 1
        self.liststore.clear()
        gutil.async_call(
                pcs.list_trash, self.app.cookie, self.app.tokens, '/',
                self.page_num, callback=self.append_filelist)

    def load_next(self):
        self.page_num = self.page_num + 1
        gutil.async_call(
                pcs.list_trash, self.app.cookie, self.app.tokens, '/',
                self.page_num, callback=self.append_filelist)

    def reload(self, *args, **kwds):
        self.load()

    def append_filelist(self, infos, error=None):
        if error or not infos or infos['errno'] != 0:
            return
        for pcs_file in infos['list']:
            self.filelist.append(pcs_file)
            path = pcs_file['path']

            icon_name = self.app.mime.get_icon_name(path, pcs_file['isdir'])
            tooltip = path
            if pcs_file['isdir']:
                size = ''
            else:
                size, _ = util.get_human_size(pcs_file['size'])
            remaining_days = util.get_delta_days(
                    int(pcs_file['server_mtime']), time.time())
            remaining_days = str(MAX_DAYS - remaining_days) + ' days'
            self.liststore.append([
                icon_name,
                pcs_file['server_filename'],
                path,
                pcs_file['fs_id'],
                tooltip,
                size,
                time.ctime(pcs_file['server_mtime']),
                remaining_days,
                ])

    def on_restore_button_clicked(self, button):
        selection = self.treeview.get_selection()
        model, tree_paths = selection.get_selected_rows()
        if not tree_paths:
            return
        fidlist = []
        for tree_path in tree_paths:
            fidlist.append(model[tree_path][FSID_COL])
        gutil.async_call(
                pcs.restore_trash, self.app.cookie, self.app.tokens,
                fidlist, callback=self.reload)

    def on_delete_button_clicked(self, button):
        selection = self.treeview.get_selection()
        model, tree_paths = selection.get_selected_rows()
        if not tree_paths:
            return
        fidlist = []
        for tree_path in tree_paths:
            fidlist.append(model[tree_path][FSID_COL])
        gutil.async_call(
                pcs.delete_trash, self.app.cookie, self.app.tokens,
                fidlist, callback=self.reload)

    def on_clear_button_clicked(self, button):
        gutil.async_call(
                pcs.clear_trash, self.app.cookie, self.app.tokens,
                callback=self.reload)
