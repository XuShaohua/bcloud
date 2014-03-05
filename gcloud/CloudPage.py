
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gtk

from gcloud.Config import _


class CloudPage(Gtk.ScrolledWindow):

    icon_name = 'cloud-symbolic'
    disname = _('Cloud')
    tooltip = _('Cloud downloading')
    page_num = 10

    def __init__(self, app):
        super().__init__()
        self.app = app
