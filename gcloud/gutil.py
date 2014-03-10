
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os
import subprocess
import threading

from gi.repository import GdkPixbuf
from gi.repository import GLib
from gcloud import net

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
        print(e)

def update_liststore_image(liststore, tree_iter, col, pcs_file, dir_name):
    '''下载文件缩略图, 并将它显示到liststore里.
    
    pcs_file - 里面包含了几个必要的字段.
    dir_name - 缓存目录, 下载到的图片会保存这个目录里.
    '''
    def _update_image(error=None):
        if error:
            return
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_size(filepath, 96, 96)
            tree_path = liststore.get_path(tree_iter)
            liststore[tree_path][col] = pix
        except GLib.GError as e:
            print('Error: Net.update_liststore_image:', e, 
                  'with filepath:', filepath, 'url:', url)

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
        print('url is to short')
        return
    filepath = os.path.join(dir_name, '{0}.jpg'.format(fs_id))
    if os.path.exists(filepath):
        _update_image()
    else:
        async_call(net.urlopen, url, callback=_dump_image)
