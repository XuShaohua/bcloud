
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud.IconWindow import IconWindow
from bcloud.IconWindow import TreeWindow
from bcloud import gutil
from bcloud import pcs

__all__ = [
    'CategoryPage', 'PicturePage', 'DocPage', 'VideoPage',
    'BTPage', 'MusicPage', 'OtherPage',
]


class CategoryPage(Gtk.Box):

    page_num = 1
    has_next = True
    first_run = True

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        nav_bar = Gtk.Toolbar()
        nav_bar.get_style_context().add_class(Gtk.STYLE_CLASS_MENUBAR)
        nav_bar.props.show_arrow = False
        nav_bar.props.toolbar_style = Gtk.ToolbarStyle.ICONS
        nav_bar.props.icon_size = Gtk.IconSize.LARGE_TOOLBAR
        nav_bar.props.halign = Gtk.Align.END
        self.pack_start(nav_bar, False, False, 0)

        # show loading process
        loading_button = Gtk.ToolItem()
        nav_bar.insert(loading_button, 0)
        loading_button.props.margin_right = 10
        self.loading_spin = Gtk.Spinner()
        loading_button.add(self.loading_spin)
        self.loading_spin.props.valign = Gtk.Align.CENTER
        nav_bar.child_set_property(loading_button, 'expand', True)

        # toggle view mode
        list_view_button = Gtk.ToolButton()
        list_view_button.set_label(_('ListView'))
        list_view_button.set_icon_name('list-view-symbolic')
        list_view_button.connect('clicked', self.on_list_view_button_clicked)
        nav_bar.insert(list_view_button, 1)

        grid_view_button = Gtk.ToolButton()
        grid_view_button.set_label(_('ListView'))
        grid_view_button.set_icon_name('grid-view-symbolic')
        grid_view_button.connect('clicked', self.on_grid_view_button_clicked)
        nav_bar.insert(grid_view_button, 2)

        self.icon_window = IconWindow(self, app)
        self.pack_end(self.icon_window, True, True, 0)

    def load(self):
        def on_load(info, error=None):
            self.loading_spin.stop()
            self.loading_spin.hide()
            if error or not info or info['errno'] != 0:
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
            if error or not info or info['errno'] != 0:
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
            self.reload()

    def on_grid_view_button_clicked(self, button):
        if isinstance(self.icon_window, TreeWindow):
            self.remove(self.icon_window)
            self.icon_window = IconWindow(self, self.app)
            self.pack_end(self.icon_window, True, True, 0)
            self.icon_window.show_all()
            self.reload()


class VideoPage(CategoryPage):

    icon_name = 'videos-symbolic'
    disname = _('Videos')
    tooltip = _('Videos')
    category = 1


class MusicPage(CategoryPage):

    icon_name = 'music-symbolic'
    disname = _('Music')
    tooltip = _('Music')
    category = 2


class PicturePage(CategoryPage):

    icon_name = 'pictures-symbolic'
    disname = _('Pictures')
    tooltip = _('Pictures')
    category = 3


class DocPage(CategoryPage):

    icon_name = 'documents-symbolic'
    disname = _('Documents')
    tooltip = _('Documents')
    category = 4


class OtherPage(CategoryPage):

    icon_name = 'others-symbolic'
    disname = _('Others')
    tooltip = _('Others')
    category = 6


class BTPage(CategoryPage):

    icon_name = 'bittorrent-symbolic'
    disname = _('BT')
    tooltip = _('BT seeds')
    category = 7
