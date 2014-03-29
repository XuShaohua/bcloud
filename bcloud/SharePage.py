
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os

from gi.repository import GdkPixbuf
from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud import gutil
from bcloud import pcs

(PIXBUF_COL, NAME_COL, PATH_COL, FSID_COL, MD5_COL, SIZE_COL,
    TOOLTIP_COL) = list(range(7))

class SharePage(Gtk.Box):

    icon_name = 'share-symbolic'
    disname = _('Share')
    tooltip = _('Share')
    first_run = True
    page_num = 1

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        toolbar = Gtk.Toolbar()
        self.pack_start(toolbar, False, False, 0)
        toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        toolbar.set_show_arrow(False)
        toolbar.set_icon_size(Gtk.IconSize.BUTTON)

        url_item = Gtk.ToolItem()
        toolbar.insert(url_item, 0)
        url_item.set_expand(True)
        self.url_entry = Gtk.Entry()
        self.url_entry.connect('activate', self.on_url_entry_activated)
        url_item.add(self.url_entry)

        refresh_button = Gtk.ToolButton()
        refresh_button.set_label(_('Refresh'))
        refresh_button.set_icon_name('view-refresh-symbolic')
        toolbar.insert(refresh_button, 1)

        home_button = Gtk.ToolButton()
        home_button.set_label(_('Home'))
        home_button.set_icon_name('go-home-symbolic')
        toolbar.insert(home_button, 2)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)

#        # name, path, sharelink, fsid, tooltip, pixbuf
#        self.liststore = Gtk.ListStore(
#                str, str, str, str, str, GdkPixbuf.Pixbuf)
#        self.iconview= Gtk.TreeView(model=self.liststore)
#        scrolled_win.add(self.iconview)
#        self.iconview.set_pixbuf_column(PIXBUF_COL)
#        self.iconview.set_text_column(NAME_COL)
#        self.iconview.set_tooltip_column(TOOLTIP_COL)
#        self.iconview.set_item_width(84)
#        self.iconview.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
#        self.iconview.connect(
#                'item-activated', self.on_iconview_item_activated)
#        self.iconview.connect(
#                'button-press-event', self.on_iconview_button_pressed)
        
    def load(self):
        '''载入用户自己的所有分享'''
        pass
        #self.liststore.clear()
#        gutil.async_call(
#                pcs.list_share, self.app.cookie, self.app.tokens, '/',
#                self.page_num, callback=self.append_filelist)

    def append_filelist(self, infos, error=None):
        print('append filelist:', infos)
        if error or not infos or infos['errno'] != 0:
            return
        for pcs_file in infos['list']:
            _, name = os.path.split(pcs_file['typicalPath'])
            self.liststore.append([
                name,
                pcs_file['typicalPath'],
                pcs_file['shortlink'],
                str(pcs_file['fsIds'][0]),
                pcs_file['typicalPath'],
                ])

    def on_url_entry_activated(self, entry):
        print(entry.get_text())

    def on_iconview_item_activated(self, iconview, tree_path):
        print(tree_path)

    def on_iconview_button_pressed(self, iconview, event):
        if ((event.type != Gdk.EventType.BUTTON_PRESS) or
                (event.button != Gdk.BUTTON_SECONDARY)):
            return
        print(event)
