
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import base64

def decode_flashget(link):
    l = base64.decodestring(link[11:len(link)-7].encode()).decode()
    return l[10:len(l)-10]

def decode_thunder(link):
    # AAhttp://127.0.0.1
    if link.startswith('QUFodHRwOi8vMTI3LjAuMC4'):
        return ''
    l = base64.decodestring(link[10:].encode()).decode()
    return l[2:-2]

def decode_qqdl(link):
    return base64.decodestring(link[7:].encode()).decode()

_router = {
    'flashge': decode_flashget,
    'thunder': decode_thunder,
    'qqdl://': decode_qqdl,
    }

def decode(link):
    if not isinstance(link, str) or len(link) < 10:
        return ''
    lower_pref = link[:7].lower()
    if lower_pref in _router:
        return _router[lower_pref](link)
    else:
        return ''
