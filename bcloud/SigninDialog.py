
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
from bcloud.log import logger
from bcloud.RequestCookie import RequestCookie
from bcloud import util
from bcloud import Widgets

DELTA = 1 * 24 * 60 * 60   # 1 days


class SigninVcodeDialog(Gtk.Dialog):
    '''登陆时的验证码对话框'''

    def __init__(self, parent, username, cookie, tokens, codeString, vcodetype):
        super().__init__(_('Verification..'), parent, Gtk.DialogFlags.MODAL)

        self.set_default_size(280, 130)
        self.set_border_width(10)
        self.username = username
        self.cookie = cookie
        self.tokens = tokens
        self.codeString = codeString
        self.vcodetype = vcodetype

        box = self.get_content_area()
        box.set_spacing(5)

        self.vcode_img = Gtk.Image()
        box.pack_start(self.vcode_img, True, True, 0)

        button_box = Gtk.Box(spacing=5)
        box.pack_start(button_box, True, True, 0)

        self.vcode_entry = Gtk.Entry()
        self.vcode_entry.connect('activate', self.check_entry)
        button_box.pack_start(self.vcode_entry, True, True, 0)

        if Config.GTK_GE_312:
            vcode_refresh = Widgets.IconButton('view-refresh-symbolic')
        else:
            vcode_refresh = Gtk.Button.new_from_stock(Gtk.STOCK_REFRESH)
        vcode_refresh.props.valign = Gtk.Align.CENTER
        vcode_refresh.connect('clicked', self.on_vcode_refresh_clicked)
        button_box.pack_start(vcode_refresh, False, False, 0)

        # show loading process
        self.loading_spin = Gtk.Spinner()
        self.loading_spin.props.valign = Gtk.Align.CENTER
        button_box.pack_start(self.loading_spin, False, False, 0)

        vcode_confirm = Gtk.Button.new_from_stock(Gtk.STOCK_OK)
        vcode_confirm.connect('clicked', self.on_vcode_confirm_clicked)
        vcode_confirm.props.valign = Gtk.Align.END
        box.pack_start(vcode_confirm, False, False, 10)

        box.show_all()
        self.loading_spin.hide()

        gutil.async_call(auth.get_signin_vcode, cookie, codeString,
                         callback=self.update_img)

    def get_vcode(self):
        return self.vcode_entry.get_text()

    def update_img(self, req_data, error=None):
        if error or not req_data:
            self.refresh_vcode()
            logger.error('SigninDialog.update_img: %s, %s' % (req_data, error))
            return
        vcode_path = os.path.join(Config.get_tmp_path(self.username),
                                  'bcloud-signin-vcode.jpg')
        with open(vcode_path, 'wb') as fh:
            fh.write(req_data)
        self.vcode_img.set_from_file(vcode_path)
        self.loading_spin.stop()
        self.loading_spin.hide()
        self.vcode_entry.set_sensitive(True)

    def refresh_vcode(self):
        def _refresh_vcode(info, error=None):
            if not info or error:
                logger.error('SigninVcode.refresh_vcode: %s, %s.' %
                             (info, error))
                return
            logger.debug('refresh vcode: %s' % info)
            self.codeString = info['data']['verifyStr']
            gutil.async_call(auth.get_signin_vcode, self.cookie,
                             self.codeString, callback=self.update_img)

        self.loading_spin.start()
        self.loading_spin.show_all()
        self.vcode_entry.set_sensitive(False)
        gutil.async_call(auth.refresh_signin_vcode, self.cookie, self.tokens,
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
    password_changed = False

    def __init__(self, app, auto_signin=True):
        super().__init__(_('Sign in now'), app.window, Gtk.DialogFlags.MODAL)
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

        if not gutil.keyring_available:
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
        if gutil.keyring_available:
            self.remember_check.set_active(self.profile['remember-password'])
            if self.profile['remember-password']:
                self.signin_check.set_active(self.profile['auto-signin'])
            else:
                self.signin_check.set_active(False)
        else:
            self.remember_check.set_sensitive(False)
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
                logger.error('SigninDialog.on_get_bdstoken: %s, %s' %
                             (bdstoken, error))
                self.signin_failed(_('Failed to get bdstoken!'))
            else:
                nonlocal tokens
                tokens['bdstoken'] = bdstoken
                self.update_profile(username, password, cookie, tokens,
                                    dump=True)

        def on_post_login(info, error=None):
            if error or not info:
                logger.error('SigninDialog.on_post_login: %s, %s' %
                             (info, error))
                self.signin_failed(
                        _('Login failed, please try again'))
            else:
                errno, query = info
                if errno == 0:
                    cookie.load_list(query)
                    self.signin_button.set_label(_('Get bdstoken...'))
                    gutil.async_call(auth.get_bdstoken, cookie,
                                     callback=on_get_bdstoken)
                # 257: 需要输入验证码
                elif errno == 257:
                    nonlocal verifycode
                    nonlocal codeString
                    vcodetype = query['vcodetype']
                    codeString = query['codeString']
                    dialog = SigninVcodeDialog(self, username, cookie,
                                               tokens['token'], codeString,
                                               vcodetype)
                    response = dialog.run()
                    verifycode = dialog.get_vcode()
                    codeString = dialog.codeString
                    dialog.destroy()
                    if not verifycode or len(verifycode) != 4:
                        self.signin_failed(_('Please input verification code!'))
                        return
                    else:
                        self.signin_button.set_label(_('Get bdstoken...'))
                        gutil.async_call(auth.post_login, cookie,
                                         tokens, username,
                                         password_enc, rsakey, verifycode,
                                         codeString, callback=on_post_login)
                # 密码错误
                elif errno == 4:
                    logger.error('SigninDialog.on_post_login: %s, %s' %
                                 (info, error))
                    self.signin_failed(_('Password error, please try again'))
                # 验证码错误
                elif errno == 6:
                    self.signin_failed(
                            _('Verfication code error, please try again'))
                # 需要短信验证
                elif errno == 400031:
                    logger.error('SigninDialog.on_post_login: %s, %s' %
                                 (info, error))
                    self.signin_failed(
                            _('Does not support SMS/Email verification!'))
                else:
                    logger.error('SigninDialog.on_post_login: %s, %s' %
                                 (info, error))
                    self.signin_failed(_('Unknown error, please try again'))

        def on_get_public_key(info, error=None):
            if not info or error:
                logger.error('SigninDialog.on_get_public_key: %s, %s' %
                             (info, error))
                self.signin_failed(
                        _('Failed to request public key, please try again'))
            else:
                pubkey = info['pubkey']
                nonlocal rsakey
                rsakey = info['key']
                nonlocal password_enc
                password_enc = util.RSA_encrypt(pubkey, password)
                gutil.async_call(auth.post_login, cookie, tokens,
                                 username, password_enc, rsakey, verifycode,
                                 codeString, callback=on_post_login)

        def on_check_login(info, error=None):
            if not info or error:
                logger.error('SigninDialog.on_check_login: %s, %s' %
                             (info, error))
                self.signin_failed(_('Failed to check login, please try again'))
            else:
                ubi_cookie, status = info
                cookie.load_list(ubi_cookie)
                nonlocal codeString
                nonlocal verifycode
                codeString = status['data']['codeString']
                vcodetype = status['data']['vcodetype']
                if codeString:
                    dialog = SigninVcodeDialog(self, username, cookie,
                                               tokens, codeString, vcodetype)
                    response = dialog.run()
                    verifycode = dialog.get_vcode()
                    codeString = dialog.codeString
                    dialog.destroy()
                    if not verifycode or len(verifycode) != 4:
                        self.signin_failed(_('Please input verification code!'))
                        return
                    else:
                        gutil.async_call(auth.get_public_key, cookie,
                                         tokens, callback=on_get_public_key)
                else:
                    gutil.async_call(auth.get_public_key, cookie,
                                     tokens, callback=on_get_public_key)

        def on_get_UBI(ubi_cookie, error=None):
            if error or not ubi_cookie:
                logger.error('SigninDialog.on_getUBI: %s, %s' %
                             (ubi_cookie, error))
                self.signin_failed(_('Failed to get UBI, please try again.'))
            else:
                cookie.load_list(ubi_cookie)
                self.signin_button.set_label(_('Check login'))
                gutil.async_call(auth.check_login, cookie, tokens,
                                 username, callback=on_check_login)

        def on_get_token(info, error=None):
            if error or not info:
                logger.error('SigninDialog.on_get_token: %s, %s' %
                             (info, error))
                self.signin_failed(_('Failed to get token, please try again.'))
            else:
                nonlocal tokens
                hosupport, token = info
                cookie.load_list(hosupport)
                cookie.load('cflag=65535%3A1; PANWEB=1;')
                tokens['token'] = token
                self.signin_button.set_label(_('Get UBI...'))
                gutil.async_call(auth.get_UBI, cookie, tokens,
                                 callback=on_get_UBI)

        def on_get_BAIDUID(uid_cookie, error=None):
            if error or not uid_cookie:
                logger.error('SigninDialog.on_get_BAIDUID: %s, %s' %
                             (uid_cookie, error))
                self.signin_failed(
                        _('Failed to get BAIDUID cookie, please try agin.'))
            else:
                cookie.load_list(uid_cookie)
                self.signin_button.set_label(_('Get TOKEN...'))
                gutil.async_call(auth.get_token, cookie, callback=on_get_token)


        username = self.username_combo.get_child().get_text()
        password = self.password_entry.get_text()
        # 使用本地的缓存token, 有效期是三天
        if not self.password_changed and self.signin_check.get_active():
            cookie, tokens = self.load_auth(username)
            if cookie and tokens:
                self.update_profile(username, password, cookie, tokens)
                return
        cookie = RequestCookie()
        tokens = {}
        verifycode = ''
        codeString = ''
        password_enc = ''
        rsakey = ''
        self.signin_button.set_label(_('Get BAIDUID...'))
        gutil.async_call(auth.get_BAIDUID, callback=on_get_BAIDUID)

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
