
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gtk

from gcloud.Config import _


class OtherPage(Gtk.ScrolledWindow):

    icon_name = 'content-loading-symbolic'
    disname = _('Others')
    tooltip = _('Others')
    page_num = 7

    def __init__(self, app):
        super().__init__()
        self.app = app
