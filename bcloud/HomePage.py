
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import traceback

from gi.repository import Gdk
from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud import const
from bcloud.const import TargetInfo, TargetType
from bcloud.IconWindow import IconWindow
from bcloud.IconWindow import TreeWindow
from bcloud import gutil
from bcloud.log import logger
from bcloud import pcs
from bcloud import util


# 用于处理拖放上传
DROP_TARGETS = (
    (TargetType.URI_LIST, Gtk.TargetFlags.OTHER_APP, TargetInfo.URI_LIST),
)
DROP_TARGET_LIST = [Gtk.TargetEntry.new(*t) for t in DROP_TARGETS]


class PathBox(Gtk.Box):
    '''路径栏'''

    MOUSE_BACK_BUTTON = 8
    MOUSE_FORWARD_BUTTON = 9

    def __init__(self, parent):
        super().__init__(spacing=10)
        self.parent = parent

        self.view_history = list()
        self.view_history_pos = -1
        self.back_button, self.forward_button = self.init_history_navigate()

        self.path_box = Gtk.Box()
        self.path_box.get_style_context().add_class(Gtk.STYLE_CLASS_RAISED)
        self.path_box.get_style_context().add_class(Gtk.STYLE_CLASS_LINKED)
        self.pack_start(self.path_box, False, False, 0)

    def init_history_navigate(self):
        navigate_box = Gtk.Box()
        navigate_box.get_style_context().add_class(Gtk.STYLE_CLASS_RAISED)
        navigate_box.get_style_context().add_class(Gtk.STYLE_CLASS_LINKED)
        self.pack_start(navigate_box, False, False, 0)

        back_button = Gtk.Button()
        back_img = Gtk.Image.new_from_icon_name('go-previous-symbolic',
                                                Gtk.IconSize.SMALL_TOOLBAR)
        back_button.set_image(back_img)
        back_button.set_tooltip_text(_('Back'))
        back_button.set_can_focus(False)
        back_button.connect('clicked', self.on_back_button_clicked)
        navigate_box.pack_start(back_button, False, False, 0)

        forward_button = Gtk.Button()
        forward_img = Gtk.Image.new_from_icon_name('go-next-symbolic',
                                                   Gtk.IconSize.SMALL_TOOLBAR)
        forward_button.set_image(forward_img)
        forward_button.set_tooltip_text(_('Forward'))
        forward_button.set_can_focus(False)
        forward_button.connect('clicked', self.on_forward_button_clicked)
        navigate_box.pack_start(forward_button, False, False, 0)

        # listen mouse button events
        self.parent.connect('button-press-event', self.on_button_press)

        return back_button, forward_button

    def on_back_button_clicked(self, button):
        self.history_navigate(True)

    def on_forward_button_clicked(self, button):
        self.history_navigate(False)

    def clear_buttons(self):
        buttons = self.path_box.get_children()
        for button in buttons:
            self.path_box.remove(button)

    def append_button(self, abspath, name):
        button = Gtk.Button()
        button.abspath = abspath
        button.set_tooltip_text(name)

        if abspath == '/':
            home_img = Gtk.Image.new_from_icon_name('user-home-symbolic',
                                                    Gtk.IconSize.SMALL_TOOLBAR)
            button.set_image(home_img)
        else:
            button.set_label(gutil.ellipse_text(name))

        if not Config.GTK_GE_312:
            button.set_size_request(32, -1)

        self.path_box.pack_start(button, False, False, 0)
        button.connect('clicked', self.on_button_clicked)

    def on_button_clicked(self, button):
        self.parent.load(button.abspath, is_user=True)

    def on_button_press(self, window, event):
        if event.button == self.MOUSE_BACK_BUTTON:
            self.history_navigate(True)
        elif event.button == self.MOUSE_FORWARD_BUTTON:
            self.history_navigate(False)
        else:
            return

    def history_navigate(self, is_back):
        path = self.get_history_path(is_back)

        if path:
            self.parent.load(path)

    def add_view_history(self, abs_path):
        logger.debug("add view history: %s", abs_path)
        self.view_history = self.view_history[:self.view_history_pos + 1]
        self.view_history.append(abs_path)
        self.view_history_pos += 1

    def get_history_path(self, is_back):
        length = len(self.view_history)
        if is_back:
            pos = self.view_history_pos -1
        else:
            pos = self.view_history_pos + 1
        if pos not in range(length):
            return None
        path = self.view_history[pos]
        self.view_history_pos = pos
        return path

    def can_back(self):
        return self.view_history_pos > 0

    def can_forward(self):
        return self.view_history_pos < (len(self.view_history) - 1)

    def set_path(self, path, is_user=False):
        """
        :param bool is_user: this event was fired by user
        """
        self.clear_buttons()
        pathlist = util.rec_split_path(path)
        for (abspath, name) in pathlist:
            self.append_button(abspath, name)

        if is_user:
            self.add_view_history(path)

        self.back_button.set_sensitive(self.can_back())
        self.forward_button.set_sensitive(self.can_forward())

        self.show_all()


