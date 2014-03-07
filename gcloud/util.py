#!/usr/bin/env python3

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os
import random
import time

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


def main():
    print(rec_split_path('/usr/share/icons/gnome'))

if __name__ == '__main__':
    main()
