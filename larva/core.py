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
import pickle
import base64
import sys
import traceback

from collections import OrderedDict
from larva.config import Config
from larva.task import local
from sqlalchemy.orm.query import Query
# For Database
from larva.database import db_session, init_db
root_path = os.path.dirname(os.path.abspath(__file__))


class InitMeta(type):
    def __init__(self, name, bases, attrs, **kwargs):
        self.config = Config(name)
        return super().__init__(name, bases, attrs)

class LarvaObject(object, metaclass=InitMeta):
    pass

class Object(object):
    pass

function_inspect_table = OrderedDict()


class ModuleNameError(NameError):
    pass


class FunctionNameError(NameError):
    pass


def parse_doc(function_desc):
    htmltype = {"str": "text", "int": "number", "boolean": "select", "datetime": "datetime-local",
                "list": "text", "dict": "text"}
    section_keyword = {"Args", "Returns", "Raises"}
    result = OrderedDict()
    sep_data = function_desc.__doc__.splitlines() # XXX expandtab??
    args, varg, karg, defaults = (inspect.getargspec(function_desc))
    if defaults is None:
        defaults = []
    default_table = OrderedDict(zip(args[-len(defaults):], defaults))

    result['description'] = sep_data[0]
    field = ""
    if function_desc in function_inspect_table:
        return function_inspect_table[function_desc]

    for line in sep_data[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = len(line) - len(stripped)
            if indent == 8:  # 2 tabs
                field = stripped.split(":")[0]
                if field not in section_keyword:
                    result[field] = ""
                else:
                    result[field] = OrderedDict()
            elif indent >= 12 and field != "": # 3 tabs
                if field not in section_keyword:
                    result[field] = result[field] + line[12:] + "\n"
                    continue
                value = OrderedDict()
                token_list = stripped.split(":")
                value['description'] = token_list[1]

                # enum, func
                if len(token_list) > 2:
                    query_type, query_args = stripped[len(token_list[0]) + len(token_list[1])+2:].split('=')

                    value[query_type] = json.loads(query_args, object_pairs_hook=OrderedDict)

                name = stripped.split(":")[0].split("(")[0]

                value['type'] = stripped.split(":")[0].split("(")[1][:-1]

                if field == "Args":
                    value['htmltype'] = htmltype[value['type']]
                    if name in default_table:
                        value['default'] = default_table[name]
                result[field][name]=value

    function_inspect_table[function_desc] = result
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
    if type(req_obj) == dict:
        if 'Args' in doc:
            for p, v in doc['Args'].items():
                if v['type'] == 'datetime':
                    datestring = req_obj[p]
                    req_obj[p] = dateutil.parser.parse(datestring)
                elif v['type'] == 'list' or v['type'] == 'dict':
                    if p in req_obj:
                        if isinstance(req_obj[p], list) or isinstance(req_obj[p], dict):
                            req_obj[p] = req_obj[p]
                        else:
                            json_string = req_obj[p]
                            req_obj[p] = json.loads(json_string, object_pairs_hook=OrderedDict)
        return None, req_obj
    else:
        args = req_obj[0]
        kwargs = req_obj[1]
        return args, kwargs


def parse_orm(query):
    res = dict()
    q = query
    if 'limit' in request.headers:
        limit  = int(request.headers['limit'])
        q = q.limit(limit)
        if 'page' in request.headers:
            page = int(request.headers.get('page'))
            q = q.offset(page * limit)

    db_list = db_session.execute(q).fetchall()
    keys = db_session.execute(q).keys()
    res = list()
    for db in db_list:
        data = OrderedDict(zip(keys, db))
        res.append(data)
    return res


def parse_page(res):
    output = OrderedDict()

    if 'limit' in request.headers:
        limit  = int(request.headers['limit'])
        page = int(request.headers.get('page'))

        if isinstance(res, OrderedDict):
            tmp = list(res)
            tmp = tmp[page*limit: (page+1)*limit]

            # Create new Ordereddict
            for t in tmp:
                output[t] = res[t]
        return output
    else:
        return res



class ModuleAutoStarter():
    real_modules = dict()
    started_modules = dict()

    def __getattr__(self, item):
        if item not in self.started_modules:
            self.started_modules[item] = False
            if hasattr(self.real_modules[item], '_start'):
                self.real_modules[item]._start()
            self.started_modules[item] = True
        elif self.started_modules[item] is False:
            raise RecursionError('%s can not be _start twice' % item)
        return self.real_modules[item]

    def __setattr__(self, key, value):
        self.real_modules[key] = value

    def start(self, item):
        if item not in self.started_modules:
            self.started_modules[item] = False
            self.real_modules[item]._start()
            self.started_modules[item] = True

class Larva:
    def __init__(self, modules_list, host=None, port=None, app_name="Larva", auth=None, logger=None):
        print("Init Larva")
        self.host = host
        self.port = port
        self.modules = ModuleAutoStarter()
        self.object_list = list()

        if logger is None:
            import logging
            logger = logging.getLogger("larva")

        if auth:
            self.auth = auth
        else:
            from larva.auth import Auth
            self.auth = Auth(app_name)

        for m in modules_list:
            self.object_list.append(m())

        for m in self.object_list:
            m.modules = self.modules
            setattr(self.modules, m.__class__.__name__.lower(), m)

        for m in self.object_list:
            if hasattr(m, '_start'):
                self.modules.start(m.__class__.__name__.lower())

        self.app = Flask(app_name, root_path=root_path, static_folder="files")

        @self.app.teardown_appcontext
        def shutdown_session(exception=None):
            db_session.remove()

        @self.app.route('/api/system/info', methods=['GET'])
        def system_info():
            module = getattr(self.modules, "system")
            func = getattr(module, "info")
            result = OrderedDict()
            result['data'] = parse_page(func())
            result['status'] = True
            return json.dumps(result, default=larva_format)


        @self.app.route('/api/<module_name>/<func_name>', methods=['POST'])
        @self.auth.token_auth.login_required
        def api(module_name, func_name):
            t = timeit.Timer()
            result = OrderedDict()
            args = []
            kwargs = {}
            local.username = g.username
            local.token = g.token

            try:
                if not hasattr(self.modules, module_name):
                    raise ModuleNameError("No such module")

                module = getattr(self.modules, module_name)
                if not hasattr(module, func_name):
                    raise FunctionNameError("No such function")

                f = getattr(module, func_name)
                if len(request.files) == 0:
                    args, kwargs = parse_request(f, request)
                else:
                    args=None
                    kwargs=request.files.to_dict()


                if args:
                    ret = f(*args, **kwargs)
                else:
                    ret = f(**kwargs)

                # Answer from DB
                if isinstance(ret, Query):
                    result['data'] = parse_orm(ret)
                    if 'limit' in request.headers:
                        result['total_count'] = str(ret.count())
                        result['page'] = request.headers['page']
                        result['limit'] = request.headers['limit']

                # Answer from normal function return
                else:
                    result['data'] = parse_page(ret)
                    if isinstance(ret, dict) or isinstance(ret, list):
                        result['total_count'] = len(ret)
                    else:
                        result['total_count'] = 0

                result['status'] = True

            except Exception as e:
                result['error_module'] = module_name
                result['error_func'] = func_name
                result['error_type'] = e.__class__.__name__
                result['error_args'] = e.args
                result['status'] = False
                exc_type, exc_value, exc_traceback = sys.exc_info()
                tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
                result['error_tb'] = tb

                # XXX log this
                for line in tb:
                    print(line, end='')

            result['duration'] = round(t.timeit(), 6)

            if module_name != "event":
                log_msg = json.dumps((module_name, func_name, kwargs, result), default=larva_format)
                logger.debug("larve-core: "+ log_msg)

            # Handle all non serializable token as string
            return json.dumps(result, default=larva_format)

        @self.app.route('/auth', methods=['POST'])
        @self.auth.basic_auth.login_required
        def auth():
            user = self.auth.basic_auth.username()
            return self.get_auth(user)

        @self.app.route('/get_auth', methods=['GET'])
        def auth_get():
            result = OrderedDict()
            username = request.args.get('username')
            password = request.args.get('password')
            user = self.auth.verify_password(username, password)
            result['token'] = self.get_auth(user)
            return json.dumps(result, default=larva_format)

        @self.app.route('/doc', methods=['GET'])
        def doc(module_name=None, func_name=None):
            result = OrderedDict()
            for k in self.modules.real_modules:
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
            for k in self.modules.real_modules:
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
            for k in self.modules.real_modules:
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

    def get_auth(self, user):
        if user is not None:
            if user in self.auth.users_db:
                return self.auth.users_db[user]
            else:
                uid = str(uuid.uuid4())
                self.auth.users_db[user] = uid
                self.auth.token_db[uid] = user
                self.auth.users_db.save()
                self.auth.token_db.save()
                return uid
        else:
            return None

    def run(self):
        self.app.run(host=self.host, port=self.port)

    def __del__(self):
        for m in self.object_list:
            if hasattr(m, '__del__'):
                m.__del__()


