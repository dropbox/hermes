from __future__ import unicode_literals

from datetime import datetime
import functools
import logging

from sqlalchemy import create_engine, or_, union_all, desc
from sqlalchemy.event import listen
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, object_session, aliased, validates
from sqlalchemy.orm import synonym, sessionmaker, Session as _Session, backref
from sqlalchemy.schema import Column, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql import func, label, literal, false
from sqlalchemy.types import Integer, String, Text, Boolean, SmallInteger
from sqlalchemy.types import Enum, DateTime, VARBINARY

from .settings import settings
import exc

log = logging.getLogger(__name__)


class Session(_Session):
    """ Custom session meant to utilize add on the model.

        This Session overrides the add/add_all methods to prevent them
        from being used. This is to for using the add methods on the
        models themselves where overriding is available.
    """

    _add = _Session.add
    _add_all = _Session.add_all
    _delete = _Session.delete

    def add(self, *args, **kwargs):
        raise NotImplementedError("Use add method on models instead.")

    def add_all(self, *args, **kwargs):
        raise NotImplementedError("Use add method on models instead.")

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Use delete method on models instead.")


Session = sessionmaker(class_=Session)


class Model(object):
    """ Custom model mixin with helper methods. """

    def __repr__(self):
        cls_name = self.__class__.__name__
        return u'%s(id=%r)' % (cls_name, self.id)

    @property
    def session(self):
        return object_session(self)

    @classmethod
    def query(cls):
        """Return a Query using session defaults."""
        # The Model.query() method doesn't work on classmethods. We need a
        # scoped_session for that
        from .meta import ScopedSession
        return ScopedSession().query(cls)

    @classmethod
    def get_or_create(cls, session, **kwargs):
        instance = session.query(cls).filter_by(**kwargs).scalar()
        if instance:
            return instance, False

        instance = cls(**kwargs)
        instance.add(session)

        return instance, True

    @property
    def model_name(self):
        obj_name = type(self).__name__
        return obj_name

    @classmethod
    def before_create(cls, session, user_id):
        """ Hook for before object creation."""

    def after_create(self, user_id):
        """ Hook for after object creation."""

    @classmethod
    def create(cls, session, _user_id, **kwargs):
        commit = kwargs.pop("commit", True)
        try:
            cls.before_create(session, _user_id)
            obj = cls(**kwargs).add(session)
            session.flush()
            obj.after_create(_user_id)
            if commit:
                session.commit()
        except Exception:
            session.rollback()
            raise

        return obj

    def update(self, user_id, **kwargs):
        session = self.session
        try:
            for key, value in kwargs.iteritems():
                setattr(self, key, value)

            session.flush()
            session.commit()
        except Exception:
            session.rollback()
            raise

    def add(self, session):
        session._add(self)
        return self

    def before_delete(self):
        """ Hook for extra model cleanup before delete. """

    def after_delete(self):
        """ Hook for extra model cleanup after delete. """

    def delete(self, user_id):
        session = self.session
        try:
            self.before_delete()
            session._delete(self)
            self.after_delete()
            session.commit()
        except Exception:
            session.rollback()
            raise


Model = declarative_base(cls=Model)


# Foreign Keys are ignored by default in SQLite. Don't do that.
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


def get_db_engine(url, echo=False):
    engine = create_engine(url, pool_recycle=300, echo=False)
    Model.metadata.create_all(engine)

    if engine.driver == "pysqlite":
        listen(engine, "connect", _set_sqlite_pragma)

    return engine


def get_db_session(db_engine=None, database=None):
    """
    Return a usable session object.

    If not provided, this will attempt to retrieve the database and db_engine
    from settings. If settings have not been updated from a config, this will
    return ``None``.

    :param db_engine:
        Database engine to use

    :param database:
        URI for database
    """
    if database is None:
        database = settings.database
        if database is None:
            return None
    if db_engine is None:
        db_engine = get_db_engine(database)
    Session.configure(bind=db_engine)
    return Session()


def flush_transaction(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        dryrun = kwargs.pop("dryrun", False)
        try:
            ret = method(self, *args, **kwargs)
            if dryrun:
                self.session.rollback()
            else:
                self.session.flush()
        except Exception:
            log.exception("Transaction Failed. Rolling back.")
            if self.session is not None:
                self.session.rollback()
            raise
        return ret
    return wrapper


class EventType(Model):
    __tablename__ = "event_types"

    id = Column(Integer, primary_key=True)
    category = Column(String(length=64), nullable=False)
    state = Column(String(length=32), nullable=False)
    description = Column(String(length=1024))
    __table_args__ = (
        UniqueConstraint(category, state, name='_category_state_uc'),
    )

    @classmethod
    def create(cls, session, category, state, description=None):
        """Create an EventType

        Args:
            session: the Db session to use
            category: the category name
            state: the state name
            desc: the optional description

        Returns:
            the newly created EventType
        """

        if category is None or state is None:
            raise exc.ValidationError("Category and State are required")

        try:
            obj = cls(category=category, state=state, description=description)
            obj.add(session)
            session.flush()

        except Exception:
            session.rollback()
            raise

        return obj


class Host(Model):
    __tablename__ = "hosts"

    id = Column(Integer, primary_key=True)
    hostname = Column(String(32), nullable=False, unique=True)

    @classmethod
    def create(cls, session, hostname):
        """Create a new host record

        Args:
            hostname

        Returns:
            the newly created Host
        """

        if hostname is None:
            raise exc.ValidationError("Hostname is required")

        try:
            obj = cls(hostname=hostname)
            obj.add(session)
            session.flush()

        except Exception:
            session.rollback()
            raise

        return obj


class Fates(Model):
    __tablename__ = "fates"

    id = Column(Integer, primary_key=True)
    creation_type_id = Column(
        Integer, ForeignKey("event_types.id"), nullable=False, index=True
    )
    creation_event = relationship(
        EventType, lazy="joined", backref="auto_creates",
        foreign_keys=[creation_type_id]
    )
    completion_type_id = Column(
        Integer, ForeignKey("event_types.id"), nullable=False, index=True
    )
    completion_event = relationship(
        EventType, lazy="joined", backref="auto_completes",
        foreign_keys=[completion_type_id]
    )
    description = Column(String(2048), nullable=True)


class Event(Model):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    host_id = Column(
        Integer, ForeignKey("hosts.id"), nullable=False, index=True
    )
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    host = relationship(
        Host, lazy="joined", backref="events", order_by=timestamp
    )
    user = Column(String(length=64), nullable=False)
    event_type_id = Column(
        Integer, ForeignKey("event_types.id"), nullable=False, index=True
    )
    event_type = relationship(EventType, lazy="joined", backref="events")
    note = Column(String(length=1024))


class Achievement(Model):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True)
    host_id = Column(
        Integer, ForeignKey("hosts.id"), nullable=False, index=True
    )
    host = relationship(Host, lazy="joined", backref="achievements")
    creation_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    ack_time = Column(DateTime, default=datetime.utcnow, nullable=True)
    completion_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    creation_event_id = Column(
        Integer, ForeignKey("events.id"), nullable=False, index=True
    )
    creation_event = relationship(
        Event, lazy="joined", backref="created_achievements",
        foreign_keys=[creation_event_id]
    )
    completion_event_id = Column(
        Integer, ForeignKey("events.id"), nullable=True, index=True
    )
    completion_event = relationship(
        Event, lazy="joined", backref="completed_achievements",
        foreign_keys=[completion_event_id]
    )


class Quest(Model):
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True)
    embark_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    completion_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    description = Column(String(4096), nullable=False)
    creator = Column(String(64), nullable=False)



