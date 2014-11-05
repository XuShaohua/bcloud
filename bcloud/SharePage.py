# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os
import time

from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud.FolderBrowserDialog import FolderBrowserDialog
from bcloud import gutil
from bcloud.log import logger
from bcloud import pcs
from bcloud import util

#(CHECK_COL, ICON_COL, NAME_COL, PATH_COL, SIZE_COL, HUMANSIZE_COL,
    #MTIME_COL, HUMAN_MTIME_COL) = list(range(8))
(CHECK_COL, NAME_COL, PATH_COL, SIZE_COL, HUMANSIZE_COL,
    MTIME_COL, HUMAN_MTIME_COL) = list(range(7))

REFRESH_ICON = 'view-refresh-symbolic'
ABORT_ICON = 'edit-delete-symbolic'
GO_ICON = 'go-next-symbolic'


class SharePage(Gtk.Box):

    icon_name = 'emblem-shared-symbolic'
    disname = _('Share')
    name = 'SharePage'
    tooltip = _('Shared files')
    first_run = True

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        self.curr_url = ''
        self.uk = ''
        self.shareid = ''
        self.filelist = []

        if Config.GTK_GE_312:
            self.headerbar = Gtk.HeaderBar()
            self.headerbar.props.show_close_button = True
            self.headerbar.props.has_subtitle = False

            headerbar_box = Gtk.Box()
            self.headerbar.set_custom_title(headerbar_box)

            cloud_button = Gtk.Button()
            cloud_button.props.tooltip_text = \
                    _('Transfer selected files to my account')
            cloud_image = Gtk.Image.new_from_icon_name('cloud-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            cloud_button.set_image(cloud_image)
            headerbar_box.pack_start(cloud_button, False, False, 5)

            self.url_entry = Gtk.Entry()
            self.url_entry.set_placeholder_text(_('URL of shared files...'))
            self.url_entry.props.width_chars = 80
            self.url_entry.props.secondary_icon_name = GO_ICON
            self.url_entry.connect('activate', self.on_url_entry_activated)
            self.url_entry.connect('changed', self.on_url_entry_changed)
            self.url_entry.connect('icon-press', self.on_url_entry_icon_pressed)
            headerbar_box.pack_start(self.url_entry, True, True, 0)

            # show loading process
            self.loading_spin = Gtk.Spinner()
            self.headerbar.pack_end(self.loading_spin)
        else:
            control_box = Gtk.Box()
            self.pack_start(control_box, False, False, 0)

            reload_button = Gtk.Button.new_with_label(_('Reload'))
            reload_button.props.margin_left = 40
            #reload_button.connect('clicked', self.on_reload_button_clicked)
            control_box.pack_start(reload_button, False, False, 0)

            # show loading process
            self.loading_spin = Gtk.Spinner()
            self.loading_spin.props.margin_right = 5
            control_box.pack_end(self.loading_spin, False, False, 0)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)

        # checked, icon, name, path, size, human-size, mtime, human-mtime
        #self.liststore = Gtk.ListStore(bool, GdkPixbuf.Pixbuf, str, str,
        self.liststore = Gtk.ListStore(bool, str, str,
                                       GObject.TYPE_INT64, str,
                                       GObject.TYPE_INT64, str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_headers_clickable(True)
        self.treeview.set_reorderable(True)
        self.treeview.set_search_column(NAME_COL)
        self.treeview.set_tooltip_column(PATH_COL)
        self.selection = self.treeview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        scrolled_win.add(self.treeview)

        checked_cell = Gtk.CellRendererToggle()
        checked_cell.connect('toggled', self.on_row_checked)
        checked_col = Gtk.TreeViewColumn()
        checked_col.props.clickable = True
        checked_col.pack_start(checked_cell, False)
        checked_col.add_attribute(checked_cell, 'active', CHECK_COL)
        self.treeview.append_column(checked_col)
        self.select_all_button = Gtk.CheckButton()
        checked_col.set_widget(self.select_all_button)
        checked_col.connect('clicked', self.on_select_all_button_toggled)

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

        mtime_cell = Gtk.CellRendererText()
        mtime_col = Gtk.TreeViewColumn(_('Modified'), mtime_cell,
                                       text=HUMAN_MTIME_COL)
        self.treeview.append_column(mtime_col)
        mtime_col.props.min_width = 100
        mtime_col.set_resizable(True)
        mtime_col.set_sort_column_id(MTIME_COL)

    def on_page_show(self):
        if Config.GTK_GE_312:
            self.app.window.set_titlebar(self.headerbar)
            self.headerbar.show_all()

    def check_first(self):
        if self.first_run:
            self.first_run = False
            self.load()

    def load(self):
        self.select_all_button.show_all()

    def reload(self, *args, **kwds):
        self.liststore.clear()
        self.load_url()

    def load_url(self):
        '''读取分享文件列表'''
        def on_load_url(info, error=None):
            print(info, error)
            self.url_entry.props.secondary_icon_name = REFRESH_ICON
            if timestamp != self.url_entry.timestamp:
                print('timestamp not match, ignored')
                return
            if error or not info:
                logger.warn('SharePage.load_url: %s, %s, %s' %
                            (self.curr_url, info, error))
                return
            else:
                self.uk, self.shareid, self.filelist = info
                state = self.select_all_button.get_active()
                for file_ in self.filelist:
                    size = int(file_.get('size', 0))
                    human_size = util.get_human_size(size)[0]
                    mtime = int(file_.get('server_mtime', 0))
                    human_mtime = time.ctime(mtime)
                    self.liststore.append([
                        state,
                        file_['server_filename'],
                        file_['path'],
                        size,
                        human_size,
                        mtime,
                        human_mtime,
                    ])
                # TODO: display thumbnails of files

        self.url_entry.props.secondary_icon_name = ABORT_ICON
        timestamp = time.time()
        self.url_entry.timestamp = timestamp
        self.curr_url = self.url_entry.get_text()
        gutil.async_call(pcs.get_others_share_page, self.curr_url,
                         self.app.cookie, callback=on_load_url)
        self.liststore.clear()

    def on_url_entry_activated(self, entry):
        self.load_url()

    def on_url_entry_changed(self, entry):
        entry.props.secondary_icon_name = GO_ICON

    def on_url_entry_icon_pressed(self, entry, icon_pos, event):
        if entry.props.secondary_icon_name == GO_ICON:
            self.load_url()
        elif entry.props.secondary_icon_name == REFRESH_ICON:
            entry.set_text(self.curr_url)
            self.load_url()
        else:
            pass

    def on_select_all_button_toggled(self, column):
        state = self.select_all_button.get_active()
        self.select_all_button.set_active(not state)
        for row in self.liststore:
            row[CHECK_COL] = not state

    def on_row_checked(self, cell_renderer, path):
        self.liststore[path][CHECK_COL] = not self.liststore[path][CHECK_COL]
