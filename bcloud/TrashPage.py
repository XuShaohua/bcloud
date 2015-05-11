
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import time

from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud import gutil
from bcloud.log import logger
from bcloud import pcs
from bcloud import util

(ICON_COL, NAME_COL, PATH_COL, FSID_COL, TOOLTIP_COL, SIZE_COL,
    HUMANSIZE_COL, DELETING_COL, REMAINING_COL) = list(range(9))
MAX_DAYS = 10  # 10天后会自动从回收站中删除
ICON_SIZE = 24


class TrashPage(Gtk.Box):

    icon_name = 'user-trash-symbolic'
    disname = _('Trash')
    name = 'TrashPage'
    tooltip = _('Files deleted')
    first_run = True
    page_num = 1
    has_next = False
    filelist = []

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        if Config.GTK_GE_312:
            self.headerbar = Gtk.HeaderBar()
            self.headerbar.props.show_close_button = True
            self.headerbar.props.has_subtitle = False
            self.headerbar.set_title(self.disname)

            restore_button = Gtk.Button()
            restore_img = Gtk.Image.new_from_icon_name('edit-undo-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            restore_button.set_image(restore_img)
            restore_button.set_tooltip_text(_('Restore'))
            restore_button.connect('clicked', self.on_restore_button_clicked)
            self.headerbar.pack_start(restore_button)

            # remove box
            right_box = Gtk.Box()
            right_box_context = right_box.get_style_context()
            right_box_context.add_class(Gtk.STYLE_CLASS_RAISED)
            right_box_context.add_class(Gtk.STYLE_CLASS_LINKED)
            self.headerbar.pack_end(right_box)

            delete_button = Gtk.Button()
            delete_img = Gtk.Image.new_from_icon_name('list-remove-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            delete_button.set_image(delete_img)
            delete_button.set_tooltip_text(_('Remove'))
            delete_button.set_tooltip_text(
                    _('Delete selected files in trash permanently'))
            delete_button.connect('clicked', self.on_delete_button_clicked)
            right_box.pack_start(delete_button, False, False, 0)

            clear_button = Gtk.Button()
            clear_img = Gtk.Image.new_from_icon_name('list-remove-all-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            clear_button.set_image(clear_img)
            clear_button.set_tooltip_text(_('Clear trash'))
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
            control_box = Gtk.Box(spacing=0)
            control_box.props.margin_bottom = 10
            self.pack_start(control_box, False, False, 0)

            restore_button = Gtk.Button.new_with_label(_('Restore'))
            restore_button.connect('clicked', self.on_restore_button_clicked)
            control_box.pack_start(restore_button, False, False, 0)

            reload_button = Gtk.Button.new_with_label(_('Reload (F5)'))
            reload_button.connect('clicked', self.on_reload_button_clicked)
            control_box.pack_start(reload_button, False, False, 0)

            clear_button = Gtk.Button.new_with_label(_('Clear Trash'))
            clear_button.set_tooltip_text(_('Clear trash'))
            clear_button.connect('clicked', self.on_clear_button_clicked)
            control_box.pack_end(clear_button, False, False, 0)

            delete_button = Gtk.Button.new_with_label(_('Delete'))
            delete_button.set_tooltip_text(
                    _('Delete selected files permanently'))
            delete_button.connect('clicked', self.on_delete_button_clicked)
            control_box.pack_end(delete_button, False, False, 0)

            # show loading process
            self.loading_spin = Gtk.Spinner()
            self.loading_spin.props.margin_right = 5
            control_box.pack_end(self.loading_spin, False, False, 0)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)

        # icon name, disname, path, fs_id, tooltip,
        # size, humansize, deleting time, remaining days
        self.liststore = Gtk.ListStore(str, str, str, str, str,
                                       GObject.TYPE_INT64, str, str, str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        selection = self.treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.treeview.set_rubber_banding(True)
        self.treeview.set_tooltip_column(PATH_COL)
        self.treeview.set_headers_clickable(True)
        self.treeview.set_reorderable(True)
        self.treeview.set_search_column(NAME_COL)
        scrolled_win.add(self.treeview)

        icon_cell = Gtk.CellRendererPixbuf()
        name_cell = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END,
                                         ellipsize_set=True)
        name_col = Gtk.TreeViewColumn()
        name_col.set_title(_('Name'))
        name_col.pack_start(icon_cell, False)
        name_col.pack_start(name_cell, True)
        if Config.GTK_LE_36:
            name_col.add_attribute(icon_cell, 'icon_name', ICON_COL)
            name_col.add_attribute(name_cell, 'text', NAME_COL)
        else:
            name_col.set_attributes(icon_cell, icon_name=ICON_COL)
            name_col.set_attributes(name_cell, text=NAME_COL)
        name_col.set_expand(True)
        self.treeview.append_column(name_col)
        name_col.set_sort_column_id(NAME_COL)
        self.liststore.set_sort_func(NAME_COL, gutil.tree_model_natsort)

        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(_('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)
        size_col.set_sort_column_id(SIZE_COL)

        time_cell = Gtk.CellRendererText()
        time_col = Gtk.TreeViewColumn(_('Time'), time_cell, text=DELETING_COL)
        self.treeview.append_column(time_col)
        time_col.set_sort_column_id(DELETING_COL)

        remaining_cell = Gtk.CellRendererText()
        remaining_col = Gtk.TreeViewColumn(_('Remaining'), remaining_cell,
                                           text=REMAINING_COL)
        self.treeview.append_column(remaining_col)
        remaining_col.set_sort_column_id(REMAINING_COL)

    def on_page_show(self):
        if Config.GTK_GE_312:
            self.app.window.set_titlebar(self.headerbar)
            self.headerbar.show_all()

    def check_first(self):
        if self.first_run:
            self.first_run = False
            self.load()

    def load(self):
        self.loading_spin.start()
        self.loading_spin.show_all()
        self.page_num = 1
        self.liststore.clear()
        gutil.async_call(pcs.list_trash, self.app.cookie, self.app.tokens, '/',
                         self.page_num, callback=self.append_filelist)

    def load_next(self):
        self.loading_spin.start()
        self.loading_spin.show_all()
        self.page_num = self.page_num + 1
        gutil.async_call(pcs.list_trash, self.app.cookie, self.app.tokens, '/',
                         self.page_num, callback=self.append_filelist)

    def reload(self, *args, **kwds):
        self.load()

    def append_filelist(self, info, error=None):
        self.loading_spin.stop()
        self.loading_spin.hide()
        if not info:
            self.app.toast(_('Network error'))
        elif info.get('errno', -1) != 0:
            self.app.toast(info.get('error_msg', _('Network error')))
        if error or not info or info.get('errno', -1) != 0:
            logger.error('TrashPage.append_filelist: %s, %s' % (info, error))
            return
        for pcs_file in info['list']:
            self.filelist.append(pcs_file)
            path = pcs_file['path']

            icon_name = self.app.mime.get_icon_name(path, pcs_file['isdir'])
            tooltip = gutil.escape(path)
            if pcs_file['isdir'] or 'size' not in pcs_file:
                size = 0
                humansize = ''
            else:
                size = pcs_file['size']
                humansize = util.get_human_size(size)[0]
            remaining_days = util.get_delta_days(int(pcs_file['server_mtime']),
                                                 time.time())
            remaining_days = str(MAX_DAYS - remaining_days) + ' days'
            self.liststore.append([
                icon_name,
                pcs_file['server_filename'],
                path,
                str(pcs_file['fs_id']),
                tooltip,
                size,
                humansize,
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
        gutil.async_call(pcs.restore_trash, self.app.cookie, self.app.tokens,
                         fidlist, callback=self.reload)
        self.app.blink_page(self.app.home_page)
        self.app.home_page.reload()

    def on_delete_button_clicked(self, button):
        selection = self.treeview.get_selection()
        model, tree_paths = selection.get_selected_rows()
        if not tree_paths:
            return
        fidlist = []
        for tree_path in tree_paths:
            fidlist.append(model[tree_path][FSID_COL])
        gutil.async_call(pcs.delete_trash, self.app.cookie, self.app.tokens,
                         fidlist, callback=self.reload)

    def on_clear_button_clicked(self, button):
        gutil.async_call(pcs.clear_trash, self.app.cookie, self.app.tokens,
                         callback=self.reload)

    def on_reload_button_clicked(self, button):
        self.load()
