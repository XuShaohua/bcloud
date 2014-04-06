
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud import encoder
from bcloud import gutil
from bcloud import pcs
from bcloud import util

(PIXBUF_COL, NAME_COL, PATH_COL, ISDIR_COL, FSID_COL, MD5_COL,
    SIZE_COL, TOOLTIP_COL, URL_COL, SHAREID_COL) = list(range(10))

HOME_PAGE, FILE_PAGE = 0, 1


class PathBox(Gtk.Box):

    def __init__(self, parent):
        super().__init__(spacing=0)
        self.parent = parent

        home_button = Gtk.Button.new_with_label(_('Home'))
        home_button.connect(
            'clicked', lambda *args: parent.load(parent.uk))
        self.pack_start(home_button, False, False, 0)

        all_files_button = Gtk.Button.new_with_label(_('All Files'))
        all_files_button.connect(
            'clicked', self.on_all_files_button_clicked)
        self.pack_start(all_files_button, False, False, 0)

        self.list_box = Gtk.Box()
        self.pack_start(self.list_box, True, True, 0)
        
    def clear_buttons(self):
        buttons = self.list_box.get_children()
        for button in buttons:
            self.list_box.remove(button)

    def append_button(self, abspath, name):
        button = Gtk.Button.new_with_label(gutil.ellipse_text(name))
        button.abspath = abspath
        button.set_tooltip_text(name)
        self.list_box.pack_start(button, False, False, 0)
        button.connect('clicked', self.on_button_clicked)

    def on_button_clicked(self, button):
        self.parent.list_share_files(button.abspath)

    def on_all_files_button_clicked(self, button):
        self.clear_buttons()
        self.parent.load_share(self.parent.file_url)
    
    # Open API
    def reset(self):
        self.clear_buttons()

    # Open API
    def set_path(self, path):
        '''在导航栏中更新各目录的信息
        
        path - 当前目录的绝对路径.
        我们需要与parent.file_path做比较, 然后得到一个相对路径, 只需要在
        里面显示出相对路径即可.
        '''
        self.clear_buttons()
        if path == self.parent.file_path:
            return
        pathlist = util.rec_split_path(path)
        for (abspath, name) in pathlist:
            if (not abspath.startswith(self.parent.file_path) or 
                not abspath.replace(self.parent.file_path, '')):
                continue
            self.append_button(abspath, name)
        self.show_all()


