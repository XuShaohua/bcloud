# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gtk

import Config
Config.check_first()
_ = Config._
from MimeProvider import MimeProvider
from PreferencesDialog import PreferencesDialog

from BTPage import BTPage
from CloudPage import CloudPage
from DownloadPage import DownloadPage
from DocPage import DocPage
from HomePage import HomePage
from InboxPage import InboxPage
from MusicPage import MusicPage
from OtherPage import OtherPage
from PicturePage import PicturePage
from SharePage import SharePage
from SigninDialog import SigninDialog
from TrashPage import TrashPage
from UploadPage import UploadPage
from VideoPage import VideoPage

GObject.threads_init()
DBUS_APP_NAME = 'org.liulang.gcloud'

class App:

    profile = None
    cookie = None
    tokens = None

    def __init__(self):
        self.app = Gtk.Application.new(DBUS_APP_NAME, 0)
        self.app.connect('startup', self.on_app_startup)
        self.app.connect('activate', self.on_app_activate)
        self.app.connect('shutdown', self.on_app_shutdown)

    def on_app_startup(self, app):
        self.icon_theme = Gtk.IconTheme.new()
        #self.icon_theme.append_search_path(Config.ICON_PATH)
        self.mime = MimeProvider(self)

        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_default_size(*Config._default_profile['window-size'])
        self.window.set_title(Config.APPNAME)
        self.window.props.hide_titlebar_when_maximized = True
        # self.window.set_icon_name()
        self.window.connect('check-resize', self.on_main_window_resized)
        self.window.connect('delete-event', self.on_main_window_deleted)
        app.add_window(self.window)

        paned = Gtk.Paned()
        self.window.add(paned)

        nav_window = Gtk.ScrolledWindow()
        nav_window.props.hscrollbar_policy = Gtk.PolicyType.NEVER
        #nav_window.props.border_width = 5
        paned.add1(nav_window)

        # icon_name, disname, tooltip
        self.nav_liststore = Gtk.ListStore(str, str, str)
        nav_treeview = Gtk.TreeView(model=self.nav_liststore)
        nav_treeview.props.headers_visible = False
        nav_treeview.set_tooltip_column(2)
        pix_cell = Gtk.CellRendererPixbuf()
        name_cell = Gtk.CellRendererText()
        nav_col = Gtk.TreeViewColumn.new()
        nav_col.set_title('Places')
        nav_col.pack_start(pix_cell, False)
        nav_col.pack_start(name_cell, True)
        nav_col.set_attributes(pix_cell, icon_name=0)
        nav_col.set_attributes(name_cell, text=1)
        nav_treeview.append_column(nav_col)
        nav_selection = nav_treeview.get_selection()
        nav_selection.connect('changed', self.on_nav_selection_changed)
        nav_window.add(nav_treeview)

        self.notebook = Gtk.Notebook()
        self.notebook.props.show_tabs = False
        paned.add2(self.notebook)

        self.init_notebook()
        self.notebook.connect('switch-page', self.on_notebook_switched)
        self.init_status_icon()

    def on_app_activate(self, app):
        print('on_app_activate')
        self.window.show_all()
        signin = SigninDialog(self)
        signin.run()
        signin.destroy()

        if self.profile and self.profile['first-run']:
            self.profile['first-run'] = False
            preferences = PreferencesDialog(self)
            preferences.run()
            preferences.destroy()

        if self.tokens and self.cookie:
            self.switch_page_by_name('Home')
            page = self.get_page_by_name('Home')
            self.get_page_by_name('Home').init()

    def on_app_shutdown(self, app):
        '''Dump profile content to disk'''
        if self.profile:
            Config.dump_profile(self.profile)

    def run(self, argv):
        self.app.run(argv)

    def quit(self):
        self.window.destroy()
        self.app.quit()

    def on_main_window_resized(self, window):
        if self.profile:
            self.profile['window-size'] = window.get_size()

    def on_main_window_deleted(self, window, event):
        pass

    def init_notebook(self):
        self.page_names = (
            'Home', 'Picture', 'Doc', 'Video', 'BT', 'Music', 'Other',
            'Share', 'Inbox', 'Trash', 'Cloud', 'Download', 'Upload',
            )
        self.pages = (
            HomePage(self),
            PicturePage(self),
            DocPage(self),
            VideoPage(self),
            BTPage(self),
            MusicPage(self),
            OtherPage(self),
            SharePage(self),
            InboxPage(self),
            TrashPage(self),
            CloudPage(self),
            DownloadPage(self),
            UploadPage(self),
            )
        for page in self.pages:
            page.page_num = self.notebook.append_page(
                    page, Gtk.Label(page.disname))
            self.nav_liststore.append([
                page.icon_name, page.disname, page.tooltip])

    def get_page_by_name(self, name):
        index = self.page_names.index(name)
        return self.pages[index]

    def reload_current_page(self, *args, **kwds):
        '''重新载入当前页面.
        
        所有的页面都应该实现reload()方法.
        '''
        index = self.notebook.get_current_page()
        self.pages[index].reload()

    def switch_page_by_name(self, name):
        index = self.page_names.index(name)
        self.switch_page_by_index(index)

    def switch_page_by_index(self, index):
        self.notebook.set_current_page(index)

    def on_notebook_switched(self, notebook, page, num):
        pass

    def on_nav_selection_changed(self, nav_selection):
        model, iter_ = nav_selection.get_selected()
        path = model.get_path(iter_)
        index = path.get_indices()[0]
        self.switch_page_by_index(index)

    def init_status_icon(self):
        pass
