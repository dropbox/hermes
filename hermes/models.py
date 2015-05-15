from __future__ import unicode_literals

from datetime import datetime
import functools
import logging

from sqlalchemy import create_engine, or_, union_all, desc, and_
from sqlalchemy.event import listen
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, object_session, aliased, validates
from sqlalchemy.orm import synonym, sessionmaker, Session as _Session, backref
from sqlalchemy.orm import subqueryload
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
    def create(cls, session, **kwargs):
        commit = kwargs.pop("commit", True)
        try:
            obj = cls(**kwargs).add(session)
            session.flush()
            if commit:
                session.commit()
        except Exception:
            session.rollback()
            raise

        return obj

    def update(self, **kwargs):
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
    engine = create_engine(url, pool_recycle=300, echo=echo)
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
    """An EventType is a meta type for events.  All events must be of a given
    and previously defined EventType.  The event type of an event is used to
    match events to Fates.

    Attributes:
        id: the unique id
        category: an arbitrary name to define the event type (ex: "system-needsreboot")
        state: a unique state that the above category can be in (ex: "complete")
        description: the optional human readable description of this EventType

    Notes:
        the combination of category and state form a uniqueness constraint

    """
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

    @classmethod
    def get_event_type(cls, session, category, state):
        """Look up an EventType with the given category and state

        Args:
            session: a live database session
            category: the category to match
            state: the state to match

        Returns:
            the matching EventType, or None
        """
        return session.query(EventType).filter(
            and_(
                EventType.category == category,
                EventType.state == state
            )
        ).first()


class Host(Model):
    """A basic declaration of a host, which should map to unique server (real or virtual)

    Attributes:
        id: the unique database id
        hostname: the name of this host

    Note:
        matching on hostname is done in a very rudimentary fashion.  The code makes
        no attempt to check if a domain has been specified so be sure to be consistent
        in usage to avoid duplicates.
    """

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

    @classmethod
    def get_host(cls, session, hostname):
        """Find a host with a given hostname

        Args:
            session: a database session
            hostname: the name to look for
        """
        return session.query(Host).filter(Host.hostname == hostname).first()

    def get_latest_events(self, limit=20):
        """Get the latest Events for this Host

        Args:
            limit: the number of Events to return

        Returns:
            list of Events
        """
        return (
            self.session.query(Event).filter(Event.host == self)
            .order_by(desc(Event.timestamp)).limit(limit)
            .from_self().order_by(Event.timestamp)
        )

    def get_open_achievements(self, limit=20):
        """Get the open Achievements for this Host

        Args:
            limit: the number of Achievements to return

        Returns:
            list of Achievements
        """
        return (
            self.session.query(Achievement).filter(
                and_(
                    Achievement.host == self,
                    Achievement.completion_time == None
                ))
            .order_by(desc(Achievement.creation_time)).limit(limit)
            .from_self().order_by(Achievement.creation_time)
        )


