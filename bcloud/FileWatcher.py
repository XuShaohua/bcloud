import os
import time
import pyinotify
from queue import Queue, Empty, Full
from threading import Thread
from pyinotify import IN_CREATE, IN_DELETE, IN_ACCESS, IN_CLOSE_NOWRITE, IN_CLOSE_WRITE, IN_MODIFY, IN_MOVED_FROM, IN_MOVED_TO, IN_OPEN 


# MASK = IN_CREATE|IN_DELETE|IN_ACCESS|IN_CLOSE_NOWRITE|IN_CLOSE_WRITE|IN_MODIFY|IN_MOVED_FROM|IN_MOVED_TO|IN_OPEN 
MASK = IN_CREATE

class EventHandler(pyinotify.ProcessEvent):

    def __init__(self, source, upload_func, limiter):
        super(EventHandler, self).__init__()
        self.source = source
        self.upload_func = upload_func
        self.limiter = limiter

    def process_IN_CREATE(self, event):
        if os.path.isfile(event.pathname):
            remotepath = self.process_Remote_Path(event.pathname)
            # self.limiter.put_task((event.pathname, remotepath))
            self.upload_func(event.pathname, remotepath)

    def process_Remote_Path(self, pathname):
        return os.path.dirname(pathname[len(self.source):])


    def process_IN_DELETE(self, event):
        print("Deleteing", event.pathname)


    def process_IN_CLOSE_NOWRITE(self, event):
        print("closenowrite", event.pathname)

    def process_IN_CLOSE_WRITE(self, event):
        print("IN_CLOSE_WRITE", event.pathname)

    def process_IN_MODIFY(self, event):
        print("IN_MODIFY", event.pathname)

    def process_IN_MOVED_FROM(self, event):
        print("move from", event.pathname)

    def process_IN_MOVED_TO(self, event):
        print("in_moved_to", event.pathname)

    def process_IN_OPEN(self, event):
        print("OPEN FILE", event.pathname)

class WatchFileChange(Thread):


    def __init__(self, monitor_path, upload_func):

        super(WatchFileChange, self).__init__()
        self.setDaemon(True)
        self.monitor_path = monitor_path
        self.upload_func = upload_func
        self.limiter = TaskLimiter(self.upload_func)
        self.handler = EventHandler(self.monitor_path, self.upload_func, self.limiter)
        self.wm = pyinotify.WatchManager()
        self.notifyer = pyinotify.Notifier(self.wm, self.handler)
   
    def stop(self):
        self.wm.close()
        self.notifyer.stop()
        self.limiter.stop()

    def run(self):
        # self.limiter.start()
        self.wm.add_watch(self.monitor_path, MASK, rec=True, auto_add=True)
        self.notifyer.loop()

class TaskLimiter(Thread):

    def __init__(self, upload_func):
        super(TaskLimiter, self).__init__()
        self.queue = Queue(10000)
        self.setDaemon(True)
        self.runflag = True
        self.upload_func = upload_func

    def put_task(self, task):
        for retry in range(3):
            try:
                self.queue.put_nowait(task)
            except Full:
                pass

    def stop(self):
        self.runflag = False
    
    def batch_get(self, num):
        tasks = []
        try:
            for i in range(num):
                task = self.queue.get_nowait()
                tasks.append(task)
        except Empty:
            pass
        return tasks

    def run(self):
        while self.runflag:
            tasks = self.batch_get(50)
            for task in tasks:
                source, dest = task
                self.upload_func(source, dest)
            time.sleep(0.5)
