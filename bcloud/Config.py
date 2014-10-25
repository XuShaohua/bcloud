
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import gettext
import json
import os

from gi.repository import Gdk
from gi.repository import Gtk

import bcloud

HOME_DIR = os.path.expanduser('~')
LOCAL_DIR = os.path.join(HOME_DIR, '.local')
if __file__.startswith('/usr/local/'):
    PREF = '/usr/local/share'
elif __file__.startswith('/usr/'):
    PREF = '/usr/share'
elif __file__.startswith(LOCAL_DIR):
    PREF = os.path.join(LOCAL_DIR, 'share')
else:
    PREF = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'share')

NAME = 'bcloud'
ICON_PATH = os.path.join(PREF, NAME, 'icons')
COLOR_SCHEMA = os.path.join(PREF, NAME, 'color_schema.json')

LOCALEDIR = os.path.join(PREF, 'locale')
gettext.bindtextdomain(NAME, LOCALEDIR)
gettext.textdomain(NAME)
_ = gettext.gettext

DBUS_APP_NAME = 'org.liulang.bcloud'
APPNAME = 'BCloud'
VERSION = bcloud.__version__
HOMEPAGE = 'https://github.com/LiuLang/bcloud'
# 这里只列出了提交代码在三次以上的开发者, 完整的开发者信息可以在
# https://github.com/LiuLang/bcloud/pulls 查看
AUTHORS = [
    'LiuLang <gsushzhsosgsu@gmail.com>',
    'CzBiX <czbix@live.com>',
]
COPYRIGHT = 'Copyright (c) 2014 LiuLang'
DESCRIPTION = _('Baidu Pan client for GNU/Linux desktop users.')

CACHE_DIR = os.path.join(HOME_DIR, '.cache', NAME)

# Check Gtk version <= 3.6
GTK_LE_36 = (Gtk.MAJOR_VERSION == 3) and (Gtk.MINOR_VERSION <= 6)
GTK_GE_312 = (Gtk.MAJOR_VERSION == 3) and (Gtk.MINOR_VERSION >= 12)

CONF_DIR = os.path.join(HOME_DIR, '.config', NAME)
_conf_file = os.path.join(CONF_DIR, 'conf.json')

_base_conf = {
    'default': '',
    'profiles': [],
}

def check_first():
    '''这里, 要创建基本的目录结构'''
    if not os.path.exists(CONF_DIR):
        os.makedirs(CONF_DIR, exist_ok=True)
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)

def load_conf():
    '''获取基本设定信息, 里面存放着所有可用的profiles, 以及默认的profile'''
    if os.path.exists(_conf_file):
        with open(_conf_file) as fh:
            return json.load(fh)
    else:
        dump_conf(_base_conf)
        return _base_conf

def dump_conf(conf):
    with open(_conf_file, 'w') as fh:
        json.dump(conf, fh)

def get_cache_path(profile_name):
    '''获取这个帐户的缓存目录, 如果不存在, 就创建它'''
    path = os.path.join(CACHE_DIR, profile_name, 'cache')
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def get_tmp_path(profile_name):
    '''获取这个帐户的临时文件目录, 可以存放验证码图片, 上传时的文件分片等'''
    path = os.path.join(CACHE_DIR, profile_name, 'tmp')
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def load_color_schema():
    if not os.path.exists(COLOR_SCHEMA):
        return []
    with open(COLOR_SCHEMA) as fh:
        color_list = json.load(fh)

    schema = []
    for color in color_list:
        rgba = Gdk.RGBA()
        rgba.red = int(color[:2], base=16) / 255
        rgba.green = int(color[2:4], base=16) / 255
        rgba.blue = int(color[4:6], base=16) / 255
        rgba.alpha = int(color[6:], base=16) / 255
        schema.append(rgba)
    return schema
