#!/usr/bin/env python3

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import copy
import gzip
import http
import os
import sys
import urllib.parse
import urllib.request
import zlib

sys.path.insert(0, os.path.dirname(__file__))
import const

default_headers = {
    'User-agent': const.USER_AGENT,
    'Referer': const.PAN_REFERER,
    'x-requested-with': 'XMLHttpRequest',
    'Accept': const.ACCEPT_JSON,
    'Accept-language': 'zh-cn, zh',
    'Accept-encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Cache-control': 'no-cache',
    }

def urlopen(url, headers={}, data=None):
    '''打开一个http连接, 并返回Request.

    headers 是一个dict. 默认提供了一些项目, 比如User-Agent, Referer等, 就
    不需要重复加入了.

    这个函数只能用于http请求, 不可以用于下载大文件.
    如果服务器支持gzip压缩的话, 就会使用gzip对数据进行压缩, 然后在本地自动
    解压.
    req.data 里面放着的是最终的http数据内容, 通常都是UTF-8编码的文本.
    '''
    headers_merged = copy.copy(default_headers)
    for key in headers.keys():
        headers_merged[key] = headers[key]
    opener = urllib.request.build_opener()
    opener.addheaders = [(k, v) for k,v in headers_merged.items()]

    req = opener.open(url, data=data)
    encoding = req.headers.get('Content-encoding')
    req.data = req.read()
    if encoding == 'gzip':
        req.data = gzip.decompress(req.data)
    elif encoding == 'deflate':
        req.data = zlib.decompress(req.data, -zlib.MAX_WBITS)
    return req

#class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
#
#    def http_error_302(self, req, fp, code, msg, headers):
#        if 'location' in headers:
#            return headers['location']
#        elif 'uri' in headers:
#            return headers['uri']
#        else:
#            return ''
#
#    http_error_301 = http_error_302
#    http_error_303 = http_error_302
#    http_error_307 = http_error_302

#def urlopen_without_redirect(url, headers={}, data=None):
#    '''不处理重定向, 直接返回重定向后的地址
#    
#    在下载大文件时, 网盘服务器会进行一次302重定向, 如果不手动修改一下cookie,
#    就会被限速.
#    '''
#    headers_merged = copy.copy(default_headers)
#    for key in headers.keys():
#        headers_merged[key] = headers[key]
#    opener = urllib.request.build_opener(NoRedirectHandler)
#    opener.addheaders = [(k, v) for k,v in headers_merged.items()]
#
#    req = opener.open(url, data=data)
#    if isinstance(req, str):
#        return req
#    else:
#        return url

def urlopen_without_redirect(url, headers={}, data=None):
    '''使用HEAD方法请求一个URL, 并返回一个Response对象.

    HEAD 方法只会要求服务器返回Response Header, 并不返回Response Body,
    因为有时候我们只需要这个Response Header.
    使用这个函数可以返回URL重定向(Error 301/302)后的地址, 也可以重到URL中请
    求的文件的大小, 或者Header中的其它认证信息.
    '''
    headers_merged = copy.copy(default_headers)
    for key in headers.keys():
        headers_merged[key] = headers[key]

    parse_result = urllib.parse.urlparse(url)
    conn = http.client.HTTPConnection(parse_result.netloc)
    conn.request('HEAD', url, body=data, headers=headers_merged)
    return conn.getresponse()
