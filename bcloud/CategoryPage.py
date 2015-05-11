
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud import const
from bcloud.IconWindow import IconWindow
from bcloud.IconWindow import TreeWindow
from bcloud import gutil
from bcloud.log import logger
from bcloud import pcs

__all__ = [
    'CategoryPage', 'PicturePage', 'DocPage', 'VideoPage',
    'BTPage', 'MusicPage', 'OtherPage',
]


class CategoryPage(Gtk.Box):

    page_num = 1
    has_next = True
    first_run = True
    name = 'CategoryPage'

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        if Config.GTK_GE_312:
            self.headerbar = Gtk.HeaderBar()
            self.headerbar.props.show_close_button = True
            self.headerbar.props.has_subtitle = False
            self.headerbar.set_title(self.disname)

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

            # show loading process
            self.loading_spin = Gtk.Spinner()
            self.loading_spin.props.valign = Gtk.Align.CENTER
            self.headerbar.pack_end(self.loading_spin)

        else:
            nav_bar = Gtk.Box()
            nav_bar_context = nav_bar.get_style_context()
            nav_bar_context.add_class(Gtk.STYLE_CLASS_RAISED)
            nav_bar_context.add_class(Gtk.STYLE_CLASS_LINKED)
            nav_bar.props.halign = Gtk.Align.END
            self.pack_start(nav_bar, False, False, 0)

            # show loading process
            self.loading_spin = Gtk.Spinner()
            self.loading_spin.props.valign = Gtk.Align.CENTER
            nav_bar.pack_start(self.loading_spin, False, False, 0)

            # toggle view mode
            list_view_button = Gtk.RadioButton()
            list_view_button.set_mode(False)
            list_view_img = Gtk.Image.new_from_icon_name('view-list-symbolic',
                    Gtk.IconSize.SMALL_TOOLBAR)
            list_view_button.set_image(list_view_img)
            nav_bar.pack_start(list_view_button, False, False, 0)

            grid_view_button = Gtk.RadioButton()
            grid_view_button.props.margin_right = 10
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
            nav_bar.pack_start(grid_view_button, False, False, 0)

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
            self.load()

    def load(self):
        def on_load(info, error=None):
            self.loading_spin.stop()
            self.loading_spin.hide()
            if not info:
                self.app.toast(_('Network error'))
            elif info.get('errno', -1) != 0:
                self.app.toast(info.get('error_msg', _('Network error')))
            if error or not info or info.get('errno', -1) != 0:
                logger.error('%s.on_load: %s, %s' % (self.disname, info, error))
                return
            self.icon_window.load(info['info'])

        has_next = True
        self.page_num = 1
        self.loading_spin.start()
        self.loading_spin.show_all()
        gutil.async_call(pcs.get_category, self.app.cookie, self.app.tokens,
                         self.category, self.page_num, callback=on_load)

    def load_next(self):
        def on_load_next(info, error=None):
            self.loading_spin.stop()
            self.loading_spin.hide()
            if not info:
                self.app.toast(_('Network error'))
            elif info.get('errno', -1) != 0:
                self.app.toast(info.get('error_msg', _('Network error')))
            if error or not info or info['errno'] != 0:
                logger.error('%s.on_load_next: %s, %s' %
                             (self.disname, info, error))
                return
            if info['info']:
                self.icon_window.load_next(info['info'])
            else:
                self.has_next = False

        if not self.has_next:
            return
        self.loading_spin.start()
        self.loading_spin.show_all()
        self.page_num = self.page_num + 1
        gutil.async_call(pcs.get_category, self.app.cookie, self.app.tokens,
                         self.category, self.page_num, callback=on_load_next)

    def reload(self, *args):
        self.load()

    def on_list_view_button_clicked(self, button):
        if not isinstance(self.icon_window, TreeWindow):
            self.remove(self.icon_window)
            self.icon_window = TreeWindow(self, self.app)
            self.pack_end(self.icon_window, True, True, 0)
            self.icon_window.show_all()
            self.app.profile['view-mode'][self.name] = const.TREE_VIEW
            gutil.dump_profile(self.app.profile)
            self.reload()

    def on_grid_view_button_clicked(self, button):
        if isinstance(self.icon_window, TreeWindow):
            self.remove(self.icon_window)
            self.icon_window = IconWindow(self, self.app)
            self.pack_end(self.icon_window, True, True, 0)
            self.icon_window.show_all()
            self.app.profile['view-mode'][self.name] = const.ICON_VIEW
            gutil.dump_profile(self.app.profile)
            self.reload()


class VideoPage(CategoryPage):

    icon_name = 'folder-videos-symbolic'
    disname = _('Videos')
    name = 'VideoPage'
    tooltip = _('Videos')
    category = 1


class MusicPage(CategoryPage):

    icon_name = 'folder-music-symbolic'
    disname = _('Music')
    name = 'MusicPage'
    tooltip = _('Music')
    category = 2


class PicturePage(CategoryPage):

    icon_name = 'folder-pictures-symbolic'
    disname = _('Pictures')
    name = 'PicturePage'
    tooltip = _('Pictures')
    category = 3


class DocPage(CategoryPage):

    icon_name = 'folder-documents-symbolic'
    disname = _('Documents')
    name = 'DocPage'
    tooltip = _('Documents')
    category = 4


class OtherPage(CategoryPage):

    icon_name = 'others-symbolic'
    disname = _('Others')
    name = 'OtherPage'
    tooltip = _('Others')
    category = 6


class BTPage(CategoryPage):

    icon_name = 'bittorrent-symbolic'
    disname = _('BT')
    name = 'BTPage'
    tooltip = _('BT seeds')
    category = 7
