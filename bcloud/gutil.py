
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import json
import os
import subprocess
import threading
import time
import traceback

import dbus
from gi.repository import GdkPixbuf
from gi.repository import Gtk
from gi.repository import GLib

from bcloud import Config
from bcloud.log import logger
from bcloud import net
from bcloud import pcs
from bcloud import util
try:
    import keyring
    keyring_available = True
    try:
        keyring.set_password("test", "utest", "ptest");
        keyring.get_password("test", "utest");
        keyring.delete_password("test", "utest");
    except:
        keyring_available = False
except (ImportError, ValueError):
    logger.warn(traceback.format_exc())
    keyring_available = False

DEFAULT_PROFILE = {
    'window-size': (960, 680),
    'use-status-icon': True,
    'use-dark-theme': False, # 默认禁用深色主题
    'display-avatar': True,  # 是否显示用户头像
    'use-notify': True,
    'first-run': True,
    'save-dir': Config.HOME_DIR,
    'sync-dir': Config.HOME_DIR,
    'dest-sync-dir': '/',
    'enable-sync': False,
    'use-streaming': True,  # 使用流媒体方式播放视频
    'username': '',
    'password': '',
    'remember-password': False,
    'auto-signin': False,
    'upload-hidden-files': True,  # 同时上传隐藏文件.
    'concurr-tasks': 2,     # 下载/上传同时进行的任务数, 1~5
    'download-segments': 3, # 下载单个任务的线程数 1~10
    'retries-each': 5,      # 隔5分钟后尝试重新下载
    'download-timeout': 60, # 60 秒后下载超时
    'download-mode': 0,     # 下载时如果本地已存在同名文件时的操作方式
    'upload-mode': 0,       # 上传时如果服务器端已存在同名文件时的操作方式
    'view-mode': {          # 保存的视图模式
        'HomePage': 0,
        'CategoryPage': 0,
        'BTPage': 0,
        'OtherPage': 0,
        'DocPage': 0,
        'PicturePage': 0,
        'MusicPage': 0,
        'VideoPage': 0,
    },
}
RETRIES = 3   # 调用keyring模块与libgnome-keyring交互的尝试次数
AVATAR_UPDATE_INTERVAL = 604800  # 用户头像更新频率, 默认是7天


def async_call(func, *args, callback=None):
    '''Call `func` in background thread, and then call `callback` in Gtk main thread.

    If error occurs in `func`, error will keep the traceback and passed to
    `callback` as second parameter. Always check `error` is not None.
    '''
    def do_call():
        result = None
        error = None

        try:
            result = func(*args)
        except Exception:
            error = traceback.format_exc()
            logger.error(error)
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
    except FileNotFoundError:
        logger.error(traceback.format_exc())

def update_liststore_image(liststore, tree_iters, col, pcs_files, dir_name,
                           icon_size=96):
    '''下载文件缩略图, 并将它显示到liststore里.
    
    pcs_files - 里面包含了几个必要的字段.
    dir_name  - 缓存目录, 下载到的图片会保存这个目录里.
    size      - 指定图片的缩放大小, 默认是96px.
    '''
    def update_image(filepath, tree_iter):
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_size(filepath, icon_size,
                                                         icon_size)
            tree_path = liststore.get_path(tree_iter)
            if tree_path is None:
                return
            liststore[tree_path][col] = pix
        except GLib.GError:
            logger.error(traceback.format_exc())

    def dump_image(url, filepath):
        req = net.urlopen(url)
        if not req or not req.data:
            logger.warn('update_liststore_image(), failed to request %s' % url)
            return False
        with open(filepath, 'wb') as fh:
            fh.write(req.data)
        return True

    for tree_iter, pcs_file in zip(tree_iters, pcs_files):
        if 'thumbs' not in pcs_file:
            continue
        if 'url1' in pcs_file['thumbs']:
            key = 'url1'
        elif 'url2' in pcs_file['thumbs']:
            key = 'url2'
        elif 'url3' in pcs_file['thumbs']:
            key = 'url3'
        else:
            continue
        fs_id = pcs_file['fs_id']
        url = pcs_file['thumbs'][key]
        filepath = os.path.join(dir_name, '{0}.jpg'.format(fs_id))
        if os.path.exists(filepath) and os.path.getsize(filepath):
            GLib.idle_add(update_image, filepath, tree_iter)
        elif not url or len(url) < 10:
            logger.warn('update_liststore_image(), failed to get url')
        else:
            status = dump_image(url, filepath)
            if status:
                GLib.idle_add(update_image, filepath, tree_iter)

