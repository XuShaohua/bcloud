
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gtk

from gcloud.Config import _

class TrashPage(Gtk.ScrolledWindow):

    icon_name = 'user-trash-symbolic'
    disname = _('Trash')
    tooltip = _('Files deleted.')
    page_num = 9

    def __init__(self, app):
        super().__init__()
        self.app = app
