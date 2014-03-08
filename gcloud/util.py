#!/usr/bin/env python3

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import datetime
import os
import random
import time

SIZE_K = 2 ** 10
SIZE_M = 2 ** 20
SIZE_G = 2 ** 30
SIZE_T = 2 ** 40
DESI_K = SIZE_K / 10
DESI_M = SIZE_M / 10
DESI_G = SIZE_G / 10
DESI_T = SIZE_T / 10

def timestamp():
    '''返回当前的时间标记, 以毫秒为单位'''
    return str(int(time.time() * 1000))

def latency():
    '''返回操作时消耗的时间.

    这个值是0.1-1之前的五位小数, 用于跟踪服务器的响应时间.
    我们需要随机生成它.
    '''
    return str(random.random())[:7]

def rec_split_path(path):
    '''将一个路径进行分隔, 分别得到每父母的绝对路径及目录名'''
    result = []
    while path != '/':
        parent, name = os.path.split(path)
        result.append((path, name))
        path = parent
    result.append(('/', '/'))
    result.reverse()
    return result

def get_human_size(size):

    '''将文件大小转为人类可读的形式'''
    size_kb = '{0:,}'.format(size)
    if size < DESI_K:
        return ('{0} B'.format(size), size_kb)
    if size < DESI_M:
        return ('{0:.1f} kB'.format(size / SIZE_K), size_kb)
    if size < DESI_G:
        return ('{0:.1f} MB'.format(size / SIZE_M), size_kb)
    if size < DESI_T:
        return ('{0:.1f} GB'.format(size / SIZE_G), size_kb)
    return ('{0:.1f} TB'.format(size / SIZE_T), size_kb)

def get_delta_days(from_sec, to_sec):
    '''计算两个时间节点之间的日期'''
    seconds = abs(to_sec - from_sec)
    delta = datetime.timedelta(seconds=seconds)
    return delta.days

if __name__ == '__main__':
    num = 3022788
    num = 684
    print(get_human_size(num))
