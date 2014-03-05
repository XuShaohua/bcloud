
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gtk

from gcloud.Config import _

class HomePage(Gtk.Box):

    icon_name = 'go-home-symbolic'
    disname = _('Home')
    tooltip = _('Show all of your files on Cloud')
    page_num = 1

    def __init__(self, app):
        super().__init__()
        self.app = app

        label = Gtk.Label('fuck')
        self.pack_start(label, False, False, 0)
