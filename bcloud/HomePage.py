
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gdk
from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud.IconWindow import IconWindow
from bcloud import gutil
from bcloud import pcs
from bcloud import util

class PathBox(Gtk.Box):

    def __init__(self, parent):
        super().__init__(spacing=0)
        self.parent = parent
        
    def clear_buttons(self):
        buttons = self.get_children()
        for button in buttons:
            self.remove(button)

    def append_button(self, abspath, name):
        button = Gtk.Button.new_with_label(gutil.ellipse_text(name))
        button.abspath = abspath
        button.set_tooltip_text(name)
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

    icon_name = 'home-symbolic'
    disname = _('Home')
    tooltip = _('Show all of your files on Cloud')
    first_run = False
    page_num = 1
    path = '/'
    has_next = True

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        # set drop action
        targets = [
            ['text/plain', Gtk.TargetFlags.OTHER_APP, 0],
            ['*.*', Gtk.TargetFlags.OTHER_APP, 1]]
        target_list =[Gtk.TargetEntry.new(*t) for t in targets]
        self.drag_dest_set(
            Gtk.DestDefaults.ALL, target_list, Gdk.DragAction.COPY)

        nav_bar = Gtk.Toolbar()
        nav_bar.get_style_context().add_class(Gtk.STYLE_CLASS_MENUBAR)
        nav_bar.props.show_arrow = False
        nav_bar.props.toolbar_style = Gtk.ToolbarStyle.ICONS
        nav_bar.props.icon_size = Gtk.IconSize.BUTTON
        self.pack_start(nav_bar, False, False, 0)
        nav_bar.props.valign = Gtk.Align.START

        path_item = Gtk.ToolItem()
        nav_bar.insert(path_item, 0)
        nav_bar.child_set_property(path_item, 'expand', True)
        path_item.props.valign = Gtk.Align.START
        path_win = Gtk.ScrolledWindow()
        path_item.add(path_win)
        path_win.props.valign = Gtk.Align.START
        path_win.props.vscrollbar_policy = Gtk.PolicyType.NEVER
        path_viewport = Gtk.Viewport()
        path_viewport.props.valign = Gtk.Align.START
        path_win.add(path_viewport)
        self.path_box = PathBox(self)
        self.path_box.props.valign = Gtk.Align.START
        path_viewport.add(self.path_box)

        # search button
        search_button = Gtk.ToggleToolButton()
        search_button.set_label(_('Search'))
        search_button.set_icon_name('search-symbolic')
        search_button.set_tooltip_text(
                _('Search documents and folders by name'))
        search_button.connect('toggled', self.on_search_button_toggled)
        nav_bar.insert(search_button, 1)
        search_button.props.valign = Gtk.Align.START

        if Config.GTK_LE_36:
            self.search_entry = Gtk.Entry()
            self.search_entry.set_icon_from_icon_name(
                    Gtk.EntryIconPosition.PRIMARY,
                    'folder-saved-search-symbolic')
        else:
            self.search_entry = Gtk.SearchEntry()
        self.search_entry.props.no_show_all = True
        self.search_entry.props.visible = False
        self.search_entry.connect(
                'activate', self.on_search_entry_activated)
        self.pack_start(self.search_entry, False, False, 0)

        self.icon_window = IconWindow(self, app)
        self.pack_end(self.icon_window, True, True, 0)

    def do_drag_data_received(self, drag_context, x, y, data, info, time):
        uri = data.get_text()
        if uri and uri.startswith('file://'):
            source_path = uri[7:].rstrip()
            if self.app.profile:
                self.app.upload_page.add_file_task(source_path, self.path)

    # Open API
    def load(self, path='/'):
        def on_load(info, error=None):
            if error or not info or info['errno'] != 0:
                return
            self.icon_window.load(info['list'])

        self.path = path
        self.page_num = 1
        self.has_next = True
        self.path_box.set_path(path)
        gutil.async_call(
                pcs.list_dir, self.app.cookie, self.app.tokens, self.path,
                self.page_num, callback=on_load)
        gutil.async_call(
                pcs.get_quota, self.app.cookie, self.app.tokens,
                callback=self.app.update_quota)

    def load_next(self):
        '''载入下一页'''
        def on_load_next(info, error=None):
            if error or not info or info['errno'] != 0:
                return
            if info['list']:
                self.icon_window.load_next(info['list'])
            else:
                self.has_next = False

        if not self.has_next:
            return
        self.page_num = self.page_num + 1
        self.path_box.set_path(self.path)
        gutil.async_call(
                pcs.list_dir, self.app.cookie, self.app.tokens, self.path,
                self.page_num, callback=on_load_next)

    def reload(self, *args, **kwds):
        '''重新载入本页面'''
        self.load(self.path)

    def on_search_button_toggled(self, search_button):
        status = search_button.get_active()
        self.search_entry.props.visible = status
        if status:
            self.search_entry.grab_focus()
        else:
            self.reload()

    def on_search_entry_activated(self, search_entry):
        text = search_entry.get_text()
        if not text:
            return
        gutil.async_call(
                pcs.search, self.app.cookie, self.app.tokens, text,
                self.path, callback=self.icon_window.load)