class Fate(Model):
    """A Fate is a mapping of EventTypes to inform the system what kind of Events
    automatically create or satisfy Achievements.

    Attributes:
        id: the unique database id
        creation_type: the EventType that creates an Achievement based on this Fate
        completion_type: the EventType that closes an Achievement created by this Fate
        description: the optional human readable description of this Fate
    """

    __tablename__ = "fates"

    id = Column(Integer, primary_key=True)
    creation_type_id = Column(
        Integer, ForeignKey("event_types.id"), nullable=False, index=True
    )
    creation_event_type = relationship(
        EventType, lazy="joined", backref="auto_creates",
        foreign_keys=[creation_type_id]
    )
    completion_type_id = Column(
        Integer, ForeignKey("event_types.id"), nullable=False, index=True
    )
    completion_event_type = relationship(
        EventType, lazy="joined", backref="auto_completes",
        foreign_keys=[completion_type_id]
    )
    description = Column(String(2048), nullable=True)
    __table_args__ = (
        UniqueConstraint(
            creation_type_id, completion_type_id, name='_creation_completion_uc'
        ),
    )

    @classmethod
    def create(
            cls, session,
            creation_event_type, completion_event_type, description=None
    ):
        """Create a Fate

        Args:
            creation_event_type: an EventType that will trigger
                an achievement creation
            completion_event_type: an EventType that will trigger
                an achievement completion
            description: optional description for display

        Returns:
            a newly created Fate
        """
        if creation_event_type is None or completion_event_type is None:
            raise exc.ValidationError(
                "Creation EventType and completion EventType are required"
            )

        try:
            obj = cls(
                creation_event_type=creation_event_type,
                completion_event_type=completion_event_type,
                description=description
            )
            obj.add(session)
            session.flush()

        except Exception:
            session.rollback()
            raise

        return obj

    @classmethod
    def question_the_fates(cls, session, event):
        """Look through the Fates and see if we need to create or close
        Achievements based on this event.

        Args:
            session: active database session
            event: the Event for which we need to question the Fates
        """
        host = event.host
        event_type = event.event_type

        fates = session.query(Fate).all()

        # Examine all the Fates.
        for fate in fates:
            # If this type of Event is a creation type for a Fate,
            # create an Achievement
            if event_type == fate.creation_event_type:
                Achievement.create(session, host, event)

            # If this type of Event is a completion type for a Fate,
            # find all open Achievements for the related creation type and
            # mark them as complete.
            if event_type == fate.completion_event_type:
                subquery = (
                    session.query(Event.id).filter(
                        Event.event_type == fate.creation_event_type
                    ).subquery()
                )
                open_achievements = (
                    session.query(Achievement).filter(and_(
                        Achievement.completion_event == None,
                        Achievement.host == event.host,
                        Achievement.creation_event_id.in_(subquery)
                    )).all()
                )

                for open_achievement in open_achievements:
                        open_achievement.achieve(event)


class Event(Model):
    """An Event is a single occurrence of an event, such as a system reboot,
    or an operator marking a system as needing a reboot.  Events can be
    system events or human generated.

    Attributes:
        id: the unique database id
        host: the Host to which this event pertains
        user: the user or other arbitrary identifier for the registrar of this event
        event_type: the EventType that informs what this event is
        note: an optional human readable note attached to this Event

    Notes:
        the user field is for auditing purposes only.  It is not enforced or
        validated in any way.
    """

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
    note = Column(String(length=1024), nullable=True)

    @classmethod
    def create(
            cls, session,
            host, user, event_type, note=None
    ):
        """Log an Event

        Args:
            host: the Host to which this event pertains
            user: the user that created this event, if manually created
            event_type: the EventType of this event
            note: the optional note to be made about this event

        Returns:
            a newly created Event
        """
        if host is None:
            raise exc.ValidationError(
                "Host cannot be null for an event"
            )
        if event_type is None:
            raise exc.ValidationError(
                "EventType cannot be null for an event"
            )
        if user is None:
            raise exc.ValidationError(
                "A user name must be specified for an event"
            )

        try:
            event = cls(
                host=host, user=user, event_type=event_type, note=note
            )
            event.add(session)
            session.flush()

        except Exception:
            session.rollback()
            raise

        Fate.question_the_fates(session, event)

        return event


class Quest(Model):
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True)
    embark_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    completion_time = Column(DateTime, nullable=True)
    creator = Column(String(64), nullable=False)
    description = Column(String(4096), nullable=False)

    @classmethod
    def create(
            cls, session, creator, hosts, creation_event_type,
            create=True, description=None
    ):
        """Create a new Quest.

        We will always specify the creator and a list
        of hosts for which this Quest will encompass.  We also specify the
        EventType of the events we will create (or look up).

        If create is True,
        we will create the events of EventType for all Hosts and tie the created
        Achievements to this Quest.  If create is False, we will look for
        existing open Achievements for the Hosts that have a Event of EventType
        and claim them for this Quest.

        Args:
            session: an active database session
            creator: the person or system creating the Quest
            hosts: a list of hosts for which to create Events (and Achievements)
            creation_event_type: the EventType of which to create Events
            create: if True, Events will be created; if False, reclaim existing Achievements
            description: a required human readable text to describe this Quest
        """
        if creator is None:
            raise exc.ValidationError("Quest must have a creator")
        if hosts is None:
            raise exc.ValidationError("Quest must have a list of hosts")
        if creation_event_type is None:
            raise exc.ValidationError("Quest must have an EventType")

        try:
            quest = cls(
                creator=creator, description=description
            )
            quest.add(session)
            session.flush()

        except Exception:
            session.rollback()
            raise

        found_hosts = []
        for host in hosts:
            found_host = (
                session.query(Host).filter(Host.hostname == host).first()
            )
            if found_host is None:
                logging.error("Could not find host %s", host)
            else:
                found_hosts.append(found_host)

        if create:
            for host in found_hosts:
                created_event = Event.create(
                    session, host, creator, creation_event_type
                )
                created_achievements = (
                    session.query(Achievement)
                    .filter(Achievement.creation_event == created_event).all()
                )
                for achievement in created_achievements:
                    achievement.add_to_quest(quest)
        else:
            open_achievements = (
                session.query(Achievement).filter(
                    Achievement.completion_event == None
                ).all()
            )

            for open_achievement in open_achievements:
                if (
                    open_achievement.creation_event.event_type
                        == creation_event_type
                        and open_achievement.host in found_hosts
                ):
                    open_achievement.add_to_quest(quest)

        return quest

    def check_for_victory(self):
        """Test to see if all the Achievements are completed.

        Called when an associated Achievment is completed.
        """
        complete = True
        for achievement in self.achievements:
            if achievement.completion_time is None:
                complete = False

        if complete:
            self.update(
                completion_time = datetime.now()
            )


