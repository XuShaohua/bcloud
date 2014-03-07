
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gtk

from gcloud import Config
_ = Config._
from gcloud.IconWindow import IconWindow
from gcloud import gutil
from gcloud import pcs
from gcloud import util

class PathBox(Gtk.Box):

    def __init__(self, parent):
        super().__init__(spacing=0)
        self.parent = parent
        
    def clear_buttons(self):
        buttons = self.get_children()
        for button in buttons:
            self.remove(button)

    def append_button(self, abspath, name):
        button = Gtk.Button(name)
        button.abspath = abspath
        self.pack_start(button, False, False, 0)
        button.connect('clicked', self.on_button_clicked)

    def on_button_clicked(self, button):
        self.parent.load(button.abspath)

    def set_path(self, path):
        self.clear_buttons()
        pathlist = util.rec_split_path(path)
        for (abspath, name) in pathlist:
            self.append_button(abspath, name)
        self.show_all()


class HomePage(Gtk.Box):

    icon_name = 'go-home-symbolic'
    disname = _('Home')
    tooltip = _('Show all of your files on Cloud')
    page_num = 1
    path = '/'
    has_next = False

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        nav_bar = Gtk.Toolbar()
        nav_bar.get_style_context().add_class(Gtk.STYLE_CLASS_MENUBAR)
        nav_bar.props.show_arrow = False
        nav_bar.props.toolbar_style = Gtk.ToolbarStyle.ICONS
        nav_bar.props.icon_size = Gtk.IconSize.BUTTON
        self.pack_start(nav_bar, False, False, 0)

        path_item = Gtk.ToolItem()
        nav_bar.insert(path_item, 0)
        nav_bar.child_set_property(path_item, 'expand', True)
        self.path_box = PathBox(self)
        path_item.add(self.path_box)

        # search button
        search_button = Gtk.ToggleToolButton('Search')
        search_button.set_icon_name('folder-saved-search-symbolic')
        search_button.set_tooltip_text(
                _('Search documents and folders by name'))
        search_button.connect('toggled', self.on_search_button_toggled)
        nav_bar.insert(search_button, 1)

        if Config.GTK_LE_36:
            self.search_entry = Gtk.Entry()
            self.search_entry.set_icon_from_icon_name(
                    Gtk.EntryIconPosition.PRIMARY,
                    'folder-saved-search-symbolic')
        else:
            self.search_entry = Gtk.SearchEntry()
        self.search_entry.props.no_show_all = True
        self.search_entry.props.visible = False
        self.pack_start(self.search_entry, False, False, 0)

        self.icon_window = IconWindow(self, app)
        self.pack_end(self.icon_window, True, True, 0)

    def init(self):
        self.load(self.path)

    def load(self, path):
        self.path = path
        self.page_num = 1
        self.has_next = False
        self.path_box.set_path(path)
        gutil.async_call(
                pcs.list_dir, self.app.cookie, self.app.tokens, self.path,
                callback=self.icon_window.load)

    def load_next(self):
        '''载入下一页'''
        self.page_num = self.page_num + 1
        self.path_box.set_path(self.path)
        self.icon_window.load(self.path)
        gutil.async_call(
                pcs.list_dir, self.app.cookie, self.app.tokens, self.path,
                callback=self.icon_window.load_next)

    def reload(self):
        '''重新载入本页面'''
        self.load(self.path)

    def on_search_button_toggled(self, search_button):
        status = search_button.get_active()
        self.search_entry.props.visible = status
        if status:
            self.search_entry.grab_focus()
        else:
            self.reload()
