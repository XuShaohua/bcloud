
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import gzip
import http
import http.client
import mimetypes
import os
import traceback
import urllib.parse
import urllib.request
import zlib

from bcloud import const
from bcloud.log import logger

RETRIES = 3
TIMEOUT = 50

default_headers = {
    'User-agent': const.USER_AGENT,
    'Referer': const.PAN_REFERER,
    #'x-requested-with': 'XMLHttpRequest',
    'Accept': const.ACCEPT_JSON,
    'Accept-language': 'zh-cn, zh;q=0.5',
    'Accept-encoding': 'gzip, deflate',
    'Pragma': 'no-cache',
    'Cache-control': 'no-cache',
}

def urloption(url, headers={}, retries=RETRIES):
    '''发送OPTION 请求'''
    headers_merged = default_headers.copy()
    for key in headers.keys():
        headers_merged[key] = headers[key]
    schema = urllib.parse.urlparse(url)
    for i in range(retries):
        try:
            conn = http.client.HTTPConnection(schema.netloc)
            conn.request('OPTIONS', url, headers=headers_merged)
            resp = conn.getresponse()
            return resp
        except OSError:
            logger.error(traceback.format_exc())
    return None


class ForbiddenHandler(urllib.request.HTTPErrorProcessor):

    def http_error_403(self, req, fp, code, msg, headers):
        return fp

    http_error_400 = http_error_403
    http_error_500 = http_error_403


def urlopen_simple(url, retries=RETRIES, timeout=TIMEOUT):
    for i in range(retries):
        try:
            return urllib.request.urlopen(url, timeout=timeout)
        except OSError:
            logger.error(traceback.format_exc())
    return None

def urlopen(url, headers={}, data=None, retries=RETRIES, timeout=TIMEOUT):
    '''打开一个http连接, 并返回Request.

    headers 是一个dict. 默认提供了一些项目, 比如User-Agent, Referer等, 就
    不需要重复加入了.

    这个函数只能用于http请求, 不可以用于下载大文件.
    如果服务器支持gzip压缩的话, 就会使用gzip对数据进行压缩, 然后在本地自动
    解压.
    req.data 里面放着的是最终的http数据内容, 通常都是UTF-8编码的文本.
    '''
    headers_merged = default_headers.copy()
    for key in headers.keys():
        headers_merged[key] = headers[key]
    opener = urllib.request.build_opener(ForbiddenHandler)
    opener.addheaders = [(k, v) for k,v in headers_merged.items()]

    for i in range(retries):
        try:
            req = opener.open(url, data=data, timeout=timeout)
            encoding = req.headers.get('Content-encoding')
            req.data = req.read()
            if encoding == 'gzip':
                req.data = gzip.decompress(req.data)
            elif encoding == 'deflate':
                req.data = zlib.decompress(req.data, -zlib.MAX_WBITS)
            return req
        except OSError:
            logger.error(traceback.format_exc())
    return None

def urlopen_without_redirect(url, headers={}, data=None, retries=RETRIES):
    '''请求一个URL, 并返回一个Response对象. 不处理重定向.

    使用这个函数可以返回URL重定向(Error 301/302)后的地址, 也可以重到URL中请
    求的文件的大小, 或者Header中的其它认证信息.
    '''
    headers_merged = default_headers.copy()
    for key in headers.keys():
        headers_merged[key] = headers[key]

    parse_result = urllib.parse.urlparse(url)
    for i in range(retries):
        try:
            conn = http.client.HTTPConnection(parse_result.netloc)
            if data:
                conn.request('POST', url, body=data, headers=headers_merged)
            else:
                conn.request('GET', url, body=data, headers=headers_merged)
            return conn.getresponse()
        except OSError:
            logger.error(traceback.format_exc())
    return None

def post_multipart(url, headers, fields, files, retries=RETRIES):
    content_type, body = encode_multipart_formdata(fields, files)
    schema = urllib.parse.urlparse(url)

    headers_merged = default_headers.copy()
    for key in headers.keys():
        headers_merged[key] = headers[key]
    headers_merged['Content-Type'] = content_type
    headers_merged['Content-length'] = str(len(body))

    for i in range(retries):
        try:
            h = http.client.HTTPConnection(schema.netloc)
            h.request('POST', url, body=body, headers=headers_merged)
            req = h.getresponse()
            encoding = req.getheader('Content-encoding')
            req.data = req.read()
            if encoding == 'gzip':
                req.data = gzip.decompress(req.data)
            elif encoding == 'deflate':
                req.data = zlib.decompress(req.data, -zlib.MAX_WBITS)
            return req
        except OSError:
            logger.error(traceback.format_exc())
    return None

def encode_multipart_formdata(fields, files):
    BOUNDARY = b'----------ThIs_Is_tHe_bouNdaRY_$'
    S_BOUNDARY = b'--' + BOUNDARY
    E_BOUNARY = S_BOUNDARY + b'--'
    CRLF = b'\r\n'
    BLANK = b''
    l = []
    for (key, value) in fields:
        l.append(S_BOUNDARY)
        l.append('Content-Disposition: form-data; name="{0}"'.format(
                key).encode())
        l.append(BLANK)
        l.append(value.encode())
    for (key, filename, content) in files:
        l.append(S_BOUNDARY)
        l.append(
            'Content-Disposition: form-data; name="{0}"; filename="{1}"'.format(
                key, filename).encode())
        l.append(BLANK)
        l.append(content)
    l.append(E_BOUNARY)
    l.append(BLANK)
    body = CRLF.join(l)
    content_type = 'multipart/form-data; boundary={0}'.format(BOUNDARY.decode())
    return content_type, body

def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
