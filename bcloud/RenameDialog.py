
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


class RenameDialog(Gtk.Dialog):

    def __init__(self, app, path_list):
        super().__init__(_('Rename files'), app.window, Gtk.DialogFlags.MODAL,
                         (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.set_border_width(10)
        self.set_default_size(640, 480)
        self.set_default_response(Gtk.ResponseType.OK)
        self.app = app

        box = self.get_content_area()

        scrolled_win = Gtk.ScrolledWindow()
        box.pack_start(scrolled_win, True, True, 0)

        grid = Gtk.Grid()
        scrolled_win.add(grid)
        grid.set_column_spacing(10)
        grid.set_row_spacing(5)
        grid.set_column_homogeneous(True)
        grid.props.margin_bottom = 20

        grid.attach(Gtk.Label.new(_('Old Name:')), 0, 0, 1, 1)
        grid.attach(Gtk.Label.new(_('New Name:')), 1, 0, 1, 1)

        self.rows = []
        i = 1
        for path in path_list:
            dir_name, name = os.path.split(path)
            old_entry = Gtk.Entry(text=name)
            old_entry.props.editable = False
            old_entry.props.can_focus = False
            old_entry.set_tooltip_text(path)
            grid.attach(old_entry, 0, i, 1, 1)
            
            new_entry = Gtk.Entry(text=name)
            new_entry.set_tooltip_text(path)
            new_entry.connect('changed', self.on_entry_changed)
            grid.attach(new_entry, 1, i, 1, 1)
            i = i + 1
            self.rows.append((path, old_entry, new_entry))

        self.infobar = Gtk.InfoBar()
        self.infobar.timestamp = 0
        self.infobar.set_message_type(Gtk.MessageType.ERROR)
        box.pack_start(self.infobar, False, False, 0)
        self.info_label= Gtk.Label()
        self.infobar.get_content_area().pack_start(self.info_label, False,
                                                   False, 0)

        box.show_all()
        self.infobar.hide()

    def show_message(self, message):
        def hide_message(timestamp):
            if timestamp == self.infobar.timestamp:
                self.infobar.hide()

        self.info_label.set_label(message)
        self.infobar.show_all()
        timestamp = time.time()
        self.infobar.timestamp = timestamp
        GLib.timeout_add(3000, hide_message, timestamp)

    def validate_path(self, abspath):
        if not abspath:
            self.show_message(_('Filename is empty'))
            return False
        elif '/' in abspath:
            self.show_message(_('Filename should not contain /'))
            return False
        stat = util.validate_pathname(abspath)
        if stat != ValidatePathState.OK:
            self.show_message(ValidatePathStateText[stat])
            return False
        else:
            return True

    def do_response(self, response_id):
        '''进行批量重命名.

        这里, 会忽略掉那些名称没发生变化的文件.
        '''
        if response_id != Gtk.ResponseType.OK:
            return
        filelist = []
        for row in self.rows:
            if row[1].get_text() == row[2].get_text():
                continue
            filelist.append({'path': row[0], 'newname': row[2].get_text()})
        if len(filelist) == 0:
            return
        pcs.rename(self.app.cookie, self.app.tokens, filelist)
        gutil.async_call(pcs.rename, self.app.cookie, self.app.tokens,
                         filelist, callback=self.app.reload_current_page)

    def on_entry_changed(self, entry):
        self.validate_path(entry.get_text())
