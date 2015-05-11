
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os
import time

from gi.repository import GLib
from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud.const import ValidatePathState
from bcloud.const import ValidatePathStateText
from bcloud import gutil
from bcloud import pcs
from bcloud import util

class NewFolderDialog(Gtk.Dialog):

    def __init__(self, parent, app, path):
        super().__init__(_('New Folder'), app.window, Gtk.DialogFlags.MODAL,
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
        self.entry.connect('changed', self.on_entry_changed)
        self.entry.connect('activate', self.on_entry_activated)
        box.pack_start(self.entry, True, True, 10)

        self.infobar = Gtk.InfoBar()
        self.infobar.timestamp = 0
        self.infobar.set_message_type(Gtk.MessageType.ERROR)
        box.pack_start(self.infobar, False, False, 0)
        self.info_label= Gtk.Label()
        self.infobar.get_content_area().pack_start(self.info_label, False,
                                                   False, 0)

        box.show_all()
        self.infobar.hide()

    def on_show(self, *args):
        if len(self.path) == 1:
            self.entry.select_region(1, -1)
        elif len(self.path) > 1:
            self.entry.select_region(len(self.path) + 1, -1)

    def do_response(self, response_id):
        if response_id == Gtk.ResponseType.OK:
            self.mkdir()

    def on_entry_changed(self, entry):
        self.validate_path()

    def on_entry_activated(self, entry):
        self.mkdir()
        self.destroy()

    def show_message(self, message):
        def hide_message(timestamp):
            if timestamp == self.infobar.timestamp:
                self.infobar.hide()

        self.info_label.set_label(message)
        self.infobar.show_all()
        timestamp = time.time()
        self.infobar.timestamp = timestamp
        GLib.timeout_add(3000, hide_message, timestamp)

    def validate_path(self):
        abspath = self.entry.get_text()
        if not abspath:
            return False
        elif not abspath.startswith('/'):
            self.show_message(_('Filepath shall start with /'))
            return False
        stat = util.validate_pathname(abspath)
        if stat != ValidatePathState.OK:
            self.show_message(ValidatePathStateText[stat])
            return False
        else:
            return True

    def mkdir(self):
        if self.validate_path():
            gutil.async_call(pcs.mkdir, self.app.cookie, self.app.tokens,
                             self.entry.get_text(),
                             callback=self.app.reload_current_page)
