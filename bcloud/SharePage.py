
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gtk

from bcloud import Config
_ = Config._


class SharePage(Gtk.ScrolledWindow):

    icon_name = 'folder-publicshare-symbolic'
    disname = _('Share')
    tooltip = _('Share')
    first_run = False

    def __init__(self, app):
        super().__init__()
        self.app = app
        
    def load(self):
        pass
