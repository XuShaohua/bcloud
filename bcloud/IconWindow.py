
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import mimetypes
import json
import os
import time

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud.FolderBrowserDialog import FolderBrowserDialog
from bcloud.NewFolderDialog import NewFolderDialog
from bcloud.PropertiesDialog import PropertiesDialog
from bcloud.PropertiesDialog import FolderPropertyDialog
from bcloud.RenameDialog import RenameDialog
from bcloud import gutil
from bcloud import pcs
from bcloud import util

(PIXBUF_COL, NAME_COL, PATH_COL, TOOLTIP_COL, SIZE_COL, HUMAN_SIZE_COL,
    ISDIR_COL, MTIME_COL, HUMAN_MTIME_COL, TYPE_COL, PCS_FILE_COL
    ) = list(range(11))
TYPE_TORRENT = 'application/x-bittorrent'

class IconWindow(Gtk.ScrolledWindow):
    '''这个类用于获取文件, 并将它显示到IconView中去.

    可以作为其它页面的一个主要组件.
    其中的网络操作部分多半是异步进行的.
    '''

    ICON_SIZE = 64

    def __init__(self, parent, app):
        super().__init__()
        self.parent = parent
        self.app = app

        # pixbuf, name, path, tooltip, size, humansize,
        # isdir, mtime, human mtime, type, pcs_file
        self.liststore = Gtk.ListStore(
            GdkPixbuf.Pixbuf, str, str, str, GObject.TYPE_INT64, str,
            GObject.TYPE_INT, GObject.TYPE_INT64, str, str, str)
        self.init_ui()

    def init_ui(self):
        self.iconview = Gtk.IconView(model=self.liststore)
        self.iconview.set_pixbuf_column(PIXBUF_COL)
        self.iconview.set_text_column(NAME_COL)
        self.iconview.set_tooltip_column(TOOLTIP_COL)
        self.iconview.set_item_width(84)
        self.iconview.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.iconview.connect(
                'item-activated', self.on_iconview_item_activated)
        self.iconview.connect(
                'button-press-event', self.on_iconview_button_pressed)
        self.add(self.iconview)
        self.get_vadjustment().connect('value-changed', self.on_scrolled)
        self.liststore.set_sort_func(NAME_COL, gutil.tree_model_natsort)

    def load(self, pcs_files):
        '''载入一个目录并显示里面的内容.'''
        self.liststore.clear()
        self.display_files(pcs_files)

    def load_next(self, pcs_files):
        '''当滚动条向下滚动到一定位置时, 调用这个方法载入下一页'''
        self.display_files(pcs_files)

    def display_files(self, pcs_files):
        '''重新格式化一下文件列表, 去除不需要的信息

        这一操作主要是为了便于接下来的查找工作.
        文件的path都被提取出来, 然后放到了一个list中.
        '''
        cache_path = Config.get_cache_path(self.app.profile['username'])
        for pcs_file in pcs_files:
            path = pcs_file['path']
            pixbuf, type_ = self.app.mime.get(
                    path, pcs_file['isdir'], icon_size=self.ICON_SIZE)
            name = os.path.split(path)[NAME_COL]
            tooltip = gutil.escape(name)
            size = pcs_file.get('size', 0)
            human_size = util.get_human_size(pcs_file['size'])[0]
            mtime = pcs_file.get('server_mtime', 0)
            human_mtime = time.ctime(mtime)
            tree_iter = self.liststore.append([
                pixbuf, name, path, tooltip, size, human_size,
                pcs_file['isdir'], mtime, human_mtime, type_,
                json.dumps(pcs_file), ])
            gutil.update_liststore_image(
                self.liststore, tree_iter, PIXBUF_COL, pcs_file,
                cache_path, icon_size=self.ICON_SIZE)

    def get_pcs_file(self, tree_path):
        '''获取原始的pcs文件信息'''
        return json.loads(self.liststore[tree_path][PCS_FILE_COL])

    def on_scrolled(self, adj):
        if gutil.reach_scrolled_bottom(adj) and self.parent.has_next:
            self.parent.load_next()

    def on_iconview_item_activated(self, iconview, tree_path):
        path = self.liststore[tree_path][PATH_COL]
        type_ = self.liststore[tree_path][TYPE_COL]
        if type_ == 'folder':
            self.app.home_page.load(path)
        else:
            self.launch_app(tree_path)

    def on_iconview_button_pressed(self, iconview, event):
        if ((event.type != Gdk.EventType.BUTTON_PRESS) or
                (event.button != Gdk.BUTTON_SECONDARY)):
            return

        tree_path = self.iconview.get_path_at_pos(event.x, event.y)
        selected_tree_paths = self.iconview.get_selected_items()

        if tree_path is None:
            self.iconview.unselect_all()
            self.popup_folder_menu(event)
        else:
            modified = ((event.state & Gdk.ModifierType.CONTROL_MASK) |
                    (event.state & Gdk.ModifierType.SHIFT_MASK))
            if not modified and tree_path not in selected_tree_paths:
                self.iconview.unselect_all()
            self.iconview.select_path(tree_path)
            self.popup_item_menu(event)

    def popup_folder_menu(self, event):
        # create folder; reload; share; properties
        menu = Gtk.Menu()
        self.menu = menu
        
        new_folder_item = Gtk.MenuItem.new_with_label(_('New Folder'))
        new_folder_item.connect('activate', self.on_new_folder_activated)
        menu.append(new_folder_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        reload_item = Gtk.MenuItem.new_with_label(_('Reload'))
        reload_item.connect('activate', self.on_reload_activated)
        menu.append(reload_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        props_item = Gtk.MenuItem.new_with_label(_('Properties'))
        props_item.connect('activate', self.on_props_activated)
        menu.append(props_item)

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)

    def popup_item_menu(self, event):
        # 要检查选中的条目数, 如果选中多个, 只显示出它们共有的一些菜单项:
        # share; rename; delete; copy to; move to; download;
        def build_app_menu(menu, menu_item, app_info):
            menu_item.set_always_show_image(True)
            img = self.app.mime.get_app_img(app_info)
            if img:
                menu_item.set_image(img)
            menu_item.connect(
                    'activate', self.on_launch_app_activated, app_info)
            menu.append(menu_item)

        tree_paths = self.iconview.get_selected_items()
        menu = Gtk.Menu()
        # 将这个menu标记为对象的属性, 不然很快它就会被回收, 就无法显示出菜单
        self.menu = menu

        if len(tree_paths) == 1:
            tree_path = tree_paths[0]
            file_type = self.liststore[tree_path][TYPE_COL]
            if file_type == 'folder':
                open_dir_item = Gtk.MenuItem.new_with_label(_('Open'))
                open_dir_item.connect(
                        'activate', self.on_open_dir_item_activated)
                menu.append(open_dir_item)
            # 不是目录的话, 就显示出程序菜单
            else:
                if file_type == TYPE_TORRENT:
                    cloud_download_item = Gtk.MenuItem.new_with_label(
                            _('Cloud Download'))
                    cloud_download_item.connect(
                            'activate',
                            self.on_cloud_download_item_activated)
                    menu.append(cloud_download_item)
                app_infos = Gio.AppInfo.get_recommended_for_type(file_type)
                # 第一个app_info是默认的app.
                if len(app_infos) > 2:
                    app_info = app_infos[0]
                    launch_item = Gtk.ImageMenuItem.new_with_label(
                        _('Open With {0}').format(
                            app_info.get_display_name()))
                    build_app_menu(menu, launch_item, app_info)

                    more_app_item = Gtk.MenuItem.new_with_label(
                            _('Open With'))
                    menu.append(more_app_item)
                    sub_menu = Gtk.Menu()
                    more_app_item.set_submenu(sub_menu)

                    for app_info in app_infos[1:]:
                        launch_item = Gtk.ImageMenuItem.new_with_label(
                                app_info.get_display_name())
                        build_app_menu(sub_menu, launch_item, app_info)
                    sep_item = Gtk.SeparatorMenuItem()
                    sub_menu.append(sep_item)
                    choose_app_item = Gtk.MenuItem.new_with_label(
                            _('Other Application...'))
                    choose_app_item.connect(
                            'activate', self.on_choose_app_activated)
                    sub_menu.append(choose_app_item)
                else:
                    for app_info in app_infos:
                        launch_item = Gtk.ImageMenuItem.new_with_label(
                            _('Open With {0}').format(
                                app_info.get_display_name()))
                        build_app_menu(menu, launch_item, app_info)
                    choose_app_item = Gtk.MenuItem.new_with_label(
                            _('Open With Other Application...'))
                    choose_app_item.connect(
                            'activate', self.on_choose_app_activated)
                    menu.append(choose_app_item)

                sep_item = Gtk.SeparatorMenuItem()
                menu.append(sep_item)
                copy_link_item = Gtk.MenuItem.new_with_label(_('Copy Link'))
                copy_link_item.connect(
                        'activate', self.on_copy_link_activated)
                menu.append(copy_link_item)

            sep_item = Gtk.SeparatorMenuItem()
            menu.append(sep_item)

        download_item = Gtk.MenuItem.new_with_label(_('Download...'))
        download_item.connect('activate', self.on_download_activated)
        menu.append(download_item)
        share_item = Gtk.MenuItem.new_with_label(_('Share...'))
        share_item.connect('activate', self.on_share_activated)
        menu.append(share_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        moveto_item = Gtk.MenuItem.new_with_label(_('Move To...'))
        moveto_item.connect('activate', self.on_moveto_activated)
        menu.append(moveto_item)
        copyto_item = Gtk.MenuItem.new_with_label(_('Copy To...'))
        copyto_item.connect('activate', self.on_copyto_activated)
        menu.append(copyto_item)
        rename_item = Gtk.MenuItem.new_with_label(_('Rename...'))
        rename_item.connect('activate', self.on_rename_activated)
        menu.append(rename_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        trash_item = Gtk.MenuItem.new_with_label(_('Move to Trash'))
        trash_item.connect('activate', self.on_trash_activated)
        menu.append(trash_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        props_item = Gtk.MenuItem.new_with_label(_('Properties'))
        props_item.connect('activate', self.on_props_activated)
        menu.append(props_item)

        menu.show_all()
        menu.popup(None, None, None, None, 0, event.time)

    # current folder popup menu
    def on_new_folder_activated(self, menu_item):
        dialog = NewFolderDialog(self.parent, self.app, self.parent.path)
        dialog.run()
        dialog.destroy()

    def on_reload_activated(self, menu_item):
        self.parent.reload()

    def launch_app(self, tree_path):
        '''用默认的程序打开这个文件链接.'''
        file_type = self.liststore[tree_path][TYPE_COL]
        app_infos = Gio.AppInfo.get_recommended_for_type(file_type)
        if app_infos:
            self.launch_app_with_app_info(app_infos[0])
        else:
            pass

    def launch_app_with_app_info(self, app_info):
        def open_video_link(resp, error=None):
            '''得到视频最后地址后, 调用播放器直接播放'''
            if error or not resp:
                return
            red_url, req_id = resp
            gutil.async_call(app_info.launch_uris, [red_url, ], None)

        def save_playlist(pls, error=None):
            '''先保存播放列表到临时目录, 再调用播放器直接打开这个播放列表

            如果pls为None的话, 说明没能得到播放列表, 这时就需要使用之前的方
            法, 先得琶视频地址, 再用播放器去打开它.
            '''
            if error or not pls or b'error_code' in pls:
                gutil.async_call(
                        pcs.get_download_link, self.app.cookie,
                        pcs_file['dlink'], callback=open_video_link)
            else:
                pls_filepath = os.path.join(
                        '/tmp', pcs_file['server_filename'] + '.m3u8')
                with open(pls_filepath, 'wb') as fh:
                    fh.write(pls)
                pls_file_uri = 'file://' + pls_filepath
                app_info.launch_uris([pls_file_uri, ], None)

        # first, download this to load dir
        # then open it with app_info
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        tree_path = tree_paths[0]
        file_type = self.liststore[tree_path][TYPE_COL]
        pcs_file = self.get_pcs_file(tree_path)
        # 'media' 对应于rmvb格式.
        # 如果是视频等多媒体格式的话, 默认是直接调用播放器进行网络播放的
        if 'video' in file_type or 'media' in file_type:
            if self.app.profile['use-streaming']:
                gutil.async_call(
                        pcs.get_streaming_playlist, self.app.cookie,
                        pcs_file['path'], callback=save_playlist)
            else:
                gutil.async_call(
                        pcs.get_download_link, self.app.cookie,
                        pcs_file['dlink'], callback=open_video_link)
        else:
            self.app.blink_page(self.app.download_page)
            self.app.download_page.add_launch_task(pcs_file, app_info)

    # item popup menu
    def on_launch_app_activated(self, menu_item, app_info):
        self.launch_app_with_app_info(app_info)

    def on_choose_app_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths or len(tree_paths) != 1:
            return
        tree_path = tree_paths[0]
        type_ = self.liststore[tree_path][TYPE_COL]
        dialog = Gtk.AppChooserDialog.new_for_content_type(
                self.app.window, Gtk.DialogFlags.MODAL,
                type_)
        response = dialog.run()
        app_info = dialog.get_app_info()
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return
        self.launch_app_with_app_info(app_info)

    def on_open_dir_item_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if tree_paths and len(tree_paths) == 1:
            self.parent.load(self.liststore[tree_paths[0]][PATH_COL])

    def on_cloud_download_item_activated(self, menu_item):
        '''创建离线下载任务, 下载选中的BT种子.'''
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        self.app.cloud_page.add_cloud_bt_task(
            self.liststore[tree_paths[0]][PATH_COL])
        self.app.blink_page(self.app.cloud_page)

    def on_copy_link_activated(self, menu_item):
        def copy_link_to_clipboard(res, error=None):
            if error or not res:
                return
            red_url, req_id = res
            self.app.update_clipboard(red_url)

        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        pcs_file = self.get_pcs_file(tree_paths[0])
        gutil.async_call(
                pcs.get_download_link, self.app.cookie, pcs_file['dlink'],
                callback=copy_link_to_clipboard)

    def on_download_activated(self, menu_item):
        # 下载文件与下载目录的操作是不相同的.
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        pcs_files = [self.get_pcs_file(p) for p in tree_paths]
        self.app.blink_page(self.app.download_page)
        self.app.download_page.add_tasks(pcs_files)

    def on_share_activated(self, menu_item):
        def on_share(info, error=None):
            if error or not info or info['errno'] != 0:
                self.app.toast(_('Failed to share selected files'))
                return
            self.app.update_clipboard(info['shorturl'])

        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        fid_list = []
        for tree_path in tree_paths:
            pcs_file = self.get_pcs_file(tree_path)
            fid_list.append(pcs_file['fs_id'])
            gutil.async_call(
                    pcs.enable_share, self.app.cookie, self.app.tokens,
                    fid_list, callback=on_share)

    def on_moveto_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return

        dialog = FolderBrowserDialog(self.parent, self.app, _('Move To...'))
        response = dialog.run()
        targ_path = ''
        if response != Gtk.ResponseType.OK:
            dialog.destroy()
            return
        targ_path = dialog.get_path()
        dialog.destroy()

        filelist = []
        for tree_path in tree_paths:
            filelist.append({
                'path': self.liststore[tree_path][PATH_COL],
                'dest': targ_path,
                'newname': self.liststore[tree_path][NAME_COL],
                })
        gutil.async_call(
                pcs.move,
                self.app.cookie, self.app.tokens, filelist,
                callback=self.parent.reload)

    def on_copyto_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return

        dialog = FolderBrowserDialog(self.parent, self.app, _('Copy To...'))
        response = dialog.run()
        targ_path = ''
        if response != Gtk.ResponseType.OK:
            dialog.destroy()
            return
        targ_path = dialog.get_path()
        dialog.destroy()

        filelist = []
        for tree_path in tree_paths:
            filelist.append({
                'path': self.liststore[tree_path][PATH_COL],
                'dest': targ_path,
                'newname': self.liststore[tree_path][NAME_COL],
                })
        gutil.async_call(
                pcs.copy,
                self.app.cookie, self.app.tokens, filelist,
                callback=self.parent.reload)

    def on_rename_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        path_list = []
        for tree_path in tree_paths:
            path_list.append(self.liststore[tree_path][PATH_COL])
        dialog = RenameDialog(self.app, path_list)
        dialog.run()
        dialog.destroy()

    def on_trash_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        path_list = []
        for tree_path in tree_paths:
            path_list.append(self.liststore[tree_path][PATH_COL])
        gutil.async_call(
                pcs.delete_files, self.app.cookie, self.app.tokens,
                path_list, callback=self.parent.reload)
        self.app.blink_page(self.app.trash_page)

    def on_props_activated(self, menu_item):
        '''显示选中的文件或者当前目录的属性'''
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            dialog = FolderPropertyDialog(self, self.app, self.parent.path)
            dialog.run()
            dialog.destroy()
        else:
            for tree_path in tree_paths:
                pcs_file = self.get_pcs_file(tree_path)
                dialog = PropertiesDialog(self.parent, self.app, pcs_file)
                dialog.run()
                dialog.destroy()


class TreeWindow(IconWindow):

    ICON_SIZE = 24

    def __init__(self, parent, app):
        super().__init__(parent, app)

    # Override
    def init_ui(self):
        self.iconview = Gtk.TreeView(model=self.liststore)
        self.iconview.set_tooltip_column(TOOLTIP_COL)
        self.iconview.connect(
                'row-activated',
                lambda view, path, column:
                    self.on_iconview_item_activated(view, path))
        self.iconview.connect(
                'button-press-event', self.on_iconview_button_pressed)
        self.get_vadjustment().connect('value-changed', self.on_scrolled)
        self.iconview.set_headers_clickable(True)
        self.iconview.set_reorderable(True)
        self.iconview.set_search_column(NAME_COL)
        self.selection = self.iconview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.add(self.iconview)

        icon_cell = Gtk.CellRendererPixbuf()
        name_cell = Gtk.CellRendererText(
                ellipsize=Pango.EllipsizeMode.END, ellipsize_set=True)
        name_col = Gtk.TreeViewColumn()
        name_col.set_title(_('Name'))
        name_col.pack_start(icon_cell, False)
        name_col.pack_start(name_cell, True)
        if Config.GTK_LE_36:
            name_col.add_attribute(icon_cell, 'pixbuf', PIXBUF_COL)
            name_col.add_attribute(name_cell, 'text', NAME_COL)
        else:
            name_col.set_attributes(icon_cell, pixbuf=PIXBUF_COL)
            name_col.set_attributes(name_cell, text=NAME_COL)
        name_col.set_expand(True)
        name_col.set_resizable(True)
        self.iconview.append_column(name_col)
        name_col.set_sort_column_id(NAME_COL)
        self.liststore.set_sort_func(NAME_COL, gutil.tree_model_natsort)

        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(
                _('Size'), size_cell, text=HUMAN_SIZE_COL)
        self.iconview.append_column(size_col)
        size_col.props.min_width = 100
        size_col.set_resizable(True)
        size_col.set_sort_column_id(SIZE_COL)

        mtime_cell = Gtk.CellRendererText()
        mtime_col = Gtk.TreeViewColumn(
                _('Modified'), mtime_cell, text=HUMAN_MTIME_COL)
        self.iconview.append_column(mtime_col)
        mtime_col.props.min_width = 100
        mtime_col.set_resizable(True)
        mtime_col.set_sort_column_id(MTIME_COL)

        # Override selection methods
        self.iconview.unselect_all = self.selection.unselect_all
        self.iconview.select_path = self.selection.select_path
        # Gtk.TreeSelection.get_selected_rows() returns (model, tree_paths)
        self.iconview.get_selected_items = lambda: self.selection.get_selected_rows()[1]
        # Gtk.TreeView.get_path_at_pos() returns (path, column)
        def get_path_at_pos(x, y):
            selected = Gtk.TreeView.get_path_at_pos(self.iconview, x, y)
            if selected:
                return selected[0]
            else:
                return None
        self.iconview.get_path_at_pos = get_path_at_pos
