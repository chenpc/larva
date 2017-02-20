import requests
from functools import partial


def larva_call(host, port, token, module, func, *args, **kwargs):
    headers = {'Authorization': 'Token %s' % token, "Content-Type": "application/json"}
    params = [args, kwargs]
    result = requests.post('http://%s:%d/api/%s/%s' % (host, port, module, func), headers=headers, json=params)
    return result.json()


class LarvaProxy(object):
    def __init__(self, host="127.0.0.1", port=8080, token=None, method=None):
        if token is None:
            r = requests.post('http://%s:%d/auth' % (host, port), auth=('user', 'pass'))
            self.token = r.text
        else:
            self.token = token
        self.method = method
        self.host = host
        self.port = port

    def __getattr__(self, item):
        if self.method:
            return partial(larva_call, self.host, self.port, self.token, self.method, item)
        else:
            return LarvaProxy(self.host, self.port, self.token, method=item)


rpc = LarvaProxy("127.0.0.1", 8080)
res = rpc.hello.test_hello("kk", True, 4)
print(res)

