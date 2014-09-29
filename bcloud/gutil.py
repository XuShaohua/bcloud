
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import json
import os
import subprocess
import threading

import dbus
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib
try:
    import keyring
except (ImportError, ValueError) as e:
    print(e, ', keyring will be disabled')

from bcloud import Config
from bcloud import net
from bcloud import util

DEFAULT_PROFILE = {
    'window-size': (960, 680),
    'use-status-icon': True,
    'use-dark-theme': False, # 默认禁用深色主题
    'use-notify': True,
    'first-run': True,
    'save-dir': Config.HOME_DIR,
    'use-streaming': True,  # 使用流媒体方式播放视频
    'username': '',
    'password': '',
    'remember-password': False,
    'auto-signin': False,
    'upload-hidden-files': True,  # 同时上传隐藏文件.
    'concurr-tasks': 2,     # 下载/上传同时进行的任务数, 1~5
    'download-segments': 3, # 下载单个任务的线程数 1~5
    'retries-each': 5,      # 隔5分钟后尝试重新下载
    'download-timeout': 30, # 30 秒后下载超时
    }
RETRIES = 5   # 调用keyring模块与libgnome-keyring交互的尝试次数

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
    thread.daemon = True
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
        print(e)

def update_liststore_image(liststore, tree_iter, col, pcs_file,
                           dir_name, icon_size=96):
    '''下载文件缩略图, 并将它显示到liststore里.
    
    pcs_file - 里面包含了几个必要的字段.
    dir_name - 缓存目录, 下载到的图片会保存这个目录里.
    size     - 指定图片的缩放大小, 默认是96px.
    '''
    def _update_image():
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    filepath, icon_size, icon_size)
            tree_path = liststore.get_path(tree_iter)
            if tree_path is None:
                return
            liststore[tree_path][col] = pix
        except GLib.GError as e:
            pass

    def _dump_image(req, error=None):
        if error or not req:
            return
        with open(filepath, 'wb') as fh:
            fh.write(req.data)
        # Now, check its mime type
        file_ = Gio.File.new_for_path(filepath)
        file_info = file_.query_info(
                Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE,
                Gio.FileQueryInfoFlags.NONE)
        content_type = file_info.get_content_type()
        if 'image' in content_type:
            _update_image()

    if 'thumbs' not in pcs_file:
        return
    if 'url1' in pcs_file['thumbs']:
        key = 'url1'
    elif 'url2' in pcs_file['thumbs']:
        key = 'url2'
    else:
        return
    fs_id = pcs_file['fs_id']
    url = pcs_file['thumbs'][key]

    filepath = os.path.join(dir_name, '{0}.jpg'.format(fs_id))
    if os.path.exists(filepath) and os.path.getsize(filepath):
        _update_image()
    else:
        if not url or len(url) < 10:
            return
        async_call(net.urlopen, url, callback=_dump_image)

def ellipse_text(text, length=10):
    if len(text) < length:
        return text
    else:
        return text[:8] + '..'

def load_profile(profile_name):
    '''读取特定帐户的配置信息

    有时, dbus会出现连接错误, 这里会进行重试. 但如果超过最大尝试次数, 就
    会失效, 此时, profile['password'] 是一个空字符串, 所以在下一步, 应该去
    检查一下password是否有效, 如果无效, 应该提醒用户.
    '''
    path = os.path.join(Config.CONF_DIR, profile_name)
    if not os.path.exists(path):
        return DEFAULT_PROFILE
    with open(path) as fh:
        profile = json.load(fh)

    for key in DEFAULT_PROFILE:
        if key not in profile:
            profile[key] = DEFAULT_PROFILE[key]

    if globals().get('keyring'):
        for i in range(RETRIES):
            try:
                profile['password'] = keyring.get_password(
                        Config.DBUS_APP_NAME, profile['username'])
                break
            except dbus.exceptions.DBusException as e:
                print(e)
    return profile

def dump_profile(profile):
    '''保存帐户的配置信息.

    这里会检查用户是否愿意保存密码, 如果需要保存密码的话, 就调用keyring来存
    放密码.
    但如果密码为空, 就不再存放它了.
    '''
    profile = profile.copy()
    path = os.path.join(Config.CONF_DIR, profile['username'])
    if profile['remember-password'] and profile['password']:
        for i in range(RETRIES):
            try:
                keyring.set_password(
                        Config.DBUS_APP_NAME, profile['username'],
                        profile['password'])
                break
            except dbus.exceptions.DBusException as e:
                print(e)
    profile['password'] = ''
    with open(path, 'w') as fh:
        json.dump(profile, fh)

def reach_scrolled_bottom(adj):
    '''在ScrolledWindow里面, 滚动到了底部, 就需要尝试载入下一页的内容'''
    return (adj.get_upper() - adj.get_page_size() - adj.get_value()) < 80

def tree_model_natsort(model, row1, row2, user_data=None):
    '''用natural sorting算法对TreeModel的一个column进行排序'''
    sort_column, sort_type = model.get_sort_column_id()
    value1 = model.get_value(row1, sort_column)
    value2 = model.get_value(row2, sort_column)
    sort_list1 = util.natsort(value1)
    sort_list2 = util.natsort(value2)
    status = sort_list1 < sort_list2
    if sort_list1 < sort_list2:
        return -1
    else:
        return 1

def escape(tooltip):
    '''Escape special characters in tooltip text'''
    return GLib.markup_escape_text(tooltip)

def text_buffer_get_all_text(buf):
    '''Get all text in a GtkTextBuffer'''
    return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
