
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gtk

from gcloud.Config import _


class PicturePage(Gtk.ScrolledWindow):

    icon_name = 'folder-pictures-symbolic'
    disname = _('Pictures')
    tooltip = _('Pictures')
    page_num = 2

    def __init__(self, app):
        super().__init__()
        self.app = app
