
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import json
import os
import subprocess
import threading

from gi.repository import GdkPixbuf
from gi.repository import GLib
try:
    import keyring
    keyring_imported = True
except ImportError:
    keyring_imported = False

from bcloud import Config
from bcloud import net

PASSWORD_MAGIC_CHAR = 'x'
DEFAULT_PROFILE = {
    'version': Config.VERSION,
    'window-size': (960, 680),
    'use-status-icon': True,
    'use-notify': False,
    'first-run': True,
    'save-dir': Config.HOME_DIR,
    'update-threshold': 1,  # 上传时的阈值, 1~20.
    'concurr-tasks': 2,     # 下载/上传同时进行的任务数, 1~5
    'username': '',
    'password': '',
    'remember-password': False,
    'auto-signin': False,
    }

# calls f on another thread
def async_call(func, *args, callback=None):
    def do_call():
        result = None
        error = None

        try:
            result = func(*args)
        except Exception as e:
            error = e
        if callback:
            GLib.idle_add(callback, result, error)

    thread = threading.Thread(target=do_call)
    thread.start()

def xdg_open(uri):
    '''使用桌面环境中默认的程序打开指定的URI
    
    当然, 除了URI格式之外, 也可以是路径名, 文件名, 比如:
    xdg_open('/etc/issue')
    推荐使用Gio.app_info_xx() 来启动一般程序, 而用xdg_open() 来打开目录.
    '''
    try:
        subprocess.call(['xdg-open', uri, ])
    except FileNotFoundError as e:
        pass
        #print(e)

def update_liststore_image(liststore, tree_iter, col, pcs_file, dir_name):
    '''下载文件缩略图, 并将它显示到liststore里.
    
    pcs_file - 里面包含了几个必要的字段.
    dir_name - 缓存目录, 下载到的图片会保存这个目录里.
    '''
    def _update_image(error=None):
        if error:
            return
        if os.stat(filepath).st_size == 0:
            #print('target image file is empty:', filepath)
            return
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_size(filepath, 96, 96)
            tree_path = liststore.get_path(tree_iter)
            if tree_path is None:
                return
            row = liststore[tree_path]
            if row is None:
                return
            row[col] = pix
        except GLib.GError as e:
            pass
            #print('Error: Net.update_liststore_image:', e, 
            #      'with filepath:', filepath, 'url:', url)

    def _dump_image(req, error=None):
        if error or not req:
            return
        with open(filepath, 'wb') as fh:
            fh.write(req.data)
        _update_image()

    if 'thumbs' not in pcs_file or 'url1' not in pcs_file['thumbs']:
        return
    fs_id = pcs_file['fs_id']
    url = pcs_file['thumbs']['url1']

    if len(url) < 10:
        #print('url is too short')
        return
    filepath = os.path.join(dir_name, '{0}.jpg'.format(fs_id))
    if os.path.exists(filepath) and os.stat(filepath).st_blocks:
        _update_image()
    else:
        async_call(net.urlopen, url, callback=_dump_image)

def ellipse_text(text, length=10):
    if len(text) < length:
        return text
    else:
        return text[:8] + '..'

def load_profile(profile_name):
    '''读取特定帐户的配置信息'''
    path = os.path.join(Config.CONF_DIR, profile_name)
    if not os.path.exists(path):
        return DEFAULT_PROFILE
    with open(path) as fh:
        profile = json.load(fh)
    if profile['password'] == PASSWORD_MAGIC_CHAR and keyring_imported:
        profile['password'] = keyring.get_password(
                Config.DBUS_APP_NAME, profile['username'])
    return profile

def dump_profile(profile):
    '''保存帐户的配置信息.

    这里会检查用户是否愿意保存密码, 如果需要保存密码的话, 就会检查是否存在
    keyring这个模块, 如果存在, 就使用它来管理密码;
    如果不存存, 就会把密码明文存放(这个很不安全).
    '''
    profile = profile.copy()
    path = os.path.join(Config.CONF_DIR, profile['username'])
    if not profile['remember-password']:
        profile['password'] = ''
    elif keyring_imported:
        keyring.set_password(
                Config.DBUS_APP_NAME, profile['username'],
                profile['password'])
        profile['password'] = PASSWORD_MAGIC_CHAR
    else:
        print('警告: 密码被明文存储!')
    with open(path, 'w') as fh:
        json.dump(profile, fh)

def reach_scrolled_bottom(adj):
    '''在ScrolledWindow里面, 滚动到了底部, 就需要尝试载入下一页的内容'''
    return (adj.get_upper() - adj.get_page_size() - adj.get_value()) < 80
