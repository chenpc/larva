from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
import sys

if not os.path.exists('/var/db'):
    os.makedirs('/var/db')
    engine = create_engine('sqlite:////var/db/larva.db', convert_unicode=True)

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
BaseDB = declarative_base()
BaseDB.query = db_session.query_property()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    # import yourapplication.models
    BaseDB.metadata.create_all(bind=engine)