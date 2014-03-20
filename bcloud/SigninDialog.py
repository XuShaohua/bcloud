
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os

from gi.repository import GLib
from gi.repository import Gtk

from bcloud import auth
from bcloud import Config
_ = Config._

class SigninDialog(Gtk.Dialog):

    def __init__(self, app):
        super().__init__(
                _('Sign in now'), app.window, Gtk.DialogFlags.MODAL)
        self.app = app

        self.set_default_size(460, 260)
        self.set_border_width(15)
        
        self.conf = Config.load_conf()
        self.profile = None

        box = self.get_content_area()
        box.set_spacing(8)

        # username
        username_ls = Gtk.ListStore(str)
        for username in self.conf['profiles']:
            username_ls.append([username,])
        self.username_combo = Gtk.ComboBox.new_with_entry()
        self.username_combo.set_model(username_ls)
        self.username_combo.set_entry_text_column(0)
        self.username_combo.set_tooltip_text(_('Username/Email/Phone...'))
        box.pack_start(self.username_combo, False, False, 0)
        self.username_combo.connect('changed', self.on_username_changed)

        self.password_entry = Gtk.Entry()
        self.password_entry.set_placeholder_text(_('Password ..'))
        self.password_entry.props.invisible_char_set = True
        box.pack_start(self.password_entry, False, False, 0)

        self.remember_check = Gtk.CheckButton(_('Remember Password'))
        self.remember_check.props.margin_top = 20
        box.pack_start(self.remember_check, False, False, 0)
        self.remember_check.connect('toggled', self.on_remember_check_toggled)

        self.signin_check = Gtk.CheckButton(_('Signin Automatically'))
        self.signin_check.set_sensitive(False)
        box.pack_start(self.signin_check, False, False, 0)
        self.signin_check.connect('toggled', self.on_signin_check_toggled)

        signin_button = Gtk.Button(_('Sign in'))
        signin_button.props.margin_top = 10
        box.pack_start(signin_button, False, False, 0)
        signin_button.connect('clicked', self.on_signin_button_clicked)

        self.infobar = Gtk.InfoBar()
        self.infobar.set_message_type(Gtk.MessageType.ERROR)
        box.pack_end(self.infobar, False, False, 0)
        info_content = self.infobar.get_content_area()
        info_label = Gtk.Label(_('Failed to sign in, please try again.'))
        info_content.pack_start(info_label, False, False, 0)

        box.show_all()
        self.infobar.hide()

        GLib.timeout_add(500, self.load_defualt_profile)

    def load_defualt_profile(self):
        if self.conf['default']:
            self.use_profile(self.conf['default'])
            if self.signin_check.get_active():
                self.signin()
        return False

    def on_username_changed(self, combo):
        tree_iter = combo.get_active_iter()
        username = ''
        if tree_iter != None:
            model = combo.get_model()
            username = model[tree_iter][0]
            self.use_profile(username)
        else:
            entry = combo.get_child()
            username = entry.get_text()
            self.profile = None

    def use_profile(self, username):
        model = self.username_combo.get_model()
        for row in model: 
            if row[0] == username:
                self.username_combo.set_active_iter(row.iter)
                break
        self.profile = Config.load_profile(username)
        self.password_entry.set_text(self.profile['password'])
        self.remember_check.set_active(self.profile['remember-password'])
        if self.profile['remember-password']:
            self.signin_check.set_active(self.profile['auto-signin'])
        else:
            self.signin_check.set_active(False)

    def on_remember_check_toggled(self, button):
        if button.get_active():
            self.signin_check.set_sensitive(True)
        else:
            self.signin_check.set_sensitive(False)
            self.signin_check.set_active(False)

    def on_signin_check_toggled(self, button):
        pass

    def on_signin_button_clicked(self, button):
        self.signin()

    def signin(self):
        username = self.username_combo.get_child().get_text()
        password = self.password_entry.get_text()
        auth_cache = os.path.join(Config.CACHE_DIR, username, 'auth.json')
        cookie, tokens = auth.get_auth_info(username, password, auth_cache)
        if cookie and tokens:
            if not self.profile:
                self.profile = Config.load_profile(username)
            self.profile['username'] = username
            self.profile['remember-password'] = self.remember_check.get_active()
            self.profile['auto-signin'] = self.signin_check.get_active()
            if self.profile['remember-password']:
                self.profile['password'] = password
            else:
                self.profile['password'] = ''
            Config.dump_profile(self.profile)

            if username not in self.conf['profiles']:
                self.conf['profiles'].append(username)
            if self.profile['auto-signin']:
                self.conf['default'] = username
            Config.dump_conf(self.conf)
            self.app.cookie = cookie
            self.app.tokens = tokens
            self.app.profile = self.profile
            self.app.window.set_default_size(*self.profile['window-size'])
            self.destroy()
        else:
            self.infobar.show_all()
