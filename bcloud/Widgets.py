# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html


from gi.repository import Gtk

class LeftLabel(Gtk.Label):
    '''左对齐的标签'''

    def __init__(self, label):
        super().__init__(label)
        self.props.xalign = 0.0

class SelectableLeftLabel(LeftLabel):
    '''左对齐的标签, 标签内容可选中'''

    def __init__(self, label):
        super().__init__(label)
        self.props.selectable = True
