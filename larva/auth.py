from larva.config import Config
from flask_httpauth import HTTPTokenAuth
# from flask_httpauth import MultiAuth
from flask_httpauth import HTTPBasicAuth
from flask import g
from . import pam


class Auth(object):
    def __init__(self, app_name="Larva"):
        self.users_db = Config("users_db")
        self.token_db = Config("token_db")
        self.basic_auth = HTTPBasicAuth()
        self.token_auth = HTTPTokenAuth('Token')

        @self.basic_auth.verify_password
        def _verify_password(username, password):
            return self.verify_password(username, password)

        @self.token_auth.verify_token
        def _verify_token(token):
            if token in self.token_db:
                g.username = self.token_db[token]
                g.token = token
                return True
            return False

    def verify_password(self, username, password):
        p = pam.pam()
        if p.authenticate(username, password, service="login"):
            return username
        else:
            return None
