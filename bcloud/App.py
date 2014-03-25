# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os
import random
import sys
sys.path.insert(0, os.path.dirname(__file__))
import time

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

import Config
Config.check_first()
_ = Config._
import util
from MimeProvider import MimeProvider
from PreferencesDialog import PreferencesDialog

from CategoryPage import *
from CloudPage import CloudPage
from DownloadPage import DownloadPage
from HomePage import HomePage
from InboxPage import InboxPage
from PreferencesDialog import PreferencesDialog
from SharePage import SharePage
from SigninDialog import SigninDialog
from TrashPage import TrashPage
from UploadPage import UploadPage

if Gtk.MAJOR_VERSION <= 3 and Gtk.MINOR_VERSION < 10:
    GObject.threads_init()
DBUS_APP_NAME = 'org.liulang.bcloud'
(ICON_COL, NAME_COL, TOOLTIP_COL, COLOR_COL) = list(range(4))
BLINK_DELTA = 250    # 字体闪烁间隔, 250 miliseconds 
BLINK_SUSTAINED = 3  # 字体闪烁持续时间, 5 seconds

class App:

    profile = None
    cookie = None
    tokens = None
    default_color = Gdk.RGBA(0.9, 0.9, 0.9, 1)

    def __init__(self):
        self.app = Gtk.Application.new(DBUS_APP_NAME, 0)
        self.app.connect('startup', self.on_app_startup)
        self.app.connect('activate', self.on_app_activate)
        self.app.connect('shutdown', self.on_app_shutdown)

    def on_app_startup(self, app):
        self.icon_theme = Gtk.IconTheme.get_default()
        #self.icon_theme.append_search_path(Config.ICON_PATH)
        self.mime = MimeProvider(self)
        self.color_schema = Config.load_color_schema()

        self.window = Gtk.ApplicationWindow.new(application=app)
        self.window.set_default_size(*Config._default_profile['window-size'])
        self.window.set_title(Config.APPNAME)
        self.window.props.hide_titlebar_when_maximized = True
        self.window.set_icon_name(Config.NAME)
        self.window.connect('check-resize', self.on_main_window_resized)
        self.window.connect('delete-event', self.on_main_window_deleted)
        app.add_window(self.window)

        app_menu = Gio.Menu.new()
        app_menu.append(_('Preferences'), 'app.preferences')
        app_menu.append(_('Sign out'), 'app.signout')
        app_menu.append(_('About'), 'app.about')
        app_menu.append(_('Quit'), 'app.quit')
        app.set_app_menu(app_menu)

        preferences_action = Gio.SimpleAction.new('preferences', None)
        preferences_action.connect(
                'activate', self.on_preferences_action_activated)
        app.add_action(preferences_action)
        signout_action = Gio.SimpleAction.new('signout', None)
        signout_action.connect('activate', self.on_signout_action_activated)
        app.add_action(signout_action)
        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self.on_about_action_activated)
        app.add_action(about_action)
        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', self.on_quit_action_activated)
        app.add_action(quit_action)

        paned = Gtk.Paned()
        self.window.add(paned)

        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        paned.add1(left_box)

        nav_window = Gtk.ScrolledWindow()
        nav_window.props.hscrollbar_policy = Gtk.PolicyType.NEVER
        #nav_window.props.border_width = 5
        left_box.pack_start(nav_window, True, True, 0)

        # icon_name, disname, tooltip, color
        self.nav_liststore = Gtk.ListStore(str, str, str, Gdk.RGBA)
        nav_treeview = Gtk.TreeView(model=self.nav_liststore)
        self.nav_selection = nav_treeview.get_selection()
        nav_treeview.props.headers_visible = False
        nav_treeview.set_tooltip_column(TOOLTIP_COL)
        icon_cell = Gtk.CellRendererPixbuf()
        name_cell = Gtk.CellRendererText()
        nav_col = Gtk.TreeViewColumn.new()
        nav_col.set_title('Places')
        nav_col.pack_start(icon_cell, False)
        nav_col.pack_start(name_cell, True)
        nav_col.set_attributes(icon_cell, icon_name=ICON_COL)
        nav_col.set_attributes(
            name_cell, text=NAME_COL, foreground_rgba=COLOR_COL)
        nav_treeview.append_column(nav_col)
        nav_selection = nav_treeview.get_selection()
        nav_selection.connect('changed', self.on_nav_selection_changed)
        nav_window.add(nav_treeview)

        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_show_text(True)
        self.progressbar.set_text(_('Unknown'))
        left_box.pack_end(self.progressbar, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.props.show_tabs = False
        paned.add2(self.notebook)

    def on_app_activate(self, app):
        self.window.show_all()
        self.show_signin_dialog()

    def on_app_shutdown(self, app):
        '''Dump profile content to disk'''
        if self.profile:
            Config.dump_profile(self.profile)

    def run(self, argv):
        self.app.run(argv)

    def quit(self):
        self.app.quit()

    def show_signin_dialog(self, auto_signin=True):
        self.profile = None
        signin = SigninDialog(self, auto_signin=auto_signin)
        signin.run()
        signin.destroy()

        if self.profile:
            self.init_notebook()
            self.notebook.connect('switch-page', self.on_notebook_switched)
            self.init_status_icon()

            if self.profile['first-run']:
                self.profile['first-run'] = False
                preferences = PreferencesDialog(self)
                preferences.run()
                preferences.destroy()

            self.home_page.load()
        else:
            self.quit()

    def on_main_window_resized(self, window):
        if self.profile:
            self.profile['window-size'] = window.get_size()

    def on_main_window_deleted(self, window, event):
        print('on main window deleted')
        # TODO: minimize to sys tray
        #return False

    def on_preferences_action_activated(self, action, params):
        dialog = PreferencesDialog(self)
        dialog.run()
        dialog.destroy()
        if self.profile:
            Config.dump_profile(self.profile)

    def on_signout_action_activated(self, action, params):
        if self.profile:
            self.show_signin_dialog(auto_signin=False)

    def on_about_action_activated(self, action, params):
        dialog = Gtk.AboutDialog()
        dialog.set_modal(True)
        dialog.set_transient_for(self.window)
        dialog.set_program_name(Config.APPNAME)
        dialog.set_logo_icon_name(Config.NAME)
        dialog.set_version(Config.VERSION)
        dialog.set_comments(Config.DESCRIPTION)
        dialog.set_copyright(Config.COPYRIGHT)
        dialog.set_website(Config.HOMEPAGE)
        dialog.set_license_type(Gtk.License.GPL_3_0)
        dialog.set_authors(Config.AUTHORS)
        dialog.run()
        dialog.destroy()

    def on_quit_action_activated(self, action, params):
        self.quit()

    def update_quota(self, quota_info, error=None):
        '''更新网盘容量信息'''
        if not quota_info or quota_info['errno'] != 0:
            return
        used = quota_info['used']
        total = quota_info['total']
        used_size, _ = util.get_human_size(used)
        total_size, _ = util.get_human_size(total)
        self.progressbar.set_text(used_size + ' / ' + total_size)
        self.progressbar.set_fraction(used / total)

    def init_notebook(self):
        pages = []
        self.home_page = HomePage(self)
        pages.append(self.home_page)
        self.picture_page = PicturePage(self)
        pages.append(self.picture_page)
        self.doc_page = DocPage(self)
        pages.append(self.doc_page)
        self.video_page = VideoPage(self)
        pages.append(self.video_page)
        self.bt_page = BTPage(self)
        pages.append(self.bt_page)
        self.music_page = MusicPage(self)
        pages.append(self.music_page)
        self.other_page = OtherPage(self)
        pages.append(self.other_page)
        self.share_page = SharePage(self)
        pages.append(self.share_page)
        self.inbox_page = InboxPage(self)
        pages.append(self.inbox_page)
        self.trash_page = TrashPage(self)
        pages.append(self.trash_page)
        self.cloud_page = CloudPage(self)
        pages.append(self.cloud_page)
        self.download_page = DownloadPage(self)
        pages.append(self.download_page)
        self.upload_page = UploadPage(self)
        pages.append(self.upload_page)

        self.default_color = self.get_default_color()
        self.nav_liststore.clear()

        for page in pages:
            self.notebook.append_page(page, Gtk.Label.new(page.disname))
            self.nav_liststore.append([
                page.icon_name, page.disname,
                page.tooltip, self.default_color,
                ])
        self.notebook.show_all()

    def reload_current_page(self, *args, **kwds):
        '''重新载入当前页面.
        
        所有的页面都应该实现reload()方法.
        '''
        index = self.notebook.get_current_page()
        self.notebook.get_nth_page(index).reload()

    def switch_page_by_index(self, index):
        self.notebook.set_current_page(index)

    def switch_page(self, page):
        for index, p in enumerate(self.notebook):
            if p == page:
                self.nav_selection.select_iter(self.nav_liststore[index].iter)
                #self.notebook.set_current_page(index)
                break

    def on_notebook_switched(self, notebook, page, index):
        if page.first_run:
            page.load()
            page.first_run = False

    def on_nav_selection_changed(self, nav_selection):
        model, iter_ = nav_selection.get_selected()
        if not iter_:
            return
        path = model.get_path(iter_)
        index = path.get_indices()[0]
        self.switch_page_by_index(index)

    def init_status_icon(self):
        pass

    def blink_page(self, page):
        def blink():
            row[COLOR_COL] = random.choice(self.color_schema)
            if time.time() - start_time > BLINK_SUSTAINED:
                row[COLOR_COL] = self.default_color
                return False
            return True
        
        start_time = time.time()
        for index, p in enumerate(self.notebook):
            if p == page:
                break
        row = self.nav_liststore[index]
        GLib.timeout_add(BLINK_DELTA, blink)

    def get_default_color(self):
        context = self.window.get_style_context()
        return context.get_color(Gtk.StateFlags.NORMAL)