class SharePage(Gtk.Box):

    icon_name = 'share-symbolic'
    disname = _('Share')
    tooltip = _('Share')
    first_run = True
    page_num = 1
    has_next = True
    page_type = HOME_PAGE

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        toolbar = Gtk.Toolbar()
        self.pack_start(toolbar, False, False, 0)
        toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        toolbar.set_show_arrow(False)
        toolbar.set_icon_size(Gtk.IconSize.BUTTON)

        url_item = Gtk.ToolItem()
        toolbar.insert(url_item, 0)
        url_item.set_expand(True)
        self.url_entry = Gtk.Entry()
        self.url_entry.connect('activate', self.on_url_entry_activated)
        url_item.add(self.url_entry)

        home_button = Gtk.ToolButton()
        home_button.set_label(_('Home'))
        home_button.set_icon_name('go-home-symbolic')
        home_button.connect('clicked', self.on_home_button_clicked)
        toolbar.insert(home_button, 1)

        self.notebook = Gtk.Notebook()
        self.pack_start(self.notebook, True, True, 0)

        home_win = Gtk.ScrolledWindow()
        home_win.get_vadjustment().connect(
                'value-changed', self.on_home_window_scrolled)
        self.notebook.append_page(home_win, Gtk.Label.new('Home'))

        # pixbuf, name, path, isdir, fsid, md5,
        # size, tooltip, share link, shareid,
        self.home_liststore = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, str, bool, str, str,
                GObject.TYPE_LONG, str, str, str)
        self.home_iconview= Gtk.IconView(model=self.home_liststore)
        home_win.add(self.home_iconview)
        self.home_iconview.set_pixbuf_column(PIXBUF_COL)
        self.home_iconview.set_text_column(NAME_COL)
        self.home_iconview.set_tooltip_column(TOOLTIP_COL)
        self.home_iconview.set_item_width(84)
        self.home_iconview.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.home_iconview.connect(
                'item-activated', self.on_home_iconview_item_activated)
        self.home_iconview.connect(
                'button-press-event', self.on_home_iconview_button_pressed)

        file_box = Gtk.Box()
        file_box.set_orientation(Gtk.Orientation.VERTICAL)
        self.notebook.append_page(file_box, Gtk.Label.new('File'))

        self.path_box = PathBox(self)
        file_box.pack_start(self.path_box, False, False, 0)

        file_win = Gtk.ScrolledWindow()
        file_box.pack_start(file_win, True, True, 0)

        # pixbuf, name, path, isdir, fsid, md5,
        # size, tooltip, share link, shareid
        self.file_liststore = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, str, bool, str, str,
                GObject.TYPE_LONG, str, str, str)
        self.file_iconview = Gtk.IconView(model=self.file_liststore)
        file_win.add(self.file_iconview)
        self.file_iconview.set_pixbuf_column(PIXBUF_COL)
        self.file_iconview.set_text_column(NAME_COL)
        self.file_iconview.set_tooltip_column(TOOLTIP_COL)
        self.file_iconview.set_item_width(84)
        self.file_iconview.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.file_iconview.connect(
                'item-activated', self.on_file_iconview_item_activated)
        
    # Open API
    def load(self, uk=None):
        '''载入用户自己的所有分享'''
        def on_load(info, error=None):
            if error or not info or info['errno'] != 0:
                return
            self.display_home_files(info['records'])

        self.notebook.set_current_page(HOME_PAGE)
        self.home_liststore.clear()
        self.page_num = 1
        self.path_box.hide()
        self.has_next = True
        if not uk:
            if 'uk' not in self.app.profile:
                uk = pcs.get_user_uk(self.app.cookie, self.app.tokens)
                if not uk:
                    return
                self.app.profile['uk'] = uk
            self.uk = self.app.profile['uk']
        else:
            self.uk = uk
        gutil.async_call(
                pcs.list_share, self.app.cookie, self.app.tokens, self.uk,
                self.page_num, callback=on_load)

    def load_next(self):
        '''Load next page'''
        def on_load_next(info, error=None):
            if error or not info or info['errno'] != 0:
                return
            if info['records']:
                self.display_home_files(info['records'])
            else:
                self.has_next = False

        if not self.has_next:
            return
        self.page_num = self.page_num + 1
        gutil.async_call(
                pcs.list_share, self.app.cookie, self.app.tokens, self.uk,
                self.page_num, callback=on_load_next)

    def display_home_files(self, share_files):
        for share_file in share_files:
            if not share_file['filelist']:
                continue
            filelists = share_file['filelist']
            filelist = filelists[0]
            if len(filelists) > 1:
                path, _ = os.path.split(
                        encoder.decode_uri_component(filelist['path']))
                pixbuf, _ = self.app.mime.get('unknown', False)
                tooltip = path
            else:
                path = encoder.decode_uri_component(filelist['path'])
                pixbuf, _ = self.app.mime.get(path, filelist['isdir'])
                tooltip = path
            url = 'http://pan.baidu.com/s/' + share_file['shorturl']
            self.home_liststore.append([
                pixbuf,
                share_file['title'],
                path,
                filelist['isdir'],
                str(filelist['fs_id']),
                filelist['md5'],
                filelist['size'],
                tooltip,
                url,
                share_file['shareid'],
                ])

    # Open API
    def load_share(self, url):
        '''显示某个分享URL的基本内容.

        URL 可以是长链接或者短链接
        '''
        def on_load_share(share_files, error=None):
            if error or not share_files or not share_files['list']:
                return
            self.uk = share_files['uk']
            self.file_sign = share_files['sign']
            self.file_path, _ = os.path.split(share_files['list'][0]['path'])
            self.file_share_id = share_files['share_id']
            self.path_box.reset()
            self.display_share_files(share_files['list'])

        print('load share:', url)
        self.path_box.show_all()
        self.notebook.set_current_page(FILE_PAGE)
        self.file_liststore.clear()
        self.file_page_num = 1
        self.file_has_next = True
        self.file_url = url
        #gutil.async_call(
        #        pcs.get_share_page, url, callback=on_load_share)
        info = pcs.get_share_page(url)
        on_load_share(info)

    def load_share_next(self):
        pass

    def list_share_files(self, path):
        '''显示某个分享url的子目录/文件'''
        def on_list_share_files(info, error=None):
            if error or not info or info['errno'] != 0:
                return
            self.display_share_files(info['list'])

        print('list_share_files:', path)
        self.file_liststore.clear()
        self.path_box.set_path(path)
        gutil.async_call(
            pcs.list_share_path, self.app.cookie, self.app.tokens,
            self.uk, path, self.file_share_id, self.file_page_num,
            callback=on_list_share_files)

    def display_share_files(self, share_files):
        for share_file in share_files:
            is_dir = bool(int(share_file['isdir']))
            pixbuf, file_type = self.app.mime.get(
                    share_file['path'], is_dir)
            self.file_liststore.append([
                pixbuf,
                share_file['server_filename'],
                share_file['path'],
                is_dir,
                str(share_file['fs_id']),
                share_file.get('md5', ''),
                int(share_file['size']),
                share_file['path'],
                self.file_url,
                self.file_share_id,
                ])

    def on_url_entry_activated(self, entry):
        print(entry.get_text())

    def on_home_button_clicked(self, button):
        self.load()

    def on_home_iconview_item_activated(self, iconview, tree_path):
        url = self.home_liststore[tree_path][URL_COL]
        self.load_share(url)

    def on_home_iconview_button_pressed(self, iconview, event):
        if ((event.type != Gdk.EventType.BUTTON_PRESS) or
                (event.button != Gdk.BUTTON_SECONDARY)):
            return
        print(event)
        tree_path = iconview.get_path_at_pos(event.x, event.y)
        selected_tree_paths = iconview.get_selected_items()
        if tree_path not in selected_tree_paths:
            selected_tree_paths.append(tree_path)

        if tree_path is None:
            iconview.unselect_all()
            print('popup folder menu')
            self.popup_home_folder_menu(event)
        else:
            modified = ((event.state & Gdk.ModifierType.CONTROL_MASK) |
                    (event.state & Gdk.ModifierType.SHIFT_MASK))
            if not modified and tree_path not in selected_tree_paths:
                iconview.unselect_all()
            iconview.select_path(tree_path)
            self.popup_home_item_menu(event, selected_tree_paths)

    def popup_home_folder_menu(self, event):
        def on_reload_item(menu_item):
            self.load(self.uk)

        menu = Gtk.Menu()
        self.file_menu = menu

        reload_item = Gtk.MenuItem.new_with_label(_('Reload'))
        reload_item.connect('activate', on_reload_item)
        menu.append(reload_item)

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)

    def popup_home_item_menu(self, event, tree_paths):
        def on_disable_share_item_cb(info, error=None):
            if error or not info or info['errno'] != 0:
                msg = info.get('err_msg', '')
                if msg:
                    self.app.toast(
                            _('Failed to disable share, {0}'.format(msg)))
                return
            self.app.toast(_('Share link removed'))

        def on_disable_share_item(menu_item):
            shareid_list = [liststore[p][SHAREID_COL] for p in tree_paths]
            gutil.async_call(
                pcs.disable_share, self.app.cookie, self.app.tokens,
                shareid_list, callback=on_disable_share_item_cb)

        liststore = self.home_liststore
        menu = Gtk.Menu()
        self.file_menu = menu

        if self.uk == self.app.profile['uk']:
            disable_share_item = Gtk.MenuItem.new_with_label(
                    _('Disable Share'))
            disable_share_item.connect('activate', on_disable_share_item)
            menu.append(disable_share_item)

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)

    def on_home_window_scrolled(self, adj):
        if gutil.reach_scrolled_bottom(adj) and self.has_next:
            if self.page_type == HOME_PAGE:
                self.load_next()
            elif self.page_type == FILE_PAGE:
                self.load_share_next()

    def on_file_iconview_item_activated(self, iconview, tree_path):
        # TODO: 加入右键 APP_INFO
        if not self.file_liststore[tree_path][ISDIR_COL]:
            return
        path = self.file_liststore[tree_path][PATH_COL]
        self.list_share_files(path)
