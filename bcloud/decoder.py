
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import base64
import traceback

from bcloud.log import logger

def decode_flashget(link):
    try:
        l = base64.decodestring(link[11:len(link)-7].encode()).decode()
    except ValueError:
        logger.warn(traceback.format_exc())
        l = base64.decodestring(link[11:len(link)-7].encode()).decode('gbk')
    return l[10:len(l)-10]

def decode_thunder(link):
    # AAhttp://127.0.0.1
    if link.startswith('QUFodHRwOi8vMTI3LjAuMC4'):
        return ''
    try:
        l = base64.decodestring(link[10:].encode()).decode('gbk')
    except ValueError:
        logger.warn(traceback.format_exc())
        l = base64.decodestring(link[10:].encode()).decode()
    return l[2:-2]

def decode_qqdl(link):
    try:
        return base64.decodestring(link[7:].encode()).decode()
    except ValueError:
        logger.warn(traceback.format_exc())
        return base64.decodestring(link[7:].encode()).decode('gbk')

_router = {
    'flashge': decode_flashget,
    'thunder': decode_thunder,
    'qqdl://': decode_qqdl,
}

def decode(link):
    if not isinstance(link, str) or len(link) < 10:
        logger.error('unknown link: %s' % link)
        return ''
    link_prefix = link[:7].lower()
    if link_prefix in _router:
        try:
            return _router[link_prefix](link)
        except ValueError:
            logger.error(traceback.format_exc())
            return ''
    else:
        logger.warn('unknown protocol: %s' % link)
        return ''
