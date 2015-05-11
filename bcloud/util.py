
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import base64
import datetime
import hashlib
import json
import os
import random
import re
import traceback
import urllib.parse
import time

from bcloud.const import ValidatePathState
from bcloud.log import logger
try:
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
except (ImportError, ValueError):
    logger.error(traceback.format_exc())

SIZE_K = 2 ** 10
SIZE_M = 2 ** 20
SIZE_G = 2 ** 30
SIZE_T = 2 ** 40

def timestamp():
    '''返回当前的时间标记, 以毫秒为单位'''
    return str(int(time.time() * 1000))

def curr_time():
    now = datetime.datetime.now()
    return datetime.datetime.strftime(now, '%Y%m%d%H%M%S')

def latency():
    '''返回操作时消耗的时间.

    这个值是0.1-1之前的五位小数, 用于跟踪服务器的响应时间.
    我们需要随机生成它.
    '''
    return str(random.random())[:7]

def get_human_size(size, use_giga=True):
    '''将文件大小由byte, 转为人类可读的字符串
    size     -  整数, 文件的大小, 以byte为单位
    use_giga - 如果这个选项为False, 那最大的单位就是MegaBytes, 而不会用到
               GigaBytes, 这个在显示下载进度时很有用, 因为可以动态的显示下载
               状态.
    '''
    size_kb = '{0:,}'.format(size)
    if size < SIZE_K:
        return ('{0} B'.format(size), size_kb)
    if size < SIZE_M:
        return ('{0:.1f} kB'.format(size / SIZE_K), size_kb)
    if size < SIZE_G or not use_giga:
        return ('{0:.1f} MB'.format(size / SIZE_M), size_kb)
    if size < SIZE_T:
        return ('{0:.1f} GB'.format(size / SIZE_G), size_kb)
    return ('{0:.1f} TB'.format(size / SIZE_T), size_kb)

def get_delta_days(from_sec, to_sec):
    '''计算两个时间节点之间的日期'''
    seconds = abs(to_sec - from_sec)
    delta = datetime.timedelta(seconds=seconds)
    return delta.days

def get_human_time(t):
    '''将时间标记转换成字符串'''
    if isinstance(t, int):
        # ignore micro seconds
        if len(str(t)) == 13:
            t = t // 1000
        t = datetime.datetime.fromtimestamp(t)
    return datetime.datetime.strftime(t, '%Y-%m-%d %H:%M:%S')

def get_recent_mtime(t):
    '''获取更精简的时间.

    如果是当天的, 就返回时间; 如果是当年的, 就近回月份和日期; 否则返回完整的时间
    '''
    if isinstance(t, int):
        # ignore micro seconds
        if len(str(t)) == 13:
            t = t // 1000
        t = datetime.datetime.fromtimestamp(t)
    now = datetime.datetime.now()
    delta = now - t
    if delta.days == 0:
        return datetime.datetime.strftime(t, '%H:%M:%S')
    elif now.year == t.year:
        return datetime.datetime.strftime(t, '%b %d')
    else:
        return datetime.datetime.strftime(t, '%b %d %Y')

def rec_split_path(path):
    '''将一个路径进行分隔, 分别得到每父母的绝对路径及目录名'''
    if len(path) > 1 and path.endswith('/'):
        path = path[:-1]
    if '/' not in path:
        return [path,]
    result = []
    while path != '/':
        parent, name = os.path.split(path)
        result.append((path, name))
        path = parent
    result.append(('/', '/'))
    result.reverse()
    return result

def list_remove_by_index(l, index):
    '''将list中的index位的数据删除'''
    if index < 0 or index >= len(l):
        raise ValueError('index out of range')
    if index == (len(l) - 1):
        l.pop()
    elif index == 0:
        l = l[1:]
    else:
        l = l[0:index] + l[index+1:]

    return l

def uri_to_path(uri):
    if not uri or len(uri) < 7:
        return ''
    return urllib.parse.unquote(uri[7:])

def uris_to_paths(uris):
    '''将一串URI地址转为绝对路径, 用于处理桌面程序中的文件拖放'''
    source_paths = []
    for uri in uris:
        source_path = uri_to_path(uri)
        if source_path:
            source_paths.append(source_path)
    return source_paths

def natsort(string):
    '''按照语言里的意义对字符串进行排序.

    这个方法用于替换按照字符编码顺序对字符串进行排序.
    相关链接:
    http://stackoverflow.com/questions/2545532/python-analog-of-natsort-function-sort-a-list-using-a-natural-order-algorithm
    http://www.codinghorror.com/blog/2007/12/sorting-for-humans-natural-sort-order.html
    '''
    return [int(s) if s.isdigit() else s for s in re.split('(\d+)', string)]

def RSA_encrypt(public_key, message):
    '''用RSA加密字符串.

    public_key - 公钥
    message    - 要加密的信息, 使用UTF-8编码的字符串
    @return    - 使用base64编码的字符串
    '''
    # 如果没能成功导入RSA模块, 就直接返回空白字符串.
    if not globals().get('RSA'):
        return ''
    rsakey = RSA.importKey(public_key)
    rsakey = PKCS1_v1_5.new(rsakey)
    encrypted = rsakey.encrypt(message.encode())
    return base64.encodestring(encrypted).decode().replace('\n', '')

def m3u8_to_m3u(pls):
    output = ['#EXTM3U']
    srcs_set = set()
    for line in pls.decode().split('\n'):
        if line.startswith('#') or not line:
            continue
        src = line[line.find('src='):]
        url = line[:line.find('start=')] + src
        if src not in srcs_set:
            srcs_set.add(src)
            output.append(url)
    return '\n'.join(output)

def json_loads_single(s):
    '''处理不标准JSON结构化数据'''
    try:
        return json.loads(s.replace("'", '"').replace('\t', ''))
    except (ValueError, UnicodeDecodeError):
        logger.error(traceback.format_exc())
        return None

def validate_pathname(filepath):
    '''检查路径中是否包含特殊字符.

    百度网盘对路径/文件名的要求很严格:
      1. 路径长度限制为1000
      2. 路径中不能包含以下字符：\\ ? | " > < : *
      3. 文件名或路径名开头结尾不能是“.”或空白字符，空白字符包括: \r, \n, \t, 空格, \0, \x0B

    @return, 返回的状态码: 0 表示正常

    '''
    if filepath == '/':
        return ValidatePathState.OK
    if len(filepath) > 1000:
        return ValidatePathState.LENGTH_ERROR
    filter2 = '\\?|"><:*'
    for c in filter2:
        if c in filepath:
            return ValidatePathState.CHAR_ERROR2
    paths = rec_split_path(filepath)
    filter3 = '.\r\n\t \0\x0b'
    for path in paths:
        if path[0] in filter3 or path[-1] in filter3:
            return ValidatePathState.CHAR_ERROR3
    return ValidatePathState.OK
