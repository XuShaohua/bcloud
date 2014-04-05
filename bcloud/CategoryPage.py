
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud.IconWindow import IconWindow
from bcloud import gutil
from bcloud import pcs

__all__ = [
    'CategoryPage', 'PicturePage', 'DocPage', 'VideoPage',
    'BTPage', 'MusicPage', 'OtherPage',
    ]


class CategoryPage(IconWindow):

    page_num = 1
    has_next = True
    first_run = True

    def __init__(self, app):
        super().__init__(self, app)
        self.app = app
        self.icon_window = super()

    def load(self):
        def on_load(info, error=None):
            if error or not info or info['errno'] != 0:
                return
            self.icon_window.load(info['info'])

        has_next = True
        self.page_num = 1
        gutil.async_call(
                pcs.get_category, self.app.cookie, self.app.tokens,
                self.category, self.page_num, callback=on_load)

    def load_next(self):
        def on_load_next(info, error=None):
            if error or not info or info['errno'] != 0:
                return
            if info['info']:
                self.icon_window.load_next(info['info'])
            else:
                self.has_next = False

        if not self.has_next:
            return
        self.page_num = self.page_num + 1
        gutil.async_call(
                pcs.get_category, self.app.cookie, self.app.tokens,
                self.category, self.page_num, callback=on_load_next)

    def reload(self, *args):
        self.load()

class VideoPage(CategoryPage):

    icon_name = 'videos-symbolic'
    disname = _('Videos')
    tooltip = _('Videos')
    category = 1


class MusicPage(CategoryPage):

    icon_name = 'music-symbolic'
    disname = _('Music')
    tooltip = _('Music')
    category = 2


class PicturePage(CategoryPage):

    icon_name = 'pictures-symbolic'
    disname = _('Pictures')
    tooltip = _('Pictures')
    category = 3


class DocPage(CategoryPage):

    icon_name = 'documents-symbolic'
    disname = _('Documents')
    tooltip = _('Documents')
    category = 4


class OtherPage(CategoryPage):

    icon_name = 'others-symbolic'
    disname = _('Others')
    tooltip = _('Others')
    category = 6


class BTPage(CategoryPage):

    icon_name = 'bittorrent-symbolic'
    disname = _('BT')
    tooltip = _('BT seeds')
    category = 7
