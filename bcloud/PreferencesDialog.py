
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import GLib
from gi.repository import Gtk

from bcloud import Config
_ = Config._

from bcloud.FolderBrowserDialog import FolderBrowserDialog

class PreferencesDialog(Gtk.Dialog):

    def __init__(self, app):
        self.app = app
        super().__init__(_('Preferences'), app.window, Gtk.DialogFlags.MODAL,
                         (Gtk.STOCK_CLOSE, Gtk.ResponseType.OK))
        self.set_default_response(Gtk.ResponseType.OK)

        self.set_default_size(480, 360)
        self.set_border_width(10)

        box = self.get_content_area()

        notebook = Gtk.Notebook()
        box.pack_start(notebook, True, True, 0)

        # General Tab
        general_grid = Gtk.Grid()
        general_grid.props.halign = Gtk.Align.CENTER
        general_grid.props.column_spacing = 12
        general_grid.props.row_spacing = 5
        general_grid.props.margin_top = 5
        notebook.append_page(general_grid, Gtk.Label.new(_('General')))

        stream_label = Gtk.Label.new(_('Use streaming mode:'))
        stream_label.props.xalign = 1
        general_grid.attach(stream_label, 0, 0, 1, 1)
        stream_switch = Gtk.Switch()
        stream_switch.set_active(self.app.profile['use-streaming'])
        stream_switch.connect('notify::active', self.on_stream_switch_activate)
        stream_switch.props.halign = Gtk.Align.START
        stream_switch.set_tooltip_text(
                _('Open the compressed version of videos, useful for those whose network connection is slow.'))
        general_grid.attach(stream_switch, 1, 0, 1, 1)

        notify_label = Gtk.Label.new(_('Use notification:'))
        notify_label.props.xalign = 1
        general_grid.attach(notify_label, 0, 1, 1, 1)
        notify_switch = Gtk.Switch()
        notify_switch.props.halign = Gtk.Align.START
        notify_switch.set_active(self.app.profile['use-notify'])
        notify_switch.connect('notify::active', self.on_notify_switch_activate)
        general_grid.attach(notify_switch, 1, 1, 1, 1)

        dark_theme_label = Gtk.Label.new(_('Use dark theme:'))
        dark_theme_label.props.xalign = 1
        general_grid.attach(dark_theme_label, 0, 2, 1, 1)
        dark_theme_switch = Gtk.Switch()
        dark_theme_switch.set_active(self.app.profile['use-dark-theme'])
        dark_theme_switch.connect('notify::active',
                                  self.on_dark_theme_switch_toggled)
        dark_theme_switch.props.halign = Gtk.Align.START
        general_grid.attach(dark_theme_switch, 1, 2, 1, 1)

        status_label = Gtk.Label.new(_('Use Status Icon:'))
        status_label.props.xalign = 1
        general_grid.attach(status_label, 0, 3, 1, 1)
        status_switch = Gtk.Switch()
        status_switch.set_active(self.app.profile['use-status-icon'])
        status_switch.connect('notify::active', self.on_status_switch_activate)
        status_switch.props.halign = Gtk.Align.START
        general_grid.attach(status_switch, 1, 3, 1, 1)

        minimized_label = Gtk.Label.new(_('Startup minimized:'))
        minimized_label.props.xalign = 1
        general_grid.attach(minimized_label, 0, 4, 1, 1)
        minimized_switch = Gtk.Switch()
        minimized_switch.set_active(self.app.profile['startup-minimized'])
        if self.app.profile['use-status-icon']:
            minimized_switch.set_sensitive(True)
        else:
            minimized_switch.set_sensitive(False)
            minimized_switch.set_active(False)
            self.app.profile['startup-minimized'] = False
        minimized_switch.connect('notify::active',
                                 self.on_minimized_switch_activate)
        minimized_switch.props.halign = Gtk.Align.START
        general_grid.attach(minimized_switch, 1, 4, 1, 1)
        self.minimized_switch = minimized_switch

        avatar_label = Gtk.Label.new(_('Display Avatar:'))
        avatar_label.props.xalign = 1
        general_grid.attach(avatar_label, 0, 5, 1, 1)
        avatar_switch = Gtk.Switch()
        avatar_switch.set_active(self.app.profile['display-avatar'])
        avatar_switch.connect('notify::active', self.on_avatar_switch_activate)
        avatar_switch.props.halign = Gtk.Align.START
        general_grid.attach(avatar_switch, 1, 5, 1, 1)


        # download tab
        download_grid = Gtk.Grid()
        download_grid.props.halign = Gtk.Align.CENTER
        download_grid.props.column_spacing = 12
        download_grid.props.row_spacing = 5
        download_grid.props.margin_top = 5
        notebook.append_page(download_grid, Gtk.Label.new(_('Download')))

        dir_label = Gtk.Label.new(_('Save To:'))
        dir_label.props.xalign = 1
        download_grid.attach(dir_label, 0, 0, 1, 1)
        dir_button = Gtk.FileChooserButton()
        dir_button.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        dir_button.set_current_folder(app.profile['save-dir'])
        dir_button.connect('file-set', self.on_dir_update)
        download_grid.attach(dir_button, 1, 0, 1, 1)

        concurr_label = Gtk.Label.new(_('Concurrent downloads:'))
        concurr_label.props.xalign = 1
        download_grid.attach(concurr_label, 0, 1, 1, 1)
        concurr_spin = Gtk.SpinButton.new_with_range(1, 5, 1)
        concurr_spin.set_value(self.app.profile['concurr-download'])
        concurr_spin.props.halign = Gtk.Align.START
        concurr_spin.connect('value-changed',
                             self.on_concurr_download_value_changed)
        download_grid.attach(concurr_spin, 1, 1, 1, 1)

        segments_label = Gtk.Label.new(_('Per task:'))
        segments_label.props.xalign = 1
        download_grid.attach(segments_label, 0, 2, 1, 1)
        segments_spin = Gtk.SpinButton.new_with_range(1, 10, 1)
        segments_spin.set_value(self.app.profile['download-segments'])
        segments_spin.props.halign = Gtk.Align.START
        segments_spin.connect('value-changed', self.on_segments_value_changed)
        download_grid.attach(segments_spin, 1, 2, 1, 1)
        segments_label2 = Gtk.Label.new(_('connections'))
        segments_label2.props.xalign = 0
        download_grid.attach(segments_label2, 2, 2, 1, 1)

        retries_each = Gtk.Label.new(_('Retries each:'))
        retries_each.props.xalign = 1
        download_grid.attach(retries_each, 0, 3, 1, 1)
        retries_spin = Gtk.SpinButton.new_with_range(0, 120, 1)
        retries_spin.set_value(self.app.profile['retries-each'])
        retries_spin.connect('value-changed', self.on_retries_value_changed)
        retries_spin.props.halign = Gtk.Align.START
        retries_spin.set_tooltip_text(_('0: disable retries'))
        download_grid.attach(retries_spin, 1, 3, 1, 1)
        retries_minute_label = Gtk.Label.new(_('minutes'))
        retries_minute_label.props.xalign = 0
        download_grid.attach(retries_minute_label, 2, 3, 1, 1)

        download_timeout = Gtk.Label.new(_('Download timeout:'))
        download_timeout.props.xalign = 1
        download_grid.attach(download_timeout, 0, 4, 1, 1)
        download_timeout_spin = Gtk.SpinButton.new_with_range(10, 240, 30)
        download_timeout_spin.set_value(self.app.profile['download-timeout'])
        download_timeout_spin.props.halign = Gtk.Align.START
        download_timeout_spin.connect('value-changed',
                                      self.on_download_timeout_value_changed)
        download_grid.attach(download_timeout_spin, 1, 4, 1, 1)
        download_timeout_second = Gtk.Label.new(_('seconds'))
        download_timeout_second.props.xalign = 0
        download_grid.attach(download_timeout_second, 2, 4, 1, 1)

        download_mode_label = Gtk.Label.new(_('File exists while downloading:'))
        download_mode_label.props.xalign = 1
        download_grid.attach(download_mode_label, 0, 5, 1, 1)
        download_mode_combo = Gtk.ComboBoxText()
        download_mode_combo.append_text(_('Do Nothing'))
        download_mode_combo.append_text(_('Overwrite'))
        download_mode_combo.append_text(_('Rename Automatically'))
        download_mode_combo.set_active(self.app.profile['download-mode'])
        download_mode_combo.connect('changed', self.on_download_mode_changed)
        download_mode_combo.set_tooltip_text(
                _('What to do when downloading a file which already exists on local disk'))
        download_grid.attach(download_mode_combo, 1, 5, 2, 1)

        confirm_deletion_label = Gtk.Label(
                _('Ask me when deleting unfinished tasks:'))
        download_grid.attach(confirm_deletion_label, 0, 6, 1, 1)
        confirm_deletion_switch = Gtk.Switch()
        confirm_deletion_switch.set_active(
                self.app.profile['confirm-download-deletion'])
        confirm_deletion_switch.connect('notify::active',
                self.on_confirm_deletioin_switch_activate)
        confirm_deletion_switch.props.halign = Gtk.Align.START
        download_grid.attach(confirm_deletion_switch, 1, 6, 1, 1)


        # upload tab
        upload_grid = Gtk.Grid()
        upload_grid.props.halign = Gtk.Align.CENTER
        upload_grid.props.column_spacing = 12
        upload_grid.props.row_spacing = 5
        upload_grid.props.margin_top = 5
        notebook.append_page(upload_grid, Gtk.Label.new(_('Upload')))

        concurr_upload_label = Gtk.Label.new(_('Concurrent uploads:'))
        concurr_upload_label.props.xalign = 1
        upload_grid.attach(concurr_upload_label, 0, 0, 1, 1)
        concurr_upload_spin = Gtk.SpinButton.new_with_range(1, 5, 1)
        concurr_upload_spin.set_value(self.app.profile['concurr-upload'])
        concurr_upload_spin.props.halign = Gtk.Align.START
        concurr_upload_spin.connect('value-changed',
                                    self.on_concurr_upload_value_changed)
        upload_grid.attach(concurr_upload_spin, 1, 0, 1, 1)

        upload_hidden_label = Gtk.Label.new(_('Upload hidden files:'))
        upload_hidden_label.props.xalign = 1
        upload_grid.attach(upload_hidden_label, 0, 1, 1, 1)
        upload_hidden_switch = Gtk.Switch()
        upload_hidden_switch.props.halign = Gtk.Align.START
        upload_hidden_switch.set_tooltip_text(
                _('Also upload hidden files and folders'))
        upload_hidden_switch.set_active(self.app.profile['upload-hidden-files'])
        upload_hidden_switch.connect('notify::active',
                                     self.on_upload_hidden_switch_activate)
        upload_grid.attach(upload_hidden_switch, 1, 1, 1, 1)

        upload_mode_label = Gtk.Label.new(_('File exists while uploading:'))
        upload_mode_label.props.xalign = 1
        upload_grid.attach(upload_mode_label, 0, 2, 1, 1)
        upload_mode_combo = Gtk.ComboBoxText()
        upload_mode_combo.append_text(_('Do Nothing'))
        upload_mode_combo.append_text(_('Overwrite'))
        upload_mode_combo.append_text(_('Rename Automatically'))
        upload_mode_combo.set_active(self.app.profile['upload-mode'])
        upload_mode_combo.set_tooltip_text(
                _('What to do when uploading a file which already exists on server'))
        upload_mode_combo.connect('changed', self.on_upload_mode_changed)
        upload_grid.attach(upload_mode_combo, 1, 2, 2, 1)

        enable_sync_label = Gtk.Label.new(_('Enable Sync:'))
        enable_sync_label.props.xalign = 1
        upload_grid.attach(enable_sync_label, 0, 3, 1, 1)
        sync_switch = Gtk.Switch()
        sync_switch.set_active(self.app.profile['enable-sync'])
        sync_switch.props.halign = Gtk.Align.START
        upload_grid.attach(sync_switch, 1, 3, 1, 1)

        sync_dir_label = Gtk.Label.new(_('Sync Dir:'))
        sync_dir_label.props.xalign = 1
        upload_grid.attach(sync_dir_label, 0, 4, 1, 1)
        sync_dir_button = Gtk.FileChooserButton()
        sync_dir_button.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        sync_dir_button.set_current_folder(app.profile['sync-dir'])
        sync_dir_button.connect('file-set', self.on_sync_dir_update)
        upload_grid.attach(sync_dir_button, 1, 4, 1, 1)

        sync_dest_dir_label = Gtk.Label.new(_('Dest Sync Dir:'))
        sync_dest_dir_label.props.xalign = 1
        upload_grid.attach(sync_dest_dir_label, 0, 5, 1, 1)
        dest_dir_button = Gtk.Button.new_with_label(
                app.profile['dest-sync-dir'])
        dest_dir_button.connect('clicked', self.on_destdir_clicked)
        upload_grid.attach(dest_dir_button, 1, 5, 1, 1)

        sync_elements = (sync_dir_label, sync_dir_button, sync_dest_dir_label,
                         dest_dir_button)
        for element in sync_elements:
            element.set_sensitive(app.profile['enable-sync'])
        sync_switch.connect('notify::active', self.on_sync_switch_activate,
                            sync_elements)

        box.show_all()

    def on_stream_switch_activate(self, switch, event):
        self.app.profile['use-streaming'] = switch.get_active()

    def on_notify_switch_activate(self, switch, event):
        self.app.profile['use-notify'] = switch.get_active()

    def on_dark_theme_switch_toggled(self, switch, event):
        self.app.profile['use-dark-theme'] = switch.get_active()

    def on_status_switch_activate(self, switch, event):
        status = switch.get_active()
        self.app.profile['use-status-icon'] = status
        if status:
            self.minimized_switch.set_sensitive(True)
        else:
            self.minimized_switch.set_sensitive(False)
            self.minimized_switch.set_active(False)

    def on_minimized_switch_activate(self, switch, event):
        self.app.profile['startup-minimized'] = switch.get_active()

    def on_avatar_switch_activate(self, switch, event):
        self.app.profile['display-avatar'] = switch.get_active()

    def on_concurr_download_value_changed(self, concurr_spin):
        self.app.profile['concurr-download'] = concurr_spin.get_value()

    def on_dir_update(self, file_button):
        dir_name = file_button.get_filename()
        if dir_name:
            self.app.profile['save-dir'] = dir_name

    def on_segments_value_changed(self, segments_spin):
        self.app.profile['download-segments'] = segments_spin.get_value()

    def on_retries_value_changed(self, retries_spin):
        self.app.profile['retries-each'] = retries_spin.get_value()

    def on_download_timeout_value_changed(self, download_timeout_spin):
        self.app.profile['download-timeout'] = \
                download_timeout_spin.get_value()

    def on_download_mode_changed(self, combo):
        self.app.profile['download-mode'] = combo.get_active()

    def on_confirm_deletioin_switch_activate(self, switch, event):
        self.app.profile['confirm-download-deletion'] = switch.get_active()


    def on_concurr_upload_value_changed(self, concurr_spin):
        self.app.profile['concurr-upload'] = concurr_spin.get_value()

    def on_upload_hidden_switch_activate(self, switch, event):
        self.app.profile['upload-hidden-files'] = switch.get_active()

    def on_upload_mode_changed(self, combo):
        self.app.profile['upload-mode'] = combo.get_active()

    def on_sync_switch_activate(self, switch, event, sync_elements):
        status = switch.get_active()
        self.app.profile['enable-sync'] = status

        for element in sync_elements:
            element.set_sensitive(status)

    def on_sync_dir_update(self, file_button):
        dir_name = file_button.get_filename()
        if dir_name:
            self.app.profile['sync-dir'] = dir_name

    def on_destdir_clicked(self, button):
        folder_dialog = FolderBrowserDialog(self, self.app)
        response = folder_dialog.run()
        if response != Gtk.ResponseType.OK:
            folder_dialog.destroy()
            return
        dir_name = folder_dialog.get_path()
        folder_dialog.destroy()
        button.set_label(dir_name)
        self.app.profile['dest-sync-dir'] = dir_name

