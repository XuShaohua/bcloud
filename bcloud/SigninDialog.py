
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

DELTA = 3 * 24 * 60 * 60   # 3 days

class SigninVcodeDialog(Gtk.Dialog):
    def __init__(self, parent, username, cookie, token, codeString, vcodetype):
        super().__init__(
            _('Verification..'), parent, Gtk.DialogFlags.MODAL)

        self.set_default_size(280, 120)
        self.set_border_width(10)
        self.username = username
        self.cookie = cookie
        self.token = token
        self.codeString = codeString
        self.vcodetype = vcodetype

        box = self.get_content_area()
        box.set_spacing(10)

        self.vcode_img = Gtk.Image()
        box.pack_start(self.vcode_img, False, False, 0)
        self.vcode_entry = Gtk.Entry()
        self.vcode_entry.connect('activate', self.check_entry)
        box.pack_start(self.vcode_entry, False, False, 0)

        button_box = Gtk.Box(spacing=10)
        box.pack_start(button_box, False, False, 0)
        vcode_refresh = Gtk.Button.new_from_stock(Gtk.STOCK_REFRESH)
        vcode_refresh.connect('clicked', self.on_vcode_refresh_clicked)
        button_box.pack_start(vcode_refresh, False, False, 0)
        vcode_confirm = Gtk.Button.new_from_stock(Gtk.STOCK_OK)
        vcode_confirm.connect('clicked', self.on_vcode_confirm_clicked)
        button_box.pack_start(vcode_confirm, False, False, 0)
        button_box.props.halign = Gtk.Align.CENTER

        gutil.async_call(
            auth.get_signin_vcode, cookie, codeString,
            callback=self.update_img)
        self.img = Gtk.Image()
        box.pack_start(self.img, False, False, 0)

        box.show_all()

    def get_vcode(self):
        return self.vcode_entry.get_text()

    def update_img(self, req_data, error=None):
        if error or not req_data:
            self.refresh_vcode()
            return
        vcode_path = os.path.join(
                Config.get_tmp_path(self.username),
                'bcloud-signin-vcode.jpg')
        with open(vcode_path, 'wb') as fh:
            fh.write(req_data)
        self.vcode_img.set_from_file(vcode_path)

    def refresh_vcode(self):
        def _refresh_vcode(info, error=None):
            self.codeString = info['data']['verifyStr']
            gutil.async_call(
                auth.get_signin_vcode, self.cookie, self.codeString,
                callback=self.update_img)

        gutil.async_call(
            auth.refresh_sigin_vcode, self.cookie, self.token,
            self.vcodetype, callback=_refresh_vcode)

    def check_entry(self, *args):
        if len(self.vcode_entry.get_text()) == 4:
            self.response(Gtk.ResponseType.OK)

    def on_vcode_refresh_clicked(self, button):
        self.refresh_vcode()

    def on_vcode_confirm_clicked(self, button):
        self.check_entry()


class SigninDialog(Gtk.Dialog):

    profile = None

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

        GLib.timeout_add(500, self.load_defualt_profile)

    def load_defualt_profile(self):
        if self.conf['default']:
            self.use_profile(self.conf['default'])
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

    def signin_failed(self, error=None):
        if error:
            self.info_label.set_text(error)
        self.infobar.show_all()
        self.signin_button.set_sensitive(True)
        self.signin_button.set_label(_('Sign in'))

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
        def on_get_bdstoken(bdstokens, error=None):
            if error or not bdstokens:
                self.signin_failed(
                    _('Error: Failed to get bdstokens!'))
            else:
                nonlocal tokens
                for token in bdstokens:
                    tokens[token] = bdstokens[token]
                self.update_profile(
                        username, password, cookie, tokens, dump=True)

        def on_get_bduss(result, error=None):
            status, info = result
            if status == 4:
                self.signin_failed(
                    _('Please check username and password are correct!'))
            elif status == 0:
                cookie.load_list(info)
                self.signin_button.set_label(_('Get bdstoken...'))
                gutil.async_call(
                    auth.get_bdstoken, cookie, callback=on_get_bdstoken)
            elif status == 257:
                vcodetype, codeString = info
                dialog = SigninVcodeDialog(
                    self, username, cookie, tokens['token'],
                    codeString, vcodetype)
                dialog.run()
                vcode = dialog.get_vcode()
                dialog.destroy()
                if not vcode or len(vcode) != 4:
                    self.signin_failed(
                        _('Please input verification code!'))
                    return
                self.signin_button.set_label(_('Get bduss...'))
                gutil.async_call(
                        auth.get_bduss, cookie,
                        tokens['token'], username, password, vcode,
                        codeString, callback=on_get_bduss)
            else:
                self.signin_failed(
                    _('Unknown err_no {0}, please try again!').format(
                        status))

        def on_check_login(status, error=None):
            if error or not status:
                self.signin_failed(
                        _('Failed to get check login, please try again.'))
            elif len(status['data']['codeString']):
                codeString = status['data']['codeString']
                vcodetype = status['data']['vcodetype']
                dialog = SigninVcodeDialog(
                    self, username, cookie, tokens['token'],
                    codeString, vcodetype)
                dialog.run()
                vcode = dialog.get_vcode()
                dialog.destroy()
                if not vcode or len(vcode) != 4:
                    self.signin_failed(
                        _('Please input verification code!'))
                    return
                self.signin_button.set_label(_('Get bduss...'))
                gutil.async_call(
                        auth.get_bduss, cookie,
                        tokens['token'], username, password, vcode,
                        codeString, callback=on_get_bduss)
            else:
                self.signin_button.set_label(_('Get bduss...'))
                gutil.async_call(
                        auth.get_bduss, cookie, tokens['token'], username,
                        password, callback=on_get_bduss)

        def on_get_UBI(ubi_cookie, error=None):
            if error or not ubi_cookie:
                self.signin_failed(
                        _('Failed to get UBI cookie, please try again.'))
            else:
                cookie.load_list(ubi_cookie)
                self.signin_button.set_label(_('Get token...'))
                gutil.async_call(
                        auth.check_login, cookie, tokens['token'], username,
                        callback=on_check_login)

        def on_get_token(token, error=None):
            if error or not token:
                self.signin_failed(
                        _('Failed to get tokens, please try again.'))
            else:
                nonlocal tokens
                tokens['token'] = token
                self.signin_button.set_label(_('Get UBI...'))
                gutil.async_call(
                        auth.get_UBI, cookie, token, callback=on_get_UBI)

        def on_get_BAIDUID(uid_cookie, error=None):
            if error or not uid_cookie:
                self.signin_failed(
                        _('Failed to get BAIDUID cookie, please try agin.'))
            else:
                cookie.load_list(uid_cookie)
                self.signin_button.set_label(_('Get BAIDUID...'))
                gutil.async_call(
                        auth.get_token, cookie, callback=on_get_token)


        username = self.username_combo.get_child().get_text()
        password = self.password_entry.get_text()
        # 使用本地的缓存token, 有效期是三天
        if self.signin_check.get_active():
            cookie, tokens = self.load_auth(username)
            if cookie and tokens:
                self.update_profile(username, password, cookie, tokens)
                return

        cookie = RequestCookie()
        tokens = {}
        cookie.load('cflag=65535%3A1; PANWEB=1;')
        self.signin_button.set_label(_('Get cookie...'))
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
