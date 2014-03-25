
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud.FolderBrowserDialog import FolderBrowserDialog
from bcloud.Uploader import Uploader

(NAME_COL, SOURCEPATH_COL, PATH_COL, SIZE_COL, CURRSIZE_COL, 
    STATE_COL, STATENAME_COL, HUMANSIZE_COL, PERCENT_COL) = list(range(9))

class State:
    '''下载状态常量'''
    UPLOADING = 0
    WAITING = 1
    PAUSED = 2
    FINISHED = 3
    CANCELED = 4
    ERROR = 5

StateNames = [
    _('UPLOADING'),
    _('WAITING'),
    _('PAUSED'),
    _('FINISHED'),
    _('CANCELED'),
    _('ERROR'),
    ]

class UploadPage(Gtk.Box):

    icon_name = 'upload-symbolic'
    disname = _('Upload')
    tooltip = _('Uploading tasks')
    first_run = True
    workers = {}  # {`source_path`: (worker, row)}

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.connect('destroy', self.on_destroyed)

    def check_first(self):
        if self.first_run:
            self.first_run = False
            self.load()

    def load(self):
        control_box = Gtk.Box()
        self.pack_start(control_box, False, False, 0)

        start_button = Gtk.Button.new_with_label(_('Start'))
        start_button.connect('clicked', self.on_start_button_clicked)
        control_box.pack_start(start_button, False, False, 0)

        pause_button = Gtk.Button.new_with_label(_('Pause'))
        pause_button.connect('clicked', self.on_pause_button_clicked)
        control_box.pack_start(pause_button, False, False, 0)

        remove_button = Gtk.Button.new_with_label(_('Remove'))
        remove_button.connect('clicked', self.on_remove_button_clicked)
        control_box.pack_start(remove_button, False, False, 0)

        open_folder_button = Gtk.Button.new_with_label(_('Open Directory'))
        open_folder_button.connect(
                'clicked', self.on_open_folder_button_clicked)
        control_box.pack_end(open_folder_button, False, False, 10)

        upload_button = Gtk.Button.new_with_label(_('Upload a file'))
        upload_button.connect('clicked', self.on_upload_button_clicked)
        control_box.pack_end(upload_button, False, False, 0)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)
        
        # source_name, source_path, path, size, currsize,
        # state, statename, humansize, percent
        self.liststore = Gtk.ListStore(str, str, str, GObject.TYPE_LONG,
            GObject.TYPE_LONG, int, str, str, int)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.selection = self.treeview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        scrolled_win.add(self.treeview)

        name_cell = Gtk.CellRendererText(
                ellipsize=Pango.EllipsizeMode.END, ellipsize_set=True)
        name_col = Gtk.TreeViewColumn(_('Name'), name_cell, text=NAME_COL)
        name_col.set_expand(True)
        self.treeview.append_column(name_col)
        percent_cell = Gtk.CellRendererProgress()
        percent_col = Gtk.TreeViewColumn(
                _('Progress'), percent_cell, value=PERCENT_COL)
        self.treeview.append_column(percent_col)
        percent_col.props.min_width = 145
        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(
                _('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)
        size_col.props.min_width = 100
        state_cell = Gtk.CellRendererText()
        state_col = Gtk.TreeViewColumn(
                _('State'), state_cell, text=STATENAME_COL)
        self.treeview.append_column(state_col)
        state_col.props.min_width = 100
        self.treeview.set_tooltip_column(PATH_COL)

        self.show_all()

    def on_destroyed(self, box):
        print('on destroy')

    def on_start_button_clicked(self, button):
        print('暂不支持')

    def on_pause_button_clicked(self, button):
        print('暂不支持')

    def on_remove_button_clicked(self, button):
        print('暂不支持')

    def on_open_folder_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths or len(tree_paths) != 1:
            return
        tree_path = tree_paths[0]
        path = model[tree_path][PATH_COL]
        dir_name, _ = os.path.split(path)
        self.app.home_page.load(dir_name)
        self.app.switch_page(self.app.home_page)

    def on_upload_button_clicked(self, button):
        self.add_task()

    # Open API
    def add_task(self):
        self.check_first()
        file_dialog = Gtk.FileChooserDialog(
            _('Choose a file..'), self.app.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK))
        file_dialog.set_modal(True)
        response = file_dialog.run()
        if response != Gtk.ResponseType.OK:
            file_dialog.destroy()
            return
        source_path = file_dialog.get_filename()
        file_dialog.destroy()
        row = self.get_row_by_source_path(source_path)
        if row:
            print('Task is already in uploading schedule, do nothing.')
            return
        source_dir, filename = os.path.split(source_path)
        
        folder_dialog = FolderBrowserDialog(self, self.app)
        response = folder_dialog.run()
        if response != Gtk.ResponseType.OK:
            folder_dialog.destroy()
            return
        dir_name = folder_dialog.get_path()
        folder_dialog.destroy()
        path = os.path.join(dir_name, filename)
        size = os.path.getsize(source_path)
        task = [
            filename,
            source_path,
            path,
            size,
            0,
            State.WAITING,
            StateNames[State.WAITING],
            '0',
            0,
            ]
        self.liststore.append(task)
        self.scan_tasks()

    def pause_task(self):
        pass

    def remove_task(self):
        pass

    def scan_tasks(self):
        print('scan task')
        for row in self.liststore:
            if len(self.workers.keys()) >= self.app.profile['concurr-tasks']:
                print('max concurrent tasks reached')
                break
            if row[STATE_COL] == State.WAITING:
                self.start_worker(row)
        return True

    def start_worker(self, row):
        def on_worker_slice_sent(worker, source_path, curr_size):
            print('on workerslice sent:', source_path, curr_size)

        def on_worker_uploaded(worker, source_path):
            row = self.get_row_by_source_path(source_path)
            row[PERCENT_COL] = 100
            row[STATE_COL] = State.FINISHED
            row[STATENAME_COL] = StateNames[State.FINISHED]
            del self.workers[source_path]

        def on_worker_network_error(worker, source_path):
            print('UploadPage.network error')
            self.remove_worker(source_path)

        if row[SOURCEPATH_COL] in self.workers:
            return
        row[STATE_COL] = State.UPLOADING
        row[STATENAME_COL] = StateNames[State.UPLOADING]
        worker = Uploader(self, row, self.app.cookie, self.app.tokens)
        self.workers[row[SOURCEPATH_COL]] = (worker, row)
        worker.connect('slice-sent', on_worker_slice_sent)
        worker.connect('uploaded', on_worker_uploaded)
        worker.connect('network-error', on_worker_network_error)
        worker.start()

    def remove_worker(self, source_path, stop=True):
        if source_path not in self.workers:
            return
        worker, _ = self.workers[source_path]
        if stop:
            worker.stop()
        else:
            worker.pause()
        del self.workers[source_path]

    def get_row_by_source_path(self, source_path):
        for row in self.liststore:
            if row[SOURCEPATH_COL] == source_path:
                return row
        return None
