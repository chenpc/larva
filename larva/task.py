import threading
from flask import g
from werkzeug.local import Local
local = Local()

def get_session():
    return local

def run_task(username, task, cb):
    local.username = username # XXX not all attrs are copied in to local

    (func, args, kwargs) = task
    func(*args, **kwargs)

    if cb:
        (func, args, kwargs) = cb
        func(*args, **kwargs)

class Task(object):
    def __init__(self, func, *args, **kwargs):
        self.task = (func, args, kwargs)
        self.cb = None


    def callback(self, func, *args, **kwargs):
        self.cb = (func, args, kwargs)

    def start(self):
        t = threading.Thread(target=run_task, args=(g.username, self.task, self.cb))
        t.start()


