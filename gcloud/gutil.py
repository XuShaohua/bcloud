# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html


import threading

from gi.repository import GObject

# calls f on another thread
def async_call(func, *args, callback=None):
    def do_call():
        result = None
        error = None

        try:
            result = func(*args)
        except Exception as e:
            error = e
        if callback:
            GObject.idle_add(lambda: callback(result, error))

    thread = threading.Thread(target=do_call)
    thread.start()
