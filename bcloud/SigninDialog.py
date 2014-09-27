
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import json
import os
import time

from gi.repository import GLib
from gi.repository import Gtk

from bcloud import auth
from bcloud import Config
_ = Config._
from bcloud import gutil
from bcloud.RequestCookie import RequestCookie

DELTA = 1 * 24 * 60 * 60   # 1 days

class SigninVcodeDialog(Gtk.Dialog):

    def __init__(self, parent, cookie, form):
        super().__init__(
            _('Verification..'), parent, Gtk.DialogFlags.MODAL)

        self.set_default_size(280, 120)
        self.set_border_width(5)
        self.cookie = cookie
        self.form = form

        box = self.get_content_area()
        box.set_spacing(5)

        self.vcode_img = Gtk.Image()
        box.pack_start(self.vcode_img, False, False, 0)
        self.vcode_entry = Gtk.Entry()
        self.vcode_entry.connect('activate', self.on_vcode_confirmed)
        box.pack_start(self.vcode_entry, False, False, 0)

        button_box = Gtk.Box()
        box.pack_end(button_box, False, False, 0)
        vcode_confirm = Gtk.Button.new_from_stock(Gtk.STOCK_OK)
        vcode_confirm.connect('clicked', self.on_vcode_confirmed)
        button_box.pack_end(vcode_confirm, True, True, 0)

        gutil.async_call(
            auth.get_wap_signin_vcode, cookie, form['vcodestr'],
            callback=self.update_img)
        self.img = Gtk.Image()
        box.pack_start(self.img, False, False, 0)

        box.show_all()

    def update_img(self, req_data, error=None):
        if error or not req_data:
            return
        vcode_path = os.path.join(
                Config.get_tmp_path(self.form['username']),
                'bcloud-signin-vcode')
        with open(vcode_path, 'wb') as fh:
            fh.write(req_data)
        self.vcode_img.set_from_file(vcode_path)

    def on_vcode_confirmed(self, *args):
        vcode = self.vcode_entry.get_text()
        if len(vcode) == 4:
            self.form['verifycode'] = vcode
            self.response(Gtk.ResponseType.OK)


