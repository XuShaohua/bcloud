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
from TrashPage import TrashPage
from UploadPage import UploadPage
from VideoPage import VideoPage

GObject.threads_init()
DBUS_APP_NAME = 'org.liulang.gcloud'

class App:

    def __init__(self):
        self.app = Gtk.Application.new(DBUS_APP_NAME, 0)
        self.app.connect('startup', self.on_app_startup)
        self.app.connect('activate', self.on_app_activate)
        self.app.connect('shutdown', self.on_app_shutdown)

        self.icon_theme = Gtk.IconTheme.new()
        #self.icon_theme.append_search_path(Config.ICON_PATH)

    def on_app_startup(self, app):
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
        nav_window.add(nav_treeview)

        self.notebook = Gtk.Notebook()
        paned.add2(self.notebook)

        self.init_notebook()
        self.notebook.connect('switch-page', self.on_notebook_switched)
        self.init_status_icon()

    def on_app_activate(self, app):
        self.window.show_all()

    def on_app_shutdown(self, app):
        '''Dump profile content to disk'''
        pass

    def run(self, argv):
        self.app.run(argv)

    def quit(self):
        self.window.destroy()
        self.app.quit()

    def on_main_window_resized(self, window):
        pass

    def on_main_window_deleted(self, window, event):
        pass

    def init_notebook(self):
        app = self.app
        self.pages = [
            HomePage(app),
            PicturePage(app),
            DocPage(app),
            VideoPage(app),
            BTPage(app),
            MusicPage(app),
            OtherPage(app),
            SharePage(app),
            InboxPage(app),
            TrashPage(app),
            CloudPage(app),
            DownloadPage(app),
            UploadPage(app),
            ]
        for page in self.pages:
            page.page_num = self.notebook.append_page(
                    page, Gtk.Label(page.disname))
            self.nav_liststore.append([
                page.icon_name, page.disname, page.tooltip])

    def on_notebook_switched(self, notebook, page, page_num):
        pass

    def init_status_icon(self):
        pass
