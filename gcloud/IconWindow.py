
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import mimetypes
import os

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import Gtk

from gcloud import Config
_ = Config._
from gcloud.FolderBrowserDialog import FolderBrowserDialog
from gcloud.NewFolderDialog import NewFolderDialog
from gcloud.PropertiesDialog import PropertiesDialog
from gcloud.RenameDialog import RenameDialog
from gcloud import gutil
from gcloud import pcs

PIXBUF_COL, DISNAME_COL, PATH_COL, TOOLTIP_COL, TYPE_COL = list(range(5))

class IconWindow(Gtk.ScrolledWindow):
    '''这个类用于获取文件, 并将它显示到IconView中去.

    可以作为其它页面的一个主要组件.
    其中的网络操作部分多半是异步进行的.
    '''

    filelist = []
    pathlist = []

    def __init__(self, parent, app):
        super().__init__()
        self.parent = parent
        self.app = app

        # pixbuf, disname, path, tooltip, type 
        self.liststore = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str, str, str)
        self.iconview = Gtk.IconView(model=self.liststore)
        self.iconview.set_pixbuf_column(PIXBUF_COL)
        self.iconview.set_text_column(DISNAME_COL)
        self.iconview.set_tooltip_column(TOOLTIP_COL)
        self.iconview.set_item_width(84)
        self.iconview.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.iconview.connect(
                'item-activated', self.on_iconview_item_activated)
        self.iconview.connect(
                'button-press-event', self.on_iconview_button_pressed)
        self.add(self.iconview)

    def load(self, filelist, error=None):
        '''载入一个目录并显示里面的内容.'''
        print('IconWindow.load() --')
        self.filelist = []
        self.pathlist = []
        self.liststore.clear()
        if not error:
            self.display_filelist(filelist)

    def load_next(self, filelist, error=None):
        '''当滚动条向下滚动到一定位置时, 调用这个方法载入下一页'''
        if not error:
            self.display_filelist(filelist)

    def display_filelist(self, filelist):
        '''重新格式化一下文件列表, 去除不需要的信息

        这一操作主要是为了便于接下来的查找工作.
        文件的path都被提取出来, 然后放到了一个list中.
        '''
        if filelist['errno'] != 0:
            return
        if 'list' in filelist:
            key = 'list'
        elif 'info' in filelist:
            key = 'info'
        else:
            print('Error: current filelist format not supported!')
            print(filelist)
            return
        cache_path = Config.get_cache_path(self.app.profile['username'])
        for pcs_file in filelist[key]:
            path = pcs_file['path']
            self.filelist.append(pcs_file)
            self.pathlist.append(path)
            pixbuf, type_ = self.app.mime.get(path, pcs_file['isdir'])
            disname = os.path.split(path)[DISNAME_COL]
            #tooltip = gutil.escape(disname)
            tooltip = disname
            tree_iter = self.liststore.append([
                pixbuf, disname, path, tooltip, type_
                ])
            gutil.update_liststore_image(
                self.liststore, tree_iter, PIXBUF_COL, pcs_file,
                cache_path,
                )

    def on_iconview_item_activated(self, iconview, tree_path):
        path = self.liststore[tree_path][PATH_COL]
        type_ = self.liststore[tree_path][TYPE_COL]
        if type_ == 'folder':
            self.app.home_page.load(path)
        else:
            #print('will load:', path)
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
        
        new_folder_item = Gtk.MenuItem(_('New Folder'))
        new_folder_item.connect('activate', self.on_new_folder_activated)
        menu.append(new_folder_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        reload_item = Gtk.MenuItem(_('Reload'))
        reload_item.connect('activate', self.on_reload_activated)
        menu.append(reload_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        props_item = Gtk.MenuItem(_('Properties'))
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
                open_dir_item = Gtk.MenuItem(_('Open'))
                open_dir_item.connect(
                        'activate', self.on_open_dir_item_activated)
                menu.append(open_dir_item)
            # 不是目录的话, 就显示出程序菜单
            else:
                app_infos = Gio.AppInfo.get_recommended_for_type(file_type)
                # 第一个app_info是默认的app.
                if len(app_infos) > 2:
                    app_info = app_infos[0]
                    launch_item = Gtk.ImageMenuItem(
                            _('Open with ') + app_info.get_display_name())
                    build_app_menu(menu, launch_item, app_info)

                    more_app_item = Gtk.MenuItem(_('Open with'))
                    menu.append(more_app_item)
                    sub_menu = Gtk.Menu()
                    more_app_item.set_submenu(sub_menu)

                    for app_info in app_infos[1:]:
                        launch_item = Gtk.ImageMenuItem(
                                app_info.get_display_name())
                        build_app_menu(sub_menu, launch_item, app_info)
                    sep_item = Gtk.SeparatorMenuItem()
                    sub_menu.append(sep_item)
                    choose_app_item = Gtk.MenuItem(_('Other Application...'))
                    choose_app_item.connect(
                            'activate', self.on_choose_app_activated)
                    sub_menu.append(choose_app_item)
                else:
                    for app_info in app_infos:
                        launch_item = Gtk.ImageMenuItem(
                                _('Open with ') + app_info.get_display_name())
                        build_app_menu(menu, launch_item, app_info)
                    choose_app_item = Gtk.MenuItem(
                            _('Open with Other Application...'))
                    choose_app_item.connect(
                            'activate', self.on_choose_app_activated)
                    menu.append(choose_app_item)

                sep_item = Gtk.SeparatorMenuItem()
                menu.append(sep_item)
                copy_link_item = Gtk.MenuItem(_('Copy Link'))
                copy_link_item.connect(
                        'activate', self.on_copy_link_activated)
                menu.append(copy_link_item)

            sep_item = Gtk.SeparatorMenuItem()
            menu.append(sep_item)

        download_item = Gtk.MenuItem(_('Download...'))
        download_item.connect('activate', self.on_download_activated)
        menu.append(download_item)
        share_item = Gtk.MenuItem(_('Share...'))
        share_item.connect('activate', self.on_share_activated)
        menu.append(share_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        moveto_item = Gtk.MenuItem(_('Move To...'))
        moveto_item.connect('activate', self.on_moveto_activated)
        menu.append(moveto_item)
        copyto_item = Gtk.MenuItem(_('Copy To...'))
        copyto_item.connect('activate', self.on_copyto_activated)
        menu.append(copyto_item)
        rename_item = Gtk.MenuItem(_('Rename...'))
        rename_item.connect('activate', self.on_rename_activated)
        menu.append(rename_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        trash_item = Gtk.MenuItem(_('Move to Trash'))
        trash_item.connect('activate', self.on_trash_activated)
        menu.append(trash_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        props_item = Gtk.MenuItem(_('Properties'))
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
            print('Unknown file type')

    def launch_app_with_app_info(self, app_info):
        def open_video_link(resp, error=None):
            if error:
                return
            red_url, req_id = resp
            app_info.launch_uris([red_url, ], None)

        print('open with ', app_info.get_display_name())
        # first, download this to load dir
        # then open it with app_info
        tree_paths = self.iconview.get_selected_items()
        if len(tree_paths) != 1:
            print('Please open one file at a time!')
            return
        tree_path = tree_paths[0]
        file_type = self.liststore[tree_path][TYPE_COL]
        indices = tree_path.get_indices()
        if not indices:
            return
        index = tree_path.get_indices()[0]
        pcs_file = self.filelist[index]
        # 'media' 对应于rmvb格式.
        if 'video' in file_type or 'media' in file_type:
            gutil.async_call(
                    pcs.get_download_link, self.app.cookie,
                    pcs_file['dlink'], callback=open_video_link)
        else:
            print('will download this link and launch app')
            self.app.download_page.add_launch_task(pcs_file, app_info)

    # item popup menu
    def on_launch_app_activated(self, menu_item, app_info):
        self.launch_app_with_app_info(app_info)

    def on_choose_app_activated(self, menu_item):
        print('choose app')

    def on_open_dir_item_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if tree_paths and len(tree_paths) == 1:
            self.parent.load(self.liststore[tree_paths][PATH_COL])

    def on_copy_link_activated(self, menu_item):
        def copy_link_to_clipboard(res, error=None):
            if error:
                return
            red_url, req_id = res
            print('will copy link to clipboard:', red_url)
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(red_url, -1)

        tree_paths = self.iconview.get_selected_items()
        if len(tree_paths) != 1:
            return
        tree_path = tree_paths[0]
        index = tree_path.get_indices()[0]
        pcs_file = self.filelist[index]
        gutil.async_call(
                pcs.get_download_link, self.app.cookie, pcs_file['dlink'],
                callback=copy_link_to_clipboard)

    def on_download_activated(self, menu_item):
        # 下载文件与下载目录的操作是不相同的.
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        for tree_path in tree_paths:
            pcs_file = self.filelist[tree_path.get_indices()[0]]
            self.app.download_page.add_task(pcs_file)

    def on_share_activated(self, menu_item):
        print('share activated')

    def on_moveto_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if len(tree_paths) == 0:
            return

        dialog = FolderBrowserDialog(self.parent, self.app, _('Move to..'))
        response = dialog.run()
        targ_path = ''
        if response == Gtk.ResponseType.OK:
            targ_path = dialog.get_path()
        dialog.destroy()
        if not targ_path:
            return

        filelist = []
        for tree_path in tree_paths:
            filelist.append({
                'path': self.liststore[tree_path][PATH_COL],
                'dest': targ_path,
                'newname': self.liststore[tree_path][DISNAME_COL],
                })
        gutil.async_call(
                pcs.move,
                self.app.cookie, self.app.tokens, filelist,
                callback=self.parent.reload)

    def on_copyto_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if len(tree_paths) == 0:
            return

        dialog = FolderBrowserDialog(self.parent, self.app, _('Copy to..'))
        response = dialog.run()
        targ_path = ''
        if response == Gtk.ResponseType.OK:
            targ_path = dialog.get_path()
        dialog.destroy()
        if not targ_path:
            return

        filelist = []
        for tree_path in tree_paths:
            filelist.append({
                'path': self.liststore[tree_path][PATH_COL],
                'dest': targ_path,
                'newname': self.liststore[tree_path][DISNAME_COL],
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

    def on_props_activated(self, menu_item):
        '''显示选中的文件或者当前目录的属性'''
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        for tree_path in tree_paths:
            index = tree_path.get_indices()[0]
            pcs_file = self.filelist[index]
            dialog = PropertiesDialog(self.parent, self.app, pcs_file)
            dialog.run()
            dialog.destroy()
