from larva.config import Config
from flask_httpauth import HTTPTokenAuth
# from flask_httpauth import MultiAuth
from flask_httpauth import HTTPBasicAuth
from flask import g

class Auth(object):
    def __init__(self, app_name="Larva"):
        self.users_db = Config("users_db")
        self.token_db = Config("token_db")
        self.basic_auth = HTTPBasicAuth()
        self.token_auth = HTTPTokenAuth('Token')

        @self.basic_auth.verify_password
        def verify_password(username, password):
            return username

        @self.token_auth.verify_token
        def verify_token(token):
            g.username = "root"
            return True