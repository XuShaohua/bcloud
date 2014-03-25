
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud import gutil
from bcloud import pcs

NAME_COL, PATH_COL, EMPTY_COL, LOADED_COL = list(range(4))
NUM = 100

class FolderBrowserDialog(Gtk.Dialog):

    is_loading = False

    def __init__(self, parent, app, title=_('Save to..')):
        super().__init__(
                title, app.window, Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OK, Gtk.ResponseType.OK))

        self.parent = parent
        self.app = app
        self.set_default_size(440, 480)
        self.set_border_width(10)

        box = self.get_content_area()
        scrolled_win = Gtk.ScrolledWindow()
        box.pack_start(scrolled_win, True, True, 0)

        # disname, path, empty, loaded
        self.treestore = Gtk.TreeStore(str, str, bool, bool)
        self.treeview = Gtk.TreeView(model=self.treestore)
        scrolled_win.add(self.treeview)
        icon_cell = Gtk.CellRendererPixbuf(icon_name='folder')
        name_cell = Gtk.CellRendererText()
        name_col = Gtk.TreeViewColumn(_('Folder'))
        name_col.pack_start(icon_cell, False)
        name_col.pack_start(name_cell, True)
        if Config.GTK_LE_36:
            name_col.add_attribute(name_cell, 'text', NAME_COL)
        else:
            name_col.set_attributes(name_cell, text=NAME_COL)
        self.treeview.append_column(name_col)
        self.treeview.connect('row-expanded', self.on_row_expanded)

        box.show_all()

        root_iter = self.treestore.append(None, ['/', '/', False, False,])
        self.list_dir(root_iter)

    def list_dir(self, parent_iter):
        if self.treestore[parent_iter][LOADED_COL]:
            return
        tree_path = self.treestore.get_path(parent_iter)
        path = self.treestore[tree_path][PATH_COL]
        first_child_iter = self.treestore.iter_nth_child(parent_iter, 0)
        if (first_child_iter and
                not self.treestore[first_child_iter][NAME_COL]):
            self.treestore.remove(first_child_iter)
        has_next = True
        page_num = 1
        while has_next:
            infos = pcs.list_dir(
                    self.app.cookie, self.app.tokens, path,
                    page=page_num, num=NUM)
            page_num = page_num + 1
            if not infos or infos['errno'] != 0:
                has_next = False
                return
            if len(infos['list']) < NUM:
                has_next = False
            for pcs_file in infos['list']:
                if not pcs_file['isdir']:
                    continue
                if pcs_file['dir_empty']:
                    empty = True
                else:
                    empty = False
                item = self.treestore.append(parent_iter, [
                    pcs_file['server_filename'],
                    pcs_file['path'],
                    empty,
                    False,
                    ])
                # 加入一个临时的占位点.
                if not empty:
                    self.treestore.append(item, [
                        '', pcs_file['path'], True, False])
        self.treestore[parent_iter][LOADED_COL] = True

    def get_path(self):
        selection = self.treeview.get_selection()
        model, tree_iter = selection.get_selected()
        if not tree_iter:
            return '/'
        else:
            return model[tree_iter][PATH_COL]

    def on_row_expanded(self, treeview, tree_iter, tree_path):
        if self.is_loading:
            return
        self.ist_loading = True
        self.list_dir(tree_iter)
        self.ist_loading = False
        self.treeview.expand_row(tree_path, False)
