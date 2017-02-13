#!/usr/bin/env python3
from flask import Flask, g
from flask import render_template
from flask import request, Response, session

import os
import json
import inspect
import timeit
import uuid
import datetime
import dateutil.parser

from collections import OrderedDict
from larva.config import Config
from larva.auth import Auth
from larva.task import local
from larva.log import Event, log

# For Database
from larva.database import db_session, init_db

root_path = os.path.dirname(os.path.abspath(__file__))


class Object(object):
    pass

function_inspect_table = OrderedDict()


def parse_doc(function):
    htmltype = {"str": "text", "int": "number", "boolean": "checkbox", "datetime": "datetime-local"}
    result = OrderedDict()
    sep_data = function.__doc__.splitlines() # XXX expandtab??
    args, varg, karg, defaults = (inspect.getargspec(function))
    if defaults is None:
        defaults = []
    default_table = OrderedDict(zip(args[-len(defaults):], defaults))

    result['description'] = sep_data[0]
    field = ""
    if function in function_inspect_table:
        return function_inspect_table[function]

    for line in sep_data[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = len(line) - len(stripped)
            if indent == 8: # 2 tabs
                field=  stripped.split(":")[0]
                result[field] = OrderedDict()
            elif indent == 12 and field != "": # 3 tabs
                value = OrderedDict()
                value['description'] = stripped.split(":")[1]
                name = stripped.split(":")[0].split("(")[0]
                value['type'] = stripped.split(":")[0].split("(")[1][:-1]
                value['htmltype'] = htmltype[value['type']]
                if name in default_table:
                    value['default'] = default_table[name]
                result[field][name]=value

    function_inspect_table[function] = result
    return result


def larva_format(json_token):
    if hasattr(json_token, "isoformat"):
        return json_token.isoformat()
    elif hasattr(json_token, "to_json"):
        return json_token.to_json()
    else:
        return str(json_token)


def parse_request(func, req):
    doc = parse_doc(func)
    req_obj = req.json

    if 'Args' in doc:
        for p, v in doc['Args'].items():
            if v['type'] == 'datetime':
                datestring = req_obj[p]
                req_obj[p] = dateutil.parser.parse(datestring)
    return req_obj


class Larva:
    def __init__(self, modules_list, host=None, port=None, app_name="Larva", auth=None, config=None):
        print("Init Larva")
        self.host = host
        self.port = port
        self.modules = Object()

        init_db()

        if auth:
            self.auth = auth
        else:
            self.auth = Auth(app_name)

        modules_list.append(Event())
        for m in sorted(modules_list, key= lambda m:m.__class__.__name__):
            if config:
                m.config = config(m.__class__.__name__)
            else:
                m.config = Config(m.__class__.__name__)

            m.modules = self.modules
            setattr(self.modules, m.__class__.__name__.lower(), m)

        self.app = Flask(app_name, root_path=root_path)

        @self.app.teardown_appcontext
        def shutdown_session(exception=None):
            db_session.remove()

        @self.app.route('/api/<module_name>/<func_name>', methods=['POST'])
        @self.auth.token_auth.login_required
        def api(module_name, func_name):
            t = timeit.Timer()
            result = OrderedDict()

            local.username = g.username
            f = getattr(getattr(self.modules, module_name), func_name)
            kwargs = parse_request(f, request)
            try:
                ret = f(**kwargs)
                result['data'] = ret
                result['status'] = True

            except Exception as e:
                result['error_module'] = module_name
                result['error_func'] = func_name
                result['error_type'] = e.__class__.__name__
                result['error_args'] = e.args
                result['status'] = False

            # Save Config
            m.config.save()

            result['duration'] = round(t.timeit(), 6)

            if module_name != "event":
                log.log_info("larva-core", json.dumps((module_name, func_name, kwargs, result), default=larva_format))

            # Handle all non serializable token as string
            return json.dumps(result, default=larva_format)

        @self.app.route('/auth', methods=['POST'])
        @self.auth.basic_auth.login_required
        def auth():
            user = self.auth.basic_auth.username()
            if user in self.auth.users_db:
                return self.auth.users_db[user]

            uid = str(uuid.uuid4())
            self.auth.users_db[user] = uid
            self.auth.token_db[uid] = user
            self.auth.users_db.save()
            self.auth.token_db.save()
            return uid

        @self.app.route('/', methods=['GET'])
        def doc(module_name=None, func_name=None):
            result = OrderedDict()
            for k in self.modules.__dict__:
                if k not in result:
                    result[k] = OrderedDict()
                m = getattr(self.modules, k)
                for km in dir(m):
                    if km[0] != '_' and callable(getattr(m, km)):
                        result[k][km] = parse_doc(getattr(m, km))

            return render_template('apidoc.html', doc=result, time=datetime.datetime.now().isoformat())

        @self.app.route('/', methods=['POST'])
        def post_doc():
            result = OrderedDict()
            for k in self.modules.__dict__:
                if k not in result:
                    result[k] = OrderedDict()
                m = getattr(self.modules, k)
                for km in dir(m):
                    if km[0] != '_' and callable(getattr(m, km)):
                        result[k][km] = parse_doc(getattr(m, km))
            return json.dumps(result, default=larva_format)

        @self.app.route('/doc', methods=['POST'])
        def module_list():
            result = OrderedDict()
            for k in self.modules.__dict__:
                result.append(k)
            return json.dumps(result, default=larva_format)

        @self.app.route('/doc/<module_name>', methods=['POST'])
        def function_list(module_name):
            result = OrderedDict()
            m = getattr(self.modules, module_name)
            for k in m.__dict__:
                if k[0] != '_':
                    result[k]= parse_doc(getattr(self.modules[module_name], k))['description']
            return json.dumps(result, default=larva_format)

    def run(self):
        self.app.run(host=self.host, port=self.port)

