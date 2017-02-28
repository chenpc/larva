import requests
from functools import partial
import pickle
import json
import base64
import sys

def larva_call(host, port, token, module, func, *args, **kwargs):
    headers = {'Authorization': 'Token %s' % token, "Content-Type": "application/json", "pickle": "yes"}
    params = [args, kwargs]
    result = requests.post('http://%s:%d/api/%s/%s' % (host, port, module, func), headers=headers, json=params)
    result = result.json()

    if result['status']:
        return result['data']
    else:
        p = result['error_pickle'][1:]
        b64= base64.b64decode(p)
        e = pickle.loads(b64)
        tb = result['error_tb']

        for t in tb:
            print(t, end='', file=sys.stderr)
        raise e



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

class TestException(Exception):
    pass

rpc = LarvaProxy("127.0.0.1", 8080)
try:
    res = rpc.hello.test_hello("kk", True, 4)
    print(res)
except Exception as e:
    print("aError")