class SigninDialog(Gtk.Dialog):

    profile = None
    password_changed = False

    def __init__(self, app, auto_signin=True):
        super().__init__(
                _('Sign in now'), app.window, Gtk.DialogFlags.MODAL)
        self.app = app
        self.auto_signin = auto_signin

        self.set_default_size(460, 260)
        self.set_border_width(15)
        
        self.conf = Config.load_conf()
        self.profile = None

        box = self.get_content_area()
        box.set_spacing(8)

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
        self.password_entry.props.visibility = False
        self.password_entry.connect('changed', self.on_password_entry_changed)
        box.pack_start(self.password_entry, False, False, 0)

        self.remember_check = Gtk.CheckButton.new_with_label(
                _('Remember Password'))
        self.remember_check.props.margin_top = 20
        self.remember_check.props.margin_left = 20
        box.pack_start(self.remember_check, False, False, 0)
        self.remember_check.connect('toggled', self.on_remember_check_toggled)

        self.signin_check = Gtk.CheckButton.new_with_label(
                _('Signin Automatically'))
        self.signin_check.set_sensitive(False)
        self.signin_check.props.margin_left = 20
        box.pack_start(self.signin_check, False, False, 0)
        self.signin_check.connect('toggled', self.on_signin_check_toggled)

        self.signin_button = Gtk.Button.new_with_label(_('Sign in'))
        self.signin_button.props.margin_top = 10
        self.signin_button.connect('clicked', self.on_signin_button_clicked)
        box.pack_start(self.signin_button, False, False, 0)

        self.infobar = Gtk.InfoBar()
        self.infobar.set_message_type(Gtk.MessageType.ERROR)
        box.pack_end(self.infobar, False, False, 0)
        info_content = self.infobar.get_content_area()
        self.info_label = Gtk.Label.new(
                _('Failed to sign in, please try again.'))
        info_content.pack_start(self.info_label, False, False, 0)

        box.show_all()
        self.infobar.hide()

        if not hasattr(gutil, 'keyring'):
            self.signin_check.set_active(False)
            self.signin_check.set_sensitive(False)
            self.remember_check.set_active(False)
            self.remember_check.set_sensitive(False)

        GLib.timeout_add(500, self.load_defualt_profile)

    def load_defualt_profile(self):
        if self.conf['default']:
            self.use_profile(self.conf['default'])
            self.password_changed = False
            # auto_signin here
            if self.signin_check.get_active() and self.auto_signin:
                self.signin_button.set_sensitive(False)
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
        self.profile = gutil.load_profile(username)
        self.password_entry.set_text(self.profile['password'])
        self.remember_check.set_active(self.profile['remember-password'])
        if self.profile['remember-password']:
            self.signin_check.set_active(self.profile['auto-signin'])
        else:
            self.signin_check.set_active(False)
        self.password_changed = False

    def signin_failed(self, error=None):
        if error:
            self.info_label.set_text(error)
        self.infobar.show_all()
        self.signin_button.set_sensitive(True)
        self.signin_button.set_label(_('Sign in'))

    def on_password_entry_changed(self, entry):
        self.password_changed = True

    def on_remember_check_toggled(self, button):
        if button.get_active():
            self.signin_check.set_sensitive(True)
        else:
            self.signin_check.set_sensitive(False)
            self.signin_check.set_active(False)
        if self.profile:
            self.profile['remember-password'] = self.remember_check.get_active()
            gutil.dump_profile(self.profile)

    def on_signin_check_toggled(self, button):
        if self.profile:
            self.profile['auto-signin'] = self.signin_check.get_active()
            gutil.dump_profile(self.profile)

    def on_signin_button_clicked(self, button):
        if (len(self.password_entry.get_text()) <= 1 or
                not self.username_combo.get_child().get_text()):
            return
        self.infobar.hide()
        button.set_label(_('In process...'))
        button.set_sensitive(False)
        self.signin()

    def signin(self):
        def on_get_bdstoken(bdstoken, error=None):
            if error or not bdstoken:
                print('Error in on_get_bdstoken():', bdstoken, error)
                print('Please check your username and passowrd')
                self.signin_failed(
                    _('Error: Failed to get bdstokens!'))
            else:
                nonlocal tokens
                tokens['bdstoken'] = bdstoken
                self.update_profile(
                        username, password, cookie, tokens, dump=True)

        def on_wap_signin(cookie_str, error):
            if not cookie_str or error:
                print('Error in on_wap_signin():', cookie_str, error)
                self.signin_failed(
                        _('Failed to signin, please try again.'))
            else:
                cookie.load_list(cookie_str)
                self.signin_button.set_label(_('Get bdstoken...'))
                gutil.async_call(auth.get_bdstoken, cookie,
                        callback=on_get_bdstoken)

        def on_get_wap_passport(info, error=None):
            if error or not info:
                print('Error occurs in on_get_wap_passport:', info, error)
                self.signin_failed(
                        _('Failed to get WAP page, please try again.'))
            cookie_str, _form = info
            if not cookie_str or not _form:
                print('Error occurs in on_get_wap_passport:', info, error)
                self.signin_failed(
                        _('Failed to get WAP page, please try again.'))
            else:
                nonlocal form
                form = _form
                form['username'] = username
                form['password'] = password
                cookie.load_list(cookie_str)
                if len(form.get('vcodestr', '')):
                    dialog = SigninVcodeDialog(self, cookie, form)
                    dialog.run()
                    dialog.destroy()
                    if len(form.get('verifycode', '')) != 4:
                        print('verifycode length is not 4!')
                        return
                self.signin_button.set_label(_('Signin...'))
                gutil.async_call(auth.wap_signin, cookie, form,
                        callback=on_wap_signin)

        def on_get_token(token, error=None):
            if error or not token:
                print('Error in get token():', token, error)
                self.signin_failed(
                        _('Failed to get tokens, please try again.'))
            else:
                nonlocal tokens
                tokens['token'] = token
                self.signin_button.set_label(_('Get WAP page...'))
                gutil.async_call(
                        auth.get_wap_passport, callback=on_get_wap_passport)

        def on_get_BAIDUID(uid_cookie, error=None):
            if error or not uid_cookie:
                print('Error in get BAIDUID():', uid_cookie, error)
                self.signin_failed(
                        _('Failed to get BAIDUID cookie, please try agin.'))
            else:
                cookie.load_list(uid_cookie)
                self.signin_button.set_label(_('Get TOKEN...'))
                gutil.async_call(
                        auth.get_token, cookie, callback=on_get_token)


        username = self.username_combo.get_child().get_text()
        password = self.password_entry.get_text()
        # 使用本地的缓存token, 有效期是三天
        if not self.password_changed and self.signin_check.get_active():
            cookie, tokens = self.load_auth(username)
            if cookie and tokens:
                self.update_profile(username, password, cookie, tokens)
                return
        cookie = RequestCookie()
        cookie.load('cflag=65535%3A1; PANWEB=1;')
        tokens = {}
        form = {}
        self.signin_button.set_label(_('Get BAIDUID...'))
        gutil.async_call(
                auth.get_BAIDUID, callback=on_get_BAIDUID)

    def load_auth(self, username):
        auth_file = os.path.join(Config.get_tmp_path(username), 'auth.json')
        # 如果授权信息被缓存, 并且没过期, 就直接读取它.
        if os.path.exists(auth_file):
            if time.time() - os.stat(auth_file).st_mtime < DELTA:
                with open(auth_file) as fh:
                    c, tokens = json.load(fh)
                cookie = RequestCookie(c)
                return cookie, tokens
        return None, None

    def dump_auth(self, username, cookie, tokens):
        auth_file = os.path.join(Config.get_tmp_path(username), 'auth.json')
        with open(auth_file, 'w') as fh:
            json.dump([str(cookie), tokens], fh)

    def update_profile(self, username, password, cookie, tokens, dump=False):
        if not self.profile:
            self.profile = gutil.load_profile(username)
        self.profile['username'] = username
        self.profile['remember-password'] = self.remember_check.get_active()
        self.profile['auto-signin'] = self.signin_check.get_active()
        if self.profile['remember-password']:
            self.profile['password'] = password
        else:
            self.profile['password'] = ''
        gutil.dump_profile(self.profile)

        if username not in self.conf['profiles']:
            self.conf['profiles'].append(username)
        if self.profile['auto-signin']:
            self.conf['default'] = username
        Config.dump_conf(self.conf)
        self.app.cookie = cookie
        self.app.tokens = tokens
        # dump auth info
        if dump:
            self.dump_auth(username, cookie, tokens)
        self.app.profile = self.profile
        self.app.window.set_default_size(*self.profile['window-size'])
        self.hide()
