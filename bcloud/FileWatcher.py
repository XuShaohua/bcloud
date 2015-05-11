
# Copyright (C) 2015 Alexzhang <alex8224@gmail.com>

import os
from threading import Thread, Lock
from time import time, sleep

import pyinotify
from pyinotify import ALL_EVENTS
from bcloud import gutil
from bcloud import pcs


MASK = ALL_EVENTS

class EventHandler(pyinotify.ProcessEvent):

    def __init__(self, source, bcloud_app, task_queue):
        super().__init__()
        self.source = source
        self.bcloud_app = bcloud_app
        self.task_queue = task_queue
        self.cloud_root = bcloud_app.profile['dest-sync-dir']

    def process_IN_CREATE(self, event):
        if not event.dir:
            self.process_IN_CLOSE_WRITE(event)

    def process_Remote_Path(self, pathname, dir=False):
        if dir:
            return os.path.join(self.cloud_root, pathname[len(self.source)+1:])
        else:
            return os.path.join(self.cloud_root,
                                os.path.dirname(pathname[len(self.source)+1:]))


    def is_valid_filename(self, filename):
        invalid_prefixs = ('.', '~', '#')
        invalid_suffixs = ('.swp', '.crdownload')
        not_startwith = lambda prefix: not filename.startswith(prefix)
        not_endwith = lambda suffix: not filename.endswith(suffix)
        
        return (all(map(not_startwith, invalid_prefixs)) and
                all(map(not_endwith, invalid_suffixs)))

    def process_IN_DELETE(self, event):
        if event.dir:
            remotepath = self.process_Remote_Path(event.pathname, True)
        else:
            remotepath = os.path.join(self.process_Remote_Path(event.pathname),
                                      event.name)

        gutil.async_call(pcs.delete_files, self.bcloud_app.cookie,
                         self.bcloud_app.tokens, [remotepath],
                         callback=lambda noop:noop)

    def process_IN_CLOSE_WRITE(self, event):
        if not event.dir and self.is_valid_filename(event.name):
            remotepath = self.process_Remote_Path(event.pathname)
            #self.bcloud_app.uploa_page.add_bg_task(event.pathname, remotepath)
            self.task_queue.submit((event.pathname, remotepath))

    def process_IN_MOVED_FROM(self, event):
        self.process_IN_DELETE(event)

    def process_IN_MOVED_TO(self, event):
        self.process_IN_CLOSE_WRITE(event)


class WatchFileChange(Thread):

    def __init__(self, monitor_path, bcloud_app):

        super(WatchFileChange, self).__init__()
        self.setDaemon(True) 
        self.monitor_path = monitor_path 
        self.bcloud_app = bcloud_app
        self.submitter = TaskSubmitter(self.bcloud_app)
        self.submitter.start()
        self.handler = EventHandler(self.monitor_path, self.bcloud_app,
                                    self.submitter)
        self.wm = pyinotify.WatchManager()
        self.wdds = self.wm.add_watch(self.monitor_path, MASK, rec=True,
                                      auto_add=True)
        self.notifyer = pyinotify.Notifier(self.wm, self.handler)
   
    def stop(self):
        try:
            self.wm.close()
            self.notifyer.stop()
            self.submitter.stop()
        except OSError:
            pass

    def run(self):
        self.notifyer.loop()


class TaskSubmitter(Thread):

    def __init__(self, bcloud_app):
        super().__init__()
        self.setDaemon(True) 
        self.runflag = 1
        self.bcloud_app = bcloud_app
        self.lock = Lock()
        self.queue = set()
        self.last = time()

    def submit(self, task):
        with self.lock:
            self.queue.add(task)
            self.last = time()

    def qsize(self):
        with self.lock:
            return len(self.queue)

    def stop(self):
        self.runflag = 0

    def run(self):
        while self.runflag:
            if time() - self.last > 5 and self.qsize() > 0:
                with self.lock:
                    tasks = list(self.queue)
                    self.queue.clear()

                while len(tasks) > 0:
                    pathname, remotepath = tasks.pop(0)
                    self.bcloud_app.upload_page.add_bg_task(pathname,
                                                            remotepath)
                self.last = time()    
            else:
                sleep(1)
