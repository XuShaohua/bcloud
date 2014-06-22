
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

'''
这个模块主要是用于从百度服务器取得cookie授权.
'''

import json
import os
import random
import re
import sys
import urllib.request
from urllib import parse
sys.path.insert(0, os.path.dirname(__file__))

from lxml import html
from lxml.cssselect import CSSSelector as CSS

import const
import encoder
from RequestCookie import RequestCookie
import net
import util


def get_BAIDUID():
    '''获取一个cookie - BAIDUID.

    这里, 我们访问百度首页, 返回的response header里面有我们需要的cookie
    '''
    req = net.urlopen(const.BAIDU_URL)
    if req:
        return req.headers.get_all('Set-Cookie')
    else:
        return None

def get_token(cookie):
    '''获取一个页面访问的token, 这里需要之前得到的BAIDUID 这个cookie值

    这个token的有效期还不确定.
    '''
    url = ''.join([
        const.PASSPORT_URL,
        '?getapi&tpl=mn&apiver=v3',
        '&tt=', util.timestamp(),
        '&class=login&logintype=dialogLogin',
        #'&callback=bd__cbs__d1ypgy',
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        content = content.decode().replace("'", '"')
        content_obj = json.loads(content)
        return content_obj['data']['token']
    else:
        return None

def parse_wap_passport(content):
    form = {}
    tree = html.fromstring(content)
    input_sel = CSS('form input')
    input_elems = input_sel(tree)
    for item in input_elems:
        name = item.attrib.get('name')
        if name and name not in ('changevcode', ):
            form[name] = item.attrib.get('value', '')
    return form

def get_wap_passport():
    '''WAP登录.

    返回cookie和登录form'''
    url = 'http://wappass.baidu.com/passport'
    req = net.urlopen(url)
    if req:
        return (req.headers.get_all('Set-Cookie'),
                parse_wap_passport(req.data.decode()))
    else:
        return None, None

def wap_signin(cookie, form):
    '''进行WAP登录认证'''
    print('wap_signin():', cookie, form)
    url = 'http://wappass.baidu.com/passport/login'
    req = net.urlopen_without_redirect(url, headers={
        'Cookie': cookie.header_output(),
        'Content-Type': const.CONTENT_FORM,
        'Referer': url,
        }, data=parse.urlencode(form).encode())
    if req:
        return req.headers.get_all('Set-Cookie')
    else:
        return None

def get_wap_signin_vcode(cookie, codeString):
    '''获取wap登录时的验证码'''
    url = 'http://wappass.baidu.com/cgi-bin/genimage?' + codeString
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        return req.data
    else:
        return None

def refresh_signin_vcode(cookie, token, vcodetype):
    '''刷新验证码.

    vcodetype - 在调用check_login()时返回的vcodetype.
    '''
    print('refresh_signin_vcode()', cookie, token, vcodetype)
    url = ''.join([
        const.PASSPORT_BASE,
        'v2/?reggetcodestr',
        '&token=', token,
        '&tpl=pp&apiver=v3',
        '&tt=', util.timestamp(),
        '&fr=ligin',
        '&vcodetype=', vcodetype,
        ])
    print('url:', url)
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        try:
            print('req.data is:', req.data)
            return json.loads(req.data.decode('gbk'))
        except ValueError as e:
            print('Error occurs in refresh_signin_vcode()', e)
    return None

def parse_bdstoken(content):
    '''从页面中解析出bdstoken等信息.
    
    这些信息都位于页面底部的<script>, 只有在授权后的页面中才出现.
    这里, 为了保证兼容性, 就不再使用cssselect模块解析了.

    @return 返回bdstoken
    '''
    bdstoken = ''
    bds_re = re.compile('BDSTOKEN\s*=\s*"([^"]+)"')
    bds_match = bds_re.search(content)
    print('bds match:', bds_match)
    if bds_match:
        bdstoken = bds_match.group(1)
    return bdstoken

def get_bdstoken(cookie):
    '''从/disk/home页面获取bdstoken等token信息

    这些token对于之后的请求非常重要.
    '''
    url = const.PAN_REFERER
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        return parse_bdstoken(req.data.decode())
    else:
        return None
