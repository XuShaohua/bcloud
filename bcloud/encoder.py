
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

'''This module contains some useful functions to handle encoding/decoding

just like escape(), encodeURLComponent()... in javascript.
'''

import base64
import hashlib
import json
from urllib import parse

def md5(text):
    return hashlib.md5(text.encode()).hexdigest()

def sha1(text):
    return hashlib.sha1(text.encode()).hexdigest()

def sha224(text):
    return hashlib.sha224(text.encode()).hexdigest()

def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()

def sha384(text):
    return hashlib.sha384(text.encode()).hexdigest()

def sha512(text):
    return hashlib.sha512(text.encode()).hexdigest()

def base64_encode(text):
    return base64.b64encode(text.encode()).decode()

def base64_decode(text):
    try:
        return base64.b64decode(text.encode()).decode()
    except Exception as e:
        return ''

def url_split_param(text):
    return text.replace('&', '\n&')

def url_param_plus(text):
    url = parse.urlparse(text)
    output = []
    if len(url.scheme) > 0:
        output.append(url.scheme)
        output.append('://')
    output.append(url.netloc)
    output.append(url.path)
    if len(url.query) > 0:
        output.append('?')
        output.append(url.query.replace(' ', '+'))
    return ''.join(output)

def escape(text):
    return parse.quote(text)

def unescape(text):
    return parse.unquote(text)

def encode_uri(text):
    return parse.quote(text, safe='~@#$&()*!+=:;,.?/\'')

def decode_uri(text):
    return parse.unquote(text)

def encode_uri_component(text):
    return parse.quote(text, safe='~()*!.\'')

def decode_uri_component(text):
    return parse.unquote(text)

def json_beautify(text):
    try:
        return json.dumps(json.loads(text), indent=4)
    except Exception as e:
        return ''
