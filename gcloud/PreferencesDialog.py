
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import GLib
from gi.repository import Gtk

from gcloud import Config
_ = Config._


class PreferencesDialog(Gtk.Dialog):

    def __init__(self, app):
        super().__init__(
                _('Preferences'), app.window, Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CLOSE, Gtk.ResponseType.OK))
        self.app = app

        self.set_default_size(480, 360)
        self.set_border_width(10)

        box = self.get_content_area()

        notebook = Gtk.Notebook()
        box.pack_start(notebook, True, True, 0)

        # General Tab
        general_grid = Gtk.Grid()
        general_grid.props.halign = Gtk.Align.CENTER
        general_grid.props.column_spacing = 12
        general_grid.props.margin_top = 5
        notebook.append_page(general_grid, Gtk.Label(_('General')))

        dir_label = Gtk.Label(_('Save to:'))
        dir_label.props.xalign = 1
        general_grid.attach(dir_label, 0, 0, 1, 1)
        dir_button = Gtk.FileChooserButton()
        dir_button.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        dir_button.set_current_folder(app.profile['save-dir'])
        dir_button.connect('file-set', self.on_dir_update)
        general_grid.attach(dir_button, 1, 0, 1, 1)

        notify_label = Gtk.Label(_('Use Notification:'))
        notify_label.props.xalign = 1
        general_grid.attach(notify_label, 0, 1, 1, 1)
        notify_switch = Gtk.Switch()
        notify_switch.props.halign = Gtk.Align.START
        general_grid.attach(notify_switch, 1, 1, 1, 1)

        tray_label = Gtk.Label(_('Minimize to System Tray:'))
        tray_label.props.xalign = 1
        general_grid.attach(tray_label, 0, 2, 1, 1)
        tray_switch = Gtk.Switch()
        tray_switch.props.halign = Gtk.Align.START
        general_grid.attach(tray_switch, 1, 2, 1, 1)

        box.show_all()

    def on_dir_update(self, file_button):
        dir_name = file_button.get_filename()
        if dir_name:
            self.app.profile['save-dir'] = dir_name
