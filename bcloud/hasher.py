
# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import hashlib
import os
import zlib

CHUNK = 2 ** 20


def crc(path):
    _crc = 0
    fh = open(path, 'rb')
    while True:
        chunk = fh.read(CHUNK)
        if not chunk:
            break
        _crc = zlib.crc32(chunk, _crc)
    fh.close()
    return '%X' % (_crc & 0xFFFFFFFF)

def md5(path, start=0, stop=-1):
    _md5 = hashlib.md5()
    fh = open(path, 'rb')
    if start > 0:
        fh.seek(start)
    if stop == -1:
        stop = os.path.getsize(path)
    pos = start
    while pos < stop:
        size = min(CHUNK, stop - pos)
        chunk = fh.read(size)
        if not chunk:
            break
        pos += len(chunk)
        _md5.update(chunk)
    fh.close()
    return _md5.hexdigest()

def sha1(path):
    _sha1 = hashlib.sha1()
    fh = open(path, 'rb')
    while True:
        chunk = fh.read(CHUNK)
        if not chunk:
            break
        _sha1.update(chunk)
    fh.close()
    return _sha1.hexdigest()

def sha224(path):
    _sha224 = hashlib.sha224()
    fh = open(path, 'rb')
    while True:
        chunk = fh.read(CHUNK)
        if not chunk:
            break
        _sha224.update(chunk)
    fh.close()
    return _sha224.hexdigest()

def sha256(path):
    _sha256 = hashlib.sha256()
    fh = open(path, 'rb')
    while True:
        chunk = fh.read(CHUNK)
        if not chunk:
            break
        _sha256.update(chunk)
    fh.close()
    return _sha256.hexdigest()

def sha384(path):
    _sha384 = hashlib.sha384()
    fh = open(path, 'rb')
    while True:
        chunk = fh.read(CHUNK)
        if not chunk:
            break
        _sha384.update(chunk)
    fh.close()
    return _sha384.hexdigest()

def sha512(path):
    _sha512 = hashlib.sha512()
    fh = open(path, 'rb')
    while True:
        chunk = fh.read(CHUNK)
        if not chunk:
            break
        _sha512.update(chunk)
    fh.close()
    return _sha512.hexdigest()
