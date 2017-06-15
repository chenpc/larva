from functools import wraps
from decorator import decorate
from gevent.lock import BoundedSemaphore as Lock

class Atomic(object):
    def __init__(self):
        self.local_lock = Lock()
        self.g_lock = Lock()
        self.m_lock = dict()
        self.f_lock = dict()
        self.n_lock = dict()

    def giant_lock(self, f):
        def do_function(func, *args, **kwargs):
            g_lock = self.g_lock
            try:
                g_lock.acquire()
                result = func(*args, **kwargs)
            finally:
                g_lock.release()

            return result
        return decorate(f, do_function)

    def module_lock(self, f):
        def do_function(func, module, *args, **kwargs):
            self.local_lock.acquire()
            module_name = module.__class__.__name__
            if module_name not in self.m_lock:
                m_lock = self.m_lock[module_name] = Lock()
            else:
                m_lock = self.m_lock[module_name]
            self.local_lock.release()

            try:
                m_lock.acquire()
                result = func(module, *args, **kwargs)
            finally:
                m_lock.release()

            return result
        return decorate(f, do_function)

    def function_lock(self, f):
        def do_function(func, module, *args, **kwargs):
            self.local_lock.acquire()
            lock_name = module.__class__.__name__ + "-" + func.__name__
            print(lock_name)
            if lock_name not in self.f_lock:
                f_lock = self.f_lock[lock_name] = Lock()
            else:
                f_lock = self.f_lock[lock_name]
            self.local_lock.release()

            try:
                f_lock.acquire()
                result = func(module, *args, **kwargs)
            finally:
                f_lock.release()

            return result
        return decorate(f, do_function)

    def namespace_lock(self, name):
        def fun_wrap(func):
            def do_function(*args, **kwargs):
                self.g_lock.acquire()
                if name not in self.n_lock:
                    n_lock = self.n_lock[name] = Lock()
                else:
                    n_lock = self.n_lock[name]
                self.g_lock.release()

                try:
                    n_lock.acquire()
                    result = func(*args[1:], **kwargs) # XXX, too hard to write this line.
                finally:
                    n_lock.release()
                print("exit lock")
                return result
            return decorate(func, do_function)
        return fun_wrap

atomic = Atomic()
