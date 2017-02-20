import requests
from functools import partial


r = requests.post('http://127.0.0.1:8080/auth', auth=('user', 'pass'))
token = r.text


def larva_call(module, func, *args, **kwargs):
    global token
    headers = {'Authorization': 'Token %s' % token, "Content-Type": "application/json"}
    params = [args, kwargs]
    result = requests.post('http://127.0.0.1:8080/api/%s/%s' % (module, func), headers=headers, json=params)
    return result.text


class LarvaProxy(object):
    def __init__(self, method=None):
        self.method = method

    def __getattr__(self, item):
        if self.method:
            return partial(larva_call, self.method, item)
        else:
            return LarvaProxy(item)


rpc = LarvaProxy()
res = rpc.hello.test_hello("kk", True, 4)
print(res)

