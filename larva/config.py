from larva.database import BaseDB, db_session
from sqlalchemy import Column, String
from sqlalchemy.orm.exc import NoResultFound
import json

class ConfigDB(BaseDB):
    __tablename__ = "config"
    name = Column(String, primary_key=True)
    data = Column(String)

class Config(object):
    def __init__(self, module_name):
        self.db = dict()
        self.name = module_name

        try:
            config = db_session.query(ConfigDB).filter_by(name=module_name).one()
        except NoResultFound:
            config = ConfigDB(name=module_name, data=json.dumps(self.db))
            db_session.add(config)
            db_session.commit()

        self.db = json.loads(config.data)

    def __setitem__(self, key, item):
        self.db[key] = item

    def __getitem__(self, key):
        return self.db[key]

    def __contains__(self, key):
        return key in self.db or key == "save" # XXX dirty hack

    def __delitem__(self, key):
        del self.db[key]

    def save(self):
        config = db_session.query(ConfigDB).filter_by(name=self.name).one()
        config.data = json.dumps(self.db)
        db_session.commit()