
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
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


class IconButton(Gtk.Button):
    '''在gtk3.14中, 引入了gtk_button_new_from_icon_name() 这个方法'''

    def __init__(self, icon_name, size=Gtk.IconSize.BUTTON):
        super().__init__()
        img = Gtk.Image.new_from_icon_name(icon_name, size)
        self.set_image(img)
