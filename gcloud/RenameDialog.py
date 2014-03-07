
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os

from gi.repository import Gtk

from gcloud import Config
_ = Config._
from gcloud import gutil
from gcloud import pcs

class RenameDialog(Gtk.Dialog):

    def __init__(self, app, path_list):
        super().__init__(
                _('Rename files'), app.window, Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.app = app

        self.set_border_width(10)
        box = self.get_content_area()

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(5)
        grid.set_column_homogeneous(True)
        grid.props.margin_bottom = 20
        box.pack_start(grid, True, True, 0)

        grid.attach(Gtk.Label(_('Old Name:')), 0, 0, 1, 1)
        grid.attach(Gtk.Label(_('New Name:')), 1, 0, 1, 1)

        self.rows = []
        i = 1
        for path in path_list:
            dir_name, name = os.path.split(path)
            old_entry = Gtk.Entry(text=name)
            old_entry.props.editable = False
            old_entry.set_tooltip_text(path)
            grid.attach(old_entry, 0, i, 1, 1)
            
            new_entry = Gtk.Entry(text=name)
            new_entry.set_tooltip_text(path)
            grid.attach(new_entry, 1, i, 1, 1)
            i = i + 1
            self.rows.append((path, old_entry, new_entry))

        box.show_all()

    def do_response(self, response_id):
        '''进行批量重命名.

        这里, 会忽略掉那些名称没发生变化的文件.
        '''
        print('do destroy')
        if response_id != Gtk.ResponseType.OK:
            return
        filelist = []
        for row in self.rows:
            if row[1].get_text() == row[2].get_text():
                continue
            filelist.append({
                'path': row[0],
                'newname': row[2].get_text(),
                })
        if len(filelist) == 0:
            return
        pcs.rename(self.app.cookie, self.app.tokens, filelist)
        gutil.async_call(
                pcs.rename, self.app.cookie, self.app.tokens, filelist,
                callback=self.app.reload_current_page)
