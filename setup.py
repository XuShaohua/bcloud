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
import sys

import bcloud

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
    assert sys.version_info.major > 2, 'Only works with python3'
    setup(
        name = 'bcloud',
        description = 'Baidu Pan client for Linux Desktop users',
        version = bcloud.__version__,
        license = 'GPLv3',
        url = 'https://github.com/LiuLang/bcloud',

        author = 'LiuLang',
        author_email = 'gsushzhsosgsu@gmail.com',

        packages = ['bcloud', ],
        scripts = scripts,
        data_files = build_data_files(),

        platforms = 'any',
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Environment :: X11 Applications :: GTK',
            'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
            'Natural Language :: Chinese (Simplified)',
            'Natural Language :: Chinese (Traditional)',
            'Natural Language :: English',
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.2',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Topic :: Communications :: File Sharing',
            ],
        )
