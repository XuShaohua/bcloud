
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
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
from bcloud import ErrorMsg
from bcloud.FolderBrowserDialog import FolderBrowserDialog
from bcloud import gutil
from bcloud.log import logger
from bcloud import pcs
from bcloud import util

(CHECK_COL, ICON_COL, LARGE_ICON_COL, NAME_COL, PATH_COL, ISDIR_COL, SIZE_COL,
    HUMANSIZE_COL, MTIME_COL, HUMAN_MTIME_COL) = list(range(10))
REFRESH_ICON = 'view-refresh-symbolic'
ABORT_ICON = 'edit-delete-symbolic'
GO_ICON = 'go-next-symbolic'
ICON_SIZE = 24         # 60x37
LARGE_ICON_SIZE = 100  # 100x62


class PwdDialog(Gtk.Dialog):
    '''输入密码的对话框'''

    def __init__(self, app):
        super().__init__(_('Password:'), app.window, Gtk.DialogFlags.MODAL,
                         (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_OK, Gtk.ResponseType.OK))

        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(320, 100)
        self.set_border_width(10)
        box = self.get_content_area()

        self.entry = Gtk.Entry()
        self.entry.props.placeholder_text = _('Password ...')
        box.pack_start(self.entry, False, False, 0)

        box.show_all()

    def get_pwd(self):
        return self.entry.get_text()


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
        self.page = 1  # 从1开始计数
        self.has_next = False
        self.dirname = ''

        if Config.GTK_GE_312:
            self.headerbar = Gtk.HeaderBar()
            self.headerbar.props.show_close_button = True
            self.headerbar.props.has_subtitle = False

            headerbar_box = Gtk.Box()
            self.headerbar.set_custom_title(headerbar_box)

            cloud_button = Gtk.Button()
            cloud_button.props.tooltip_text = \
                    _('Copy selected files to my account')
            cloud_image = Gtk.Image.new_from_icon_name('cloud-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            cloud_button.set_image(cloud_image)
            cloud_button.connect('clicked', self.on_cloud_button_clicked)
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

            cloud_button = Gtk.Button()
            cloud_button.props.tooltip_text = \
                    _('Copy selected files to my account')
            cloud_image = Gtk.Image.new_from_icon_name('cloud-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            cloud_button.set_image(cloud_image)
            cloud_button.connect('clicked', self.on_cloud_button_clicked)
            control_box.pack_start(cloud_button, False, False, 5)

            self.url_entry = Gtk.Entry()
            self.url_entry.set_placeholder_text(_('URL of shared files...'))
            self.url_entry.props.width_chars = 80
            self.url_entry.props.secondary_icon_name = GO_ICON
            self.url_entry.connect('activate', self.on_url_entry_activated)
            self.url_entry.connect('changed', self.on_url_entry_changed)
            self.url_entry.connect('icon-press', self.on_url_entry_icon_pressed)
            control_box.pack_start(self.url_entry, True, True, 0)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)

        # checked, icon, large_icon, name, path, isdir, size, human-size,
        # mtime, human-mtime
        self.liststore = Gtk.ListStore(bool, GdkPixbuf.Pixbuf,
                                       GdkPixbuf.Pixbuf, str, str, bool,
                                       GObject.TYPE_INT64, str,
                                       GObject.TYPE_INT64, str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_headers_clickable(True)
        self.treeview.set_search_column(NAME_COL)
        self.treeview.props.has_tooltip = True
        self.treeview.connect('query-tooltip', self.on_treeview_query_tooltip)
        self.treeview.connect('row-activated', self.on_treeview_row_activated)
        self.treeview.get_vadjustment().connect('value-changed',
                                                self.on_treeview_scrolled)
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

        icon_cell = Gtk.CellRendererPixbuf()
        name_cell = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END,
                                         ellipsize_set=True)
        name_col = Gtk.TreeViewColumn()
        name_col.set_title(_('Name'))
        name_col.pack_start(icon_cell, False)
        name_col.pack_start(name_cell, True)
        name_col.add_attribute(icon_cell, 'pixbuf', ICON_COL)
        name_col.add_attribute(name_cell, 'text', NAME_COL)
        name_col.set_expand(True)
        name_col.set_resizable(True)
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
            self.select_all_button.show_all()
            self.load()

    def load(self):
        pass

    def reload(self, *args, **kwds):
        def on_verify_password(pwd_cookie, error=None):
            if error or not pwd_cookie:
                self.app.toast(_('Error: password error, please try again'))
                logger.error('SharePage.verify_password: %s, %s' %
                             (pwd_cookie, error))
            else:
                self.app.cookie.load_list(pwd_cookie)
                self.load_url()

        def on_get_share_uk(info, error=None):
            if error or not info or not info[1]:
                logger.error('SharePage.reload: %s, %s' % (error, info))
                self.app.toast(_('Invalid link: {0}!'.format(self.curr_url)))
                self.has_next = False
                self.url_entry.props.secondary_icon_name = REFRESH_ICON
                return
            else:
                need_pwd, self.uk, self.shareid = info
                # 输入密码:
                if need_pwd:
                    pwd_dialog = PwdDialog(self.app)
                    response = pwd_dialog.run()
                    if response == Gtk.ResponseType.OK:
                        pwd = pwd_dialog.get_pwd()
                    else:
                        return
                    pwd_dialog.destroy()
                    gutil.async_call(pcs.verify_share_password, self.uk,
                                     self.shareid, pwd,
                                     callback=on_verify_password)
                else:
                    self.load_url()

        self.liststore.clear()
        self.url_entry.props.secondary_icon_name = ABORT_ICON
        self.page = 0
        self.has_next = True
        self.curr_url = self.url_entry.get_text()
        self.dirname = pcs.get_share_dirname(self.curr_url)
        gutil.async_call(pcs.get_share_uk_and_shareid, self.app.cookie,
                         self.curr_url, callback=on_get_share_uk)

    def load_next(self):
        '''载入下一页'''
        self.page += 1
        self.load_url()

    def load_url(self):
        '''读取分享文件列表'''
        def on_load_url(filelist, error=None):
            self.url_entry.props.secondary_icon_name = REFRESH_ICON
            if timestamp != self.url_entry.timestamp:
                logger.debug('SharePage.load_url, dirname not match, ignored')
                return
            if error or not filelist:
                self.app.toast(
                        _('Failed to get files, please reload this page'))
                logger.warn('SharePage.load_url: %s, %s, %s' %
                            (self.curr_url, filelist, error))
                self.has_next = False
                return
            state = self.select_all_button.get_active()
            tree_iters = []

            # 插入.. 点击后返回上个目录
            if filelist and self.dirname and self.dirname != '/':
                parent_dirname = os.path.dirname(self.dirname)
                pixbuf, type_ = self.app.mime.get(parent_dirname, True,
                                                  icon_size=ICON_SIZE)
                large_pixbuf, type_ = self.app.mime.get(parent_dirname, True,
                        icon_size=LARGE_ICON_SIZE)
                self.liststore.append([
                    state,
                    pixbuf,
                    large_pixbuf,
                    '..',
                    parent_dirname,
                    True,
                    0,
                    '0',
                    0,
                    '',
                ])

            for file_ in filelist:
                isdir = file_['isdir'] == '1'
                pixbuf, type_ = self.app.mime.get(file_['path'], isdir,
                                                  icon_size=ICON_SIZE)
                large_pixbuf, type_ = self.app.mime.get(file_['path'], isdir,
                        icon_size=LARGE_ICON_SIZE)
                size = int(file_.get('size', 0))
                human_size = util.get_human_size(size)[0]
                mtime = int(file_.get('server_mtime', 0))
                human_mtime = time.ctime(mtime)
                tree_iter = self.liststore.append([
                    state,
                    pixbuf,
                    large_pixbuf,
                    file_['server_filename'],
                    file_['path'],
                    isdir,
                    size,
                    human_size,
                    mtime,
                    human_mtime,
                ])
                tree_iters.append(tree_iter)
            cache_path = Config.get_cache_path(self.app.profile['username'])
            gutil.async_call(gutil.update_share_image, self.liststore,
                             tree_iters, ICON_COL, LARGE_ICON_COL,
                             filelist, cache_path,
                             ICON_SIZE, LARGE_ICON_SIZE)

        self.url_entry.props.secondary_icon_name = ABORT_ICON
        if not self.uk or not self.shareid:
            self.app.toast(_('Invalid link: {0}!').format(self.curr_url))
            self.has_next = False
            self.url_entry.props.secondary_icon_name = REFRESH_ICON
            return
        timestamp = time.time()
        self.url_entry.timestamp = timestamp
        gutil.async_call(pcs.list_share_files, self.app.cookie, self.app.tokens,
                         self.uk, self.shareid, self.dirname, self.page,
                         callback=on_load_url)

    def on_cloud_button_clicked(self, button):
        def on_transfer_files(info, error=None):
            if error or not info:
                self.app.toast(_('Failed to copy selected files!'))
                logger.error('SharePage.on_cloud_button_clicked: %s %s' %
                             (info, error))
            elif info['errno'] != 0:
                self.app.toast(_('Failed to copy selected files! {0}').format(
                                ErrorMsg.o.get(info['errno'])))
                logger.error('SharePage.on_cloud_button_clicked: %s %s' %
                             (info, error))
            else:
                self.app.blink_page(self.app.home_page)

        filelist = [row[PATH_COL] for row in self.liststore if
                    row[CHECK_COL] and row[NAME_COL] != '..']
        if not filelist:
            return
        folder_browser = FolderBrowserDialog(self, self.app, _('Save to..'))
        response = folder_browser.run()
        dest = folder_browser.get_path()
        folder_browser.destroy()
        if response != Gtk.ResponseType.OK:
            return
        gutil.async_call(pcs.share_transfer, self.app.cookie, self.app.tokens,
                         self.shareid, self.uk, filelist, dest,
                         self.app.profile['upload-mode'],
                         callback=on_transfer_files)

    def on_url_entry_activated(self, entry):
        self.reload()

    def on_url_entry_changed(self, entry):
        entry.props.secondary_icon_name = GO_ICON

    def on_url_entry_icon_pressed(self, entry, icon_pos, event):
        if entry.props.secondary_icon_name == GO_ICON:
            self.reload()
        elif entry.props.secondary_icon_name == REFRESH_ICON:
            entry.set_text(self.curr_url)
            self.reload()
        else:
            entry.timestamp = 0
            self.has_next = False
            entry.props.secondary_icon_name = REFRESH_ICON

    def on_select_all_button_toggled(self, column):
        state = self.select_all_button.get_active()
        self.select_all_button.set_active(not state)
        for row in self.liststore:
            row[CHECK_COL] = not state

    def on_row_checked(self, cell_renderer, path):
        self.liststore[path][CHECK_COL] = not self.liststore[path][CHECK_COL]

    def on_treeview_query_tooltip(self, treeview, x, y, keyboard_mode, tooltip):
        bx, by = treeview.convert_widget_to_bin_window_coords(x, y)
        selected = treeview.get_path_at_pos(bx, by)
        if not selected:
            return
        tree_path = selected[0]
        if tree_path is None:
            return

        box = Gtk.Box(spacing=5, orientation=Gtk.Orientation.VERTICAL)
        image = Gtk.Image.new_from_pixbuf(
                self.liststore[tree_path][LARGE_ICON_COL])
        image.props.xalign = 0
        image.props.halign = Gtk.Align.START
        box.pack_start(image, True, True, 0)
        if self.liststore[tree_path][NAME_COL] == '..':
            label = Gtk.Label(_('Go to parent directory: {0}').format(
                              self.liststore[tree_path][PATH_COL]))
        else:
            label = Gtk.Label(self.liststore[tree_path][PATH_COL])
        label.props.max_width_chars = 40
        label.props.xalign = 0
        label.props.halign = Gtk.Align.START
        label.props.wrap_mode = Pango.WrapMode.CHAR
        label.props.wrap = True
        box.pack_start(label, False, False, 0)
        tooltip.set_custom(box)
        box.show_all()
        return True

    def on_treeview_row_activated(self, treeview, tree_path, column):
        if tree_path is None:
            return

        # 现在只处理目录
        if self.liststore[tree_path][ISDIR_COL]:
            dirname = self.liststore[tree_path][PATH_COL]
            new_url = pcs.get_share_url_with_dirname(self.uk, self.shareid,
                                                     dirname)
            self.url_entry.set_text(new_url)
            self.reload()

    def on_treeview_scrolled(self, adjustment):
        if gutil.reach_scrolled_bottom(adjustment) and self.has_next:
            self.load_next()
