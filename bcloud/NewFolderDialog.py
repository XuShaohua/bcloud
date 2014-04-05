
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os

from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud import gutil
from bcloud import pcs

class NewFolderDialog(Gtk.Dialog):
    
    def __init__(self, parent, app, path):
        super().__init__(
                _('New Folder'), app.window, Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.set_default_response(Gtk.ResponseType.OK)
        self.connect('show', self.on_show)
        self.set_default_size(550, 200)

        self.app = app
        self.path = path

        self.set_border_width(10)
        box = self.get_content_area()

        folder_name = _('New Folder')
        abspath = os.path.join(path, folder_name)
        self.entry = Gtk.Entry()
        self.entry.set_text(abspath)
        self.entry.connect('activate', self.on_entry_activated)
        box.pack_start(self.entry, True, True, 10)

        box.show_all()

    def on_show(self, *args):
        if len(self.path) == 1:
            self.entry.select_region(1, -1)
        elif len(self.path) > 1:
            self.entry.select_region(len(self.path) + 1, -1)

    def do_response(self, response_id):
        if response_id == Gtk.ResponseType.OK:
            self.do_mkdir()

    def on_entry_activated(self, entry):
        self.do_mkdir()
        self.destroy()

    def do_mkdir(self):
        abspath = self.entry.get_text()
        if abspath.startswith('/'):
            gutil.async_call(
                    pcs.mkdir, self.app.cookie, self.app.tokens, abspath,
                    callback=self.app.reload_current_page)
