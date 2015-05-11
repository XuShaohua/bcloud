#!/bin/sh

# Copyright (C) 2014-2015 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

if [ "$0" = "./tools/i18n.sh" ]; then
  PO_DIR='./po'
elif [ "$0" = "./i18n.sh" ]; then
  PO_DIR='../po'
else
  echo 'Please run this script in bcloud/ folder'
  exit 1
fi
cd $PO_DIR || exit 1

POT_FILE="bcloud.pot"

printf "Please choose what to do: 
    1) generate bcloud.pot
    2) merge bcloud.pot into po files
    3) generate mo files
    q) quit
"
read choice

if [ "$choice" = 1 ]; then
  xgettext --language=Python \
           --keyword=_ \
           --from-code=UTF-8 \
           --output "$POT_FILE" \
           ../bcloud/*.py
elif [ "$choice" = 2 ]; then
  msgmerge zh_CN.po "$POT_FILE" --update
  msgmerge zh_TW.po "$POT_FILE" --update
elif [ "$choice" = 3 ]; then
  msgfmt --output-file=../share/locale/zh_CN/LC_MESSAGES/bcloud.mo zh_CN.po
  msgfmt --output-file=../share/locale/zh_TW/LC_MESSAGES/bcloud.mo zh_TW.po
else
  echo 'quit...'
  exit 0
fi