class HomePage(Gtk.Box):

    icon_name = 'user-home-symbolic'
    disname = _('Home')
    name = 'HomePage'
    tooltip = _('List all of your files')
    first_run = False
    page_num = 1
    path = '/'
    has_next = True

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        self.drag_dest_set(Gtk.DestDefaults.ALL, DROP_TARGET_LIST,
                           Gdk.DragAction.COPY)

        if Config.GTK_GE_312:
            self.headerbar = Gtk.HeaderBar()
            self.headerbar.props.show_close_button = True
            self.headerbar.props.has_subtitle = False

            path_win = Gtk.ScrolledWindow()
            self.headerbar.pack_start(path_win)
            # FIXME: add arrows in both sides
            path_win.props.hscrollbar_policy = Gtk.PolicyType.NEVER
            path_win.props.vscrollbar_policy = Gtk.PolicyType.NEVER
            path_viewport = Gtk.Viewport()
            path_win.add(path_viewport)
            self.path_box = PathBox(self)
            path_viewport.add(self.path_box)

            # right box
            right_box = Gtk.Box()
            right_box_context = right_box.get_style_context()
            right_box_context.add_class(Gtk.STYLE_CLASS_RAISED)
            right_box_context.add_class(Gtk.STYLE_CLASS_LINKED)
            self.headerbar.pack_end(right_box)

            # toggle view mode
            list_view_button = Gtk.RadioButton()
            list_view_button.set_mode(False)
            list_view_img = Gtk.Image.new_from_icon_name('view-list-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            list_view_button.set_image(list_view_img)
            right_box.pack_start(list_view_button, False, False, 0)

            grid_view_button = Gtk.RadioButton()
            grid_view_button.set_mode(False)
            grid_view_button.join_group(list_view_button)
            grid_view_button.set_active(
                    self.app.profile['view-mode'][self.name] == const.ICON_VIEW)
            grid_view_img = Gtk.Image.new_from_icon_name('view-grid-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            grid_view_button.set_image(grid_view_img)
            list_view_button.connect('clicked',
                                     self.on_list_view_button_clicked)
            grid_view_button.connect('clicked',
                                     self.on_grid_view_button_clicked)
            right_box.pack_start(grid_view_button, False, False, 0)

            # reload button
            reload_button = Gtk.Button()
            reload_img = Gtk.Image.new_from_icon_name('view-refresh-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            reload_button.set_image(reload_img)
            reload_button.set_tooltip_text(_('Reload (F5)'))
            reload_button.connect('clicked', self.reload)
            self.headerbar.pack_end(reload_button)

            # search button
            search_button = Gtk.ToggleButton()
            search_img = Gtk.Image.new_from_icon_name('edit-find-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            search_button.set_image(search_img)
            search_button.set_tooltip_text(
                    _('Search documents and folders by name'))
            search_button.connect('toggled', self.on_search_button_toggled)
            self.headerbar.pack_end(search_button)

            # show loading process
            self.loading_spin = Gtk.Spinner()
            self.loading_spin.props.valign = Gtk.Align.CENTER
            self.headerbar.pack_end(self.loading_spin)

            self.search_entry = Gtk.SearchEntry()
            self.search_entry.set_icon_from_icon_name(
                    Gtk.EntryIconPosition.PRIMARY, 'edit-find-symbolic')
            self.search_entry.props.no_show_all = True
            self.search_entry.props.visible = False
            self.search_entry.connect('activate',
                                      self.on_search_entry_activated)
            self.pack_start(self.search_entry, False, False, 0)
        else:
            nav_bar = Gtk.Box(spacing=5)
            self.pack_start(nav_bar, False, False, 0)

            path_win = Gtk.ScrolledWindow()
            nav_bar.pack_start(path_win, True, True, 0)
            path_win.props.hscrollbar_policy = Gtk.PolicyType.NEVER
            path_win.props.vscrollbar_policy = Gtk.PolicyType.NEVER
            path_viewport = Gtk.Viewport()
            path_win.add(path_viewport)
            self.path_box = PathBox(self)
            path_viewport.add(self.path_box)

            # show loading process
            self.loading_spin = Gtk.Spinner()
            self.loading_spin.props.valign = Gtk.Align.CENTER
            nav_bar.pack_start(self.loading_spin, False, False, 0)

            # search button
            search_button = Gtk.ToggleButton()
            search_img = Gtk.Image.new_from_icon_name('edit-find-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            search_button.set_image(search_img)
            search_button.set_tooltip_text(
                    _('Search documents and folders by name'))
            search_button.connect('toggled', self.on_search_button_toggled)
            nav_bar.pack_start(search_button, False, False, 0)

            # right box
            right_box = Gtk.Box()
            right_box_context = right_box.get_style_context()
            right_box_context.add_class(Gtk.STYLE_CLASS_RAISED)
            right_box_context.add_class(Gtk.STYLE_CLASS_LINKED)
            nav_bar.pack_start(right_box, False, False, 0)

            # toggle view mode
            list_view_button = Gtk.RadioButton()
            list_view_button.set_mode(False)
            list_view_img = Gtk.Image.new_from_icon_name('view-list-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            list_view_button.set_image(list_view_img)
            right_box.pack_start(list_view_button, False, False, 0)

            grid_view_button = Gtk.RadioButton()
            grid_view_button.set_mode(False)
            grid_view_button.join_group(list_view_button)
            grid_view_button.set_active(
                    self.app.profile['view-mode'][self.name] == const.ICON_VIEW)
            grid_view_img = Gtk.Image.new_from_icon_name('view-grid-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            grid_view_button.set_image(grid_view_img)
            list_view_button.connect('clicked',
                                     self.on_list_view_button_clicked)
            grid_view_button.connect('clicked',
                                     self.on_grid_view_button_clicked)
            right_box.pack_start(grid_view_button, False, False, 0)

            self.search_entry = Gtk.Entry()
            self.search_entry.set_icon_from_icon_name(
                    Gtk.EntryIconPosition.PRIMARY,
                    'folder-saved-search-symbolic')
            self.search_entry.props.no_show_all = True
            self.search_entry.props.visible = False
            self.search_entry.connect('activate',
                                      self.on_search_entry_activated)
            self.pack_start(self.search_entry, False, False, 0)

    def on_page_show(self):
        if Config.GTK_GE_312:
            self.app.window.set_titlebar(self.headerbar)
            self.headerbar.show_all()

    def check_first(self):
        if self.first_run:
            self.first_run = False
            if self.app.profile['view-mode'][self.name] == const.ICON_VIEW:
                self.icon_window = IconWindow(self, self.app)
            else:
                self.icon_window = TreeWindow(self, self.app)
            self.pack_end(self.icon_window, True, True, 0)
            self.icon_window.show_all()
            self.load(is_user=True)

    # Open API
    def load(self, path='/', is_user=False):
        self.path = path
        self.page_num = 1
        self.has_next = True
        self.path_box.set_path(path, is_user)
        self.loading_spin.start()
        self.loading_spin.show_all()
        gutil.async_call(pcs.list_dir, self.app.cookie, self.app.tokens,
                         self.path, self.page_num, callback=self.on_load)
        gutil.async_call(pcs.get_quota, self.app.cookie, self.app.tokens,
                         callback=self.app.update_quota)

    def on_load(self, info, error=None):
        self.loading_spin.stop()
        self.loading_spin.hide()
        if not info:
            self.app.toast(_('Network error'))
        elif info.get('errno', -1) != 0:
            self.app.toast(info.get('error_msg', _('Network error')))
        if error or not info or info.get('errno', -1) != 0:
            logger.error('HomePage.on_load: %s, %s' % (info, error))
            return
        self.icon_window.load(info['list'])

    def load_next(self):
        '''载入下一页'''
        def on_load_next(info, error=None):
            self.loading_spin.stop()
            self.loading_spin.hide()
            if not info:
                self.app.toast(_('Network error'))
            elif info.get('errno', -1) != 0:
                self.app.toast(info.get('error_msg', _('Network error')))
            if error or not info or info.get('errno', -1) != 0:
                logger.error('HomePage.load_next: %s, %s' % (info, error))
                return
            if info['list']:
                self.icon_window.load_next(info['list'])
            else:
                self.has_next = False

        if not self.has_next:
            return
        self.page_num = self.page_num + 1
        self.path_box.set_path(self.path)
        self.loading_spin.start()
        self.loading_spin.show_all()
        gutil.async_call(pcs.list_dir, self.app.cookie, self.app.tokens,
                         self.path, self.page_num, callback=on_load_next)

    def reload(self, *args, **kwds):
        '''重新载入本页面'''
        self.load(self.path)

    def do_drag_data_received(self, drag_context, x, y, data, info, time):
        '''从其它程序拖放目录/文件, 以便上传.

        这里, 会直接把文件上传到当前目录(self.path).
        拖放事件已经被处理, 所以不会触发self.app.window的拖放动作.
        '''
        if not self.app.profile:
            return
        if info == TargetInfo.URI_LIST:
            uris = data.get_uris()
            source_paths = util.uris_to_paths(uris)
            if source_paths:
                self.app.upload_page.upload_files(source_paths, self.path)

    def on_search_button_toggled(self, search_button):
        status = search_button.get_active()
        self.search_entry.props.visible = status
        if status:
            self.search_entry.grab_focus()
        else:
            self.reload()

    def on_list_view_button_clicked(self, list_view_button):
        if not isinstance(self.icon_window, TreeWindow):
            self.remove(self.icon_window)
            self.icon_window = TreeWindow(self, self.app)
            self.pack_end(self.icon_window, True, True, 0)
            self.icon_window.show_all()
            self.app.profile['view-mode'][self.name] = const.TREE_VIEW
            gutil.dump_profile(self.app.profile)
            self.reload()

    def on_grid_view_button_clicked(self, grid_view_button):
        if isinstance(self.icon_window, TreeWindow):
            self.remove(self.icon_window)
            self.icon_window = IconWindow(self, self.app)
            self.pack_end(self.icon_window, True, True, 0)
            self.icon_window.show_all()
            self.app.profile['view-mode'][self.name] = const.ICON_VIEW
            gutil.dump_profile(self.app.profile)
            self.reload()

    def on_search_entry_activated(self, search_entry):
        text = search_entry.get_text()
        if not text:
            return
        self.loading_spin.start()
        self.loading_spin.show_all()
        gutil.async_call(pcs.search, self.app.cookie, self.app.tokens, text,
                         self.path, callback=self.on_load)