class Achievement(Model):
    """An Achievement is a task that must be completed to satisfy a Quest.

    Attributes:
        id: the unique database id
        host: the Host to which this Achievement pertains
        creation_time: when this Achievement was created
        ack_time: when this Achievement was acknowledged
        ack_user: the user who acknowledged the Achievement
        creation_event: the Event that triggered a Fate to create this Achievement
        completion_event: the Event that triggered a Fate to close this Achievement
        complete_time: when this Achievement was closed

    Notes:
        the user field is for auditing purposes only.  It is not enforced or
        validated in any way.
    """

    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True)
    quest_id = Column(
        Integer, ForeignKey("quests.id"), nullable=True, index=True
    )
    quest = relationship(Quest, lazy="joined", backref="achievements")
    host_id = Column(
        Integer, ForeignKey("hosts.id"), nullable=False, index=True
    )
    host = relationship(Host, lazy="joined", backref="achievements")
    creation_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    ack_time = Column(DateTime, nullable=True)
    ack_user = Column(String(64), nullable=True)
    completion_time = Column(DateTime, nullable=True)
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

    @classmethod
    def create(
            cls, session,
            host, creation_event
    ):
        """Create an Achievement

        Args:
            host: the host to which this event pertains
            creation_event: the Event that lead to the creation of this achievement

        Returns:
            a newly created Achievement
        """
        if host is None:
            raise exc.ValidationError(
                "Host cannot be null for an achievement"
            )
        if creation_event is None:
            raise exc.ValidationError(
                "Creation Event cannot be null for an achievement"
            )

        try:
            obj = cls(
                host=host, creation_event=creation_event
            )
            obj.add(session)
            session.flush()

        except Exception:
            session.rollback()
            raise

        return obj

    @classmethod
    def get_open_achievements(cls, session):
        """Get all open Achievements, regardless of acknowledgement

        Returns:
            the list of open Achievements
        """
        open_achievements = session.query(Achievement).filter(
            Achievement.completion_event == None
        ).all()

        return open_achievements

    @classmethod
    def get_open_unacknowledged(cls, session):
        """Get all the open unacknowledged Achievements

        Returns:
            the list of open and unacknowledged Achievements
        """
        open_achievements = session.query(Achievement).filter(and_(
            Achievement.completion_event == None,
            Achievement.ack_time == None
        )).all()

        return open_achievements

    def acknowledge(self, user):
        """Mark the Achievement as acknowledged by the given user at this time.

        Args:
            user: the arbitrary user name acknowledging this Achievement
        """
        self.update(ack_time=datetime.now(), ack_user=user)

    def achieve(self, event):
        """Mark an achievement as completed.

        Args:
            event: the event that closed this achievement
        """
        self.update(
            completion_event=event, completion_time=datetime.now()
        )

        if self.quest:
            self.quest.check_for_victory()

    def add_to_quest(self, quest):
        """Tie this achievement to a particular Quest

        Args:
            quest: the quest that should own this Achievement
        """
        self.update(quest=quest)


