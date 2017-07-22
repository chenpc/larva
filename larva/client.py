import requests
from functools import partial
import json
from collections import OrderedDict
import builtins
requests.packages.urllib3.disable_warnings()



class LarvaError(Exception):
    def __init__(self, name, args):
        self.name = name
        self.args = args


def larva_call(host, port, token, module, func, *args, **kwargs):
    headers = {'Authorization': 'Token %s' % token, "Content-Type": "application/json"}
    params = [args, kwargs]
    result = requests.post('https://%s:%d/api/%s/%s' % (host, port, module, func), headers=headers, json=params, verify=False)
    result = json.loads(result.text, object_pairs_hook=OrderedDict)

    if result['status']:
        return result['data']
    else:
        tb = result['error_tb']
        if hasattr(builtins, result['error_type']):
            e = getattr(builtins, result['error_type'])
            raise e(result['error_args'])
        raise LarvaError(result['error_type'], result['error_args'])


class LarvaProxy(object):
    def __init__(self, host="127.0.0.1", port=443, username=None, password=None, token=None, method=None):
        if token is None:
            r = requests.post('https://%s:%d/auth' % (host, port), auth=(username, password), verify=False)
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
            return LarvaProxy(self.host, self.port, token=self.token, method=item)
