#!/usr/bin/env python3

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

from distutils.core import setup
from distutils.core import Command
from distutils.command.clean import clean as distutils_clean
from distutils.command.sdist import sdist as distutils_sdist
import glob
import os
import shutil

from gcloud import Config

def build_data_files():
    data_files = []
    for dir, dirs, files in os.walk('share'):
        target = dir
        if files:
            files = [os.path.join(dir, f) for f in files]
            data_files.append((target, files))
    return data_files

scripts = ['bcloud-gui', ]

if __name__ == '__main__':
    setup(
        name = Config.NAME,
        description = 'Baidu Pan client for Linux Desktop users',
        version = Config.VERSION,
        license = 'GPLv3',
        url = Config.HOMEPAGE,

        author = 'LiuLang',
        author_email = 'gsushzhsosgsu@gmail.com',

        packages = ['bcloud', ],
        scripts = scripts,
        data_files = build_data_files(),
        )
