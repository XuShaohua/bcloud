
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

        self.set_default_size(360, 380)
        self.set_border_width(15)

        box = self.get_content_area()

        dir_box = Gtk.Box()
        box.pack_start(dir_box, False, False, 5)

        dir_label = Gtk.Label(_('Save to:'))
        dir_box.pack_start(dir_label, False, False, 0)
        dir_button = Gtk.FileChooserButton()
        dir_button.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        dir_button.set_current_folder(app.profile['save-dir'])
        dir_button.connect('file-set', self.on_dir_update)
        dir_box.pack_end(dir_button, False, False, 0)

        box.show_all()

    def on_dir_update(self, file_button):
        dir_name = file_button.get_filename()
        if dir_name:
            self.app.profile['save-dir'] = dir_name
