
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gtk

from gcloud import Config
_ = Config._
from gcloud.IconWindow import IconWindow
from gcloud import gutil
from gcloud import pcs

__all__ = [
    'CategoryPage', 'PicturePage', 'DocPage', 'VideoPage',
    'BTPage', 'MusicPage', 'OtherPage',
    ]


class CategoryPage(IconWindow):

    page_num = 1
    first_run = True

    def __init__(self, app):
        super().__init__(self, app)
        self.app = app

    def load(self):
        gutil.async_call(
                pcs.get_category, self.app.cookie, self.app.tokens,
                self.category, self.page_num, callback=super().load)

    def reload(self, *args):
        self.load()

class VideoPage(CategoryPage):

    icon_name = 'folder-videos-symbolic'
    disname = _('Videos')
    tooltip = _('Videos')
    category = 1


class MusicPage(CategoryPage):

    icon_name = 'folder-music-symbolic'
    disname = _('Music')
    tooltip = _('Music')
    category = 2


class PicturePage(CategoryPage):

    icon_name = 'folder-pictures-symbolic'
    disname = _('Pictures')
    tooltip = _('Pictures')
    category = 3


class DocPage(CategoryPage):

    icon_name = 'folder-documents-symbolic'
    disname = _('Documents')
    tooltip = _('Documents')
    category = 4


class OtherPage(CategoryPage):

    icon_name = 'content-loading-symbolic'
    disname = _('Others')
    tooltip = _('Others')
    category = 6


class BTPage(CategoryPage):

    icon_name = 'bittorrent-symbolic'
    disname = _('Bittorrents')
    tooltip = _('BT seeds')
    category = 7
