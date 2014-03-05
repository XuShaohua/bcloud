
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html


class BasePage(Gtk.ScrolledWindow):

    icon_name = ''
    disname = ''
    tooltip = ''
    page_num = -1

    def __init__(self, app):
        self.app = app
        super().__init__()

    def on_active(self):
        '''当这个页面被激活后, 可能需要更新一些信息'''
        pass

