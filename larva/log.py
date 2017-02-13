from larva.database import BaseDB, db_session
from sqlalchemy import Column, Integer, String, Boolean, DateTime, desc
import datetime
from larva.task import get_session
import json

log_level = ['critical', 'error', 'warning', 'info', 'debug']
class LogModel(BaseDB):
    __tablename__ = 'log'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    message = Column(String)
    level = Column(Integer)
    date = Column(DateTime(timezone=True), default=datetime.datetime.now)
    unread = Column(Boolean, default=True)

    def to_json(self):
        r = dict()
        r['date'] = self.date.isoformat()
        r['message'] = self.message
        r['level'] = self.level
        r['title'] = self.title
        return r

    def __repr__(self):
        return "%s %s %s %s " % (self.date.isoformat(), log_level[self.level], self.title, self.message)

class Log(object):
    def log(self, title, message, level):
        l = LogModel(title=title, message=message, level=level)
        db_session.add(l)
        db_session.commit()

    def log_debug(self, title, message):
        self.log(title, message, 4)

    def log_info(self, title, message):
        self.log(title, message, 3)

    def log_warning(self, title, message):
        self.log(title, message, 2)

    def log_error(self, title, message):
        self.log(title, message, 1)

    def log_critical(self, title, message):
        self.log(title, message, 0)

    def get_log(self, date=None, limit=None, unread=False):

        f = LogModel.query
        # if date:
        #     f = LogModel.query.filter(LogModel.date > date)

        f = f.order_by(LogModel.date.desc())

        if limit:
            f = f.limit(limit)

        return f.all()

log = Log()


class Event(object):
    def get_event(self, date=None, limit=None):
        """ Get all events
        Args:
            date(datetime): Latest date of event
            limit(int): Limit return record number
        Returns:
        """
        return log.get_log(date, limit)

    def send_event(self, msg="Hello"):
        """ Send event
        Args:
            msg(str): message to send
        """
        log.log_info(get_session().username, msg)