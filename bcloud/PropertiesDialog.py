
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os
import time

from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud import util
from bcloud.Widgets import LeftLabel
from bcloud.Widgets import SelectableLeftLabel

(PIXBUF_COL, NAME_COL, PATH_COL, TOOLTIP_COL, SIZE_COL, HUMAN_SIZE_COL,
    ISDIR_COL, MTIME_COL, HUMAN_MTIME_COL, TYPE_COL, PCS_FILE_COL) = list(
            range(11))


class PropertiesDialog(Gtk.Dialog):

    def __init__(self, parent, app, pcs_file):
        file_path, file_name = os.path.split(pcs_file['path'])
        super().__init__(file_name + _(' Properties'), app.window,
                         Gtk.DialogFlags.MODAL,
                         (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        self.set_default_response(Gtk.ResponseType.CLOSE)

        self.set_border_width(15)
        #self.set_default_size(640, 480)

        box = self.get_content_area()

        grid = Gtk.Grid()
        grid.props.row_spacing = 8
        if Config.GTK_GE_312:
            grid.props.margin_start = 15
        else:
            grid.props.margin_left = 15
        grid.props.column_spacing = 15
        box.pack_start(grid, True, True, 10)

        name_label = LeftLabel(_('Name:'))
        grid.attach(name_label, 0, 0, 1, 1)
        name_label2 = SelectableLeftLabel(file_name)
        grid.attach(name_label2, 1, 0, 1, 1)

        location_label = LeftLabel(_('Location:'))
        grid.attach(location_label, 0, 2, 1, 1)
        location_label2 = SelectableLeftLabel(file_path)
        grid.attach(location_label2, 1, 2, 1, 1)

        if pcs_file['isdir']:
            pass
        else:
            size_label = LeftLabel(_('Size'))
            grid.attach(size_label, 0, 1, 1, 1)
            size_human, size_comma = util.get_human_size(pcs_file['size'])
            if size_human:
                size_text = ''.join([str(size_human), ' (', size_comma,
                                     _(' bytes'), ')'])
            else:
                size_text = size_comma + _(' bytes')
            size_label2 = SelectableLeftLabel(size_text)
            grid.attach(size_label2, 1, 1, 1, 1)
            md5_label = LeftLabel('MD5:')
            grid.attach(md5_label, 0, 3, 1, 1)
            md5_label2 = SelectableLeftLabel(pcs_file['md5'])
            grid.attach(md5_label2, 1, 3, 1, 1)

        id_label = LeftLabel('FS ID:')
        grid.attach(id_label, 0, 4, 1, 1)
        id_label2 = SelectableLeftLabel(pcs_file['fs_id'])
        grid.attach(id_label2, 1, 4, 1, 1)

        ctime_label = LeftLabel(_('Created:'))
        grid.attach(ctime_label, 0, 5, 1, 1)
        ctime_label2 = SelectableLeftLabel(time.ctime(pcs_file['server_ctime']))
        grid.attach(ctime_label2, 1, 5, 1, 1)

        mtime_label = LeftLabel(_('Modified:'))
        grid.attach(mtime_label, 0, 6, 1, 1)
        mtime_label2 = SelectableLeftLabel(time.ctime(pcs_file['server_mtime']))
        grid.attach(mtime_label2, 1, 6, 1, 1)

        box.show_all()


class FolderPropertyDialog(Gtk.Dialog):

    def __init__(self, icon_window, app, path):
        file_path, file_name = os.path.split(path)
        # modify file_name if path is '/'
        if not file_name:
            file_name = '/'
        super().__init__(file_name + _(' Properties'), app.window,
                         Gtk.DialogFlags.MODAL,
                         (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        self.set_border_width(15)

        box = self.get_content_area()

        grid = Gtk.Grid()
        grid.props.row_spacing = 8
        if Config.GTK_GE_312:
            grid.props.margin_start = 15
        else:
            grid.props.margin_left = 15
        grid.props.column_spacing = 15
        box.pack_start(grid, True, True, 10)

        name_label = LeftLabel(_('Name:'))
        grid.attach(name_label, 0, 0, 1, 1)
        name_label2 = SelectableLeftLabel(file_name)
        grid.attach(name_label2, 1, 0, 1, 1)

        location_label = LeftLabel(_('Location:'))
        grid.attach(location_label, 0, 1, 1, 1)
        location_label2 = SelectableLeftLabel(file_path)
        grid.attach(location_label2, 1, 1, 1, 1)

        file_count = 0
        folder_count = 0
        for row in icon_window.liststore:
            if row[ISDIR_COL]:
                folder_count = folder_count + 1
            else:
                file_count = file_count + 1
        contents = _('{0} folders, {1} files').format(folder_count, file_count)
        content_label = LeftLabel(_('Contents:'))
        grid.attach(content_label, 0, 2, 1, 1)
        content_label2 = SelectableLeftLabel(contents)
        grid.attach(content_label2, 1, 2, 1, 1)

        box.show_all()
