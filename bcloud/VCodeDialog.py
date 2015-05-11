
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os

from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud import gutil
from bcloud.log import logger
from bcloud import net


class VCodeDialog(Gtk.Dialog):

    def __init__(self, parent, app, info):
        super().__init__(_('Verification..'), app.window,
                         Gtk.DialogFlags.MODAL,
                         (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                          Gtk.STOCK_OK, Gtk.ResponseType.OK))

        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(320, 200)
        self.set_border_width(10)
        self.app = app

        box = self.get_content_area()
        box.set_spacing(10)

        gutil.async_call(net.urlopen, info['img'],
                         {'Cookie': app.cookie.header_output()},
                         callback=self.update_img)
        self.img = Gtk.Image()
        box.pack_start(self.img, False, False, 0)

        self.entry = Gtk.Entry()
        self.entry.connect('activate',
                lambda *args: self.response(Gtk.ResponseType.OK))
        box.pack_start(self.entry, False, False, 0)

        box.show_all()

    def get_vcode(self):
        return self.entry.get_text()

    def update_img(self, request, error=None):
        if error or not request:
            # TODO: add a refresh button
            logger.error('VCodeDialog.update_img: %s, %s' % (request, error))
            return
        vcode_path = os.path.join(
                Config.get_tmp_path(self.app.profile['username']),
                'bcloud-download-vcode.jpg')
        with open(vcode_path, 'wb') as fh:
            fh.write(request.data)
        self.img.set_from_file(vcode_path)