def update_share_image(liststore, tree_iters, col, large_col, pcs_files,
                       dir_name, icon_size, large_icon_size):
    '''下载文件缩略图, 并将它显示到liststore里.

    需要同时更新两列里的图片, 用不同的缩放尺寸.
    pcs_files - 里面包含了几个必要的字段.
    dir_name  - 缓存目录, 下载到的图片会保存这个目录里.
    '''
    def update_image(filepath, tree_iter):
        try:
            tree_path = liststore.get_path(tree_iter)
            if tree_path is None:
                return
            pix = GdkPixbuf.Pixbuf.new_from_file(filepath)
            width = pix.get_width()
            height = pix.get_height()
            small_pix = pix.scale_simple(icon_size,
                                         height * icon_size // width,
                                         GdkPixbuf.InterpType.NEAREST)
            liststore[tree_path][col] = small_pix
            liststore[tree_path][large_col] = pix 
        except GLib.GError:
            logger.error(traceback.format_exc())

    def dump_image(url, filepath):
        req = net.urlopen(url)
        if not req or not req.data:
            logger.warn('update_share_image:, failed to request %s' % url)
            return False
        with open(filepath, 'wb') as fh:
            fh.write(req.data)
        return True

    for tree_iter, pcs_file in zip(tree_iters, pcs_files):
        if 'thumbs' not in pcs_file:
            continue
        elif 'url2' in pcs_file['thumbs']:
            key = 'url2'
        elif 'url1' in pcs_file['thumbs']:
            key = 'url1'
        elif 'url3' in pcs_file['thumbs']:
            key = 'url3'
        else:
            continue
        fs_id = pcs_file['fs_id']
        url = pcs_file['thumbs'][key]
        filepath = os.path.join(dir_name, 'share-{0}.jpg'.format(fs_id))
        if os.path.exists(filepath) and os.path.getsize(filepath):
            GLib.idle_add(update_image, filepath, tree_iter)
        elif not url or len(url) < 10:
            logger.warn('update_share_image: failed to get url %s' % url)
        else:
            status = dump_image(url, filepath)
            if status:
                GLib.idle_add(update_image, filepath, tree_iter)

def update_avatar(cookie, tokens, dir_name):
    '''获取用户头像信息'''
    uk = pcs.get_user_uk(cookie, tokens)
    if not uk:
        return None
    user_info = pcs.get_user_info(tokens, uk)
    if not user_info:
        return None
    img_path = os.path.join(dir_name, 'avatar.jpg')
    if (os.path.exists(img_path) and
            time.time() - os.stat(img_path).st_mtime <= AVATAR_UPDATE_INTERVAL):
        return (uk, user_info['uname'], img_path)
    img_url = user_info['avatar_url']
    if not img_url:
        return None
    req = net.urlopen(img_url)
    if not req or not req.data:
        logger.warn('gutil.update_avatar(), failed to request %s' % url)
        return None
    with open(img_path, 'wb') as fh:
        fh.write(req.data)
    return (uk, user_info['uname'], img_path)

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

    global keyring_available
    if keyring_available:
        for i in range(RETRIES):
            try:
                profile['password'] = keyring.get_password(
                        Config.DBUS_APP_NAME, profile['username'])
                break
            except (keyring.errors.InitError, dbus.exceptions.DBusException):
                logger.error(traceback.format_exc())
        else:
            keyring_available = False
    if not profile['password']:
        profile['password'] = ''
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
                keyring.set_password(Config.DBUS_APP_NAME, profile['username'],
                                     profile['password'])
                break
            except dbus.exceptions.DBusException:
                logger.error(traceback.format_exc())
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
