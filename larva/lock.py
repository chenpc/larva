from functools import wraps
from decorator import decorate
from threading import Lock

class Atomic(object):
    def __init__(self):
        self.local_lock = Lock()
        self.g_lock = Lock()
        self.m_lock = dict()
        self.f_lock = dict()
        self.n_lock = dict()

    def giant_lock(self, f):
        def do_function(func, *args, **kwargs):
            with self.g_lock:
                result = func(*args, **kwargs)
                return result
        return decorate(f, do_function)

    def module_lock(self, f):
        def do_function(func, module, *args, **kwargs):
            with self.local_lock:
                module_name = module.__class__.__name__
                if module_name not in self.m_lock:
                    m_lock = self.m_lock[module_name] = Lock()
                else:
                    m_lock = self.m_lock[module_name]

            with m_lock:
                result = func(module, *args, **kwargs)
                return result
        return decorate(f, do_function)

    def function_lock(self, f):
        def do_function(func, module, *args, **kwargs):
            with self.local_lock:
                lock_name = module.__class__.__name__ + "-" + func.__name__
                if lock_name not in self.f_lock:
                    f_lock = self.f_lock[lock_name] = Lock()
                else:
                    f_lock = self.f_lock[lock_name]

            with f_lock:
                result = func(module, *args, **kwargs)
                return result
        return decorate(f, do_function)

    def namespace_lock(self, name):
        def fun_wrap(func):
            def do_function(*args, **kwargs):
                with self.local_lock:
                    if name not in self.n_lock:
                        n_lock = self.n_lock[name] = Lock()
                    else:
                        n_lock = self.n_lock[name]
                with n_lock:
                    result = func(*args[1:], **kwargs) # XXX, too hard to write this line.
                    return result
            return decorate(func, do_function)
        return fun_wrap

atomic = Atomic()
