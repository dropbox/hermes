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
from sqlalchemy.types import Integer, String, Boolean
from sqlalchemy.types import DateTime

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

        return self

    def add(self, session):
        session._add(self)
        return self

    def before_delete(self):
        """ Hook for extra model cleanup before delete. """

    def after_delete(self):
        """ Hook for extra model cleanup after delete. """

    def delete(self):
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
        Index("event_type_idx", id, category, state)
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

    def get_latest_events(self):
        """Get Events associated with this EventType

        Returns:
            query for getting associated Events
        """
        return (
            self.session.query(Event).filter(
                Event.event_type == self
            ).order_by(desc(Event.timestamp))
        )

    def get_associated_fates(self):
        """Get Fates associated with this EventType

        Returns:
            query for the associated Fates
        """
        return (
            self.session.query(Fate).filter(
                or_(
                    Fate.creation_event_type == self,
                    Fate.completion_event_type == self,
                )
            )
        )

    def href(self, base_uri):
        """Create an HREF value for this object

        Args:
            base_uri: the base URI under which this resource will exist

        Returns:
            URI for this resource
        """
        return "{}/eventtypes/{}".format(base_uri, self.id)

    def to_dict(self, base_uri=None):
        """Translate this object into a dict for serialization

        Args:
            base_uri: if included, add an href to this resource

        Returns:
            dict representation of this object
        """
        out = {
            "id": self.id,
            "category": self.category,
            "state": self.state,
            "description": self.description,
        }

        if base_uri:
            out['href'] = self.href(base_uri)

        return out


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

    __table_args__ = (
        Index("host_idx", id, hostname),
    )

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

    def get_latest_events(self):
        """Get the latest Events for this Host

        Returns:
            query for list of Events
        """
        return (
            self.session.query(Event).filter(Event.host == self)
            .order_by(desc(Event.timestamp))
        )

    def get_labors(self):
        """Get all the labors for this Host

        Returns:
            quest to the labors of this Host
        """
        return (
            self.session.query(Labor).filter(Labor.host == self)
            .order_by(desc(Labor.creation_time))
        )

    def get_open_labors(self):
        """Get the open Labors for this Host

        Returns:
            quest for list of Labors
        """
        return (
            self.session.query(Labor).filter(
                and_(
                    Labor.host == self,
                    Labor.completion_time == None
                ))
            .order_by(desc(Labor.creation_time))
        )

    def href(self, base_uri):
        """Create an HREF value for this object

        Args:
            base_uri: the base URI under which this resource will exist

        Returns:
            URI for this resource
        """
        return "{}/hosts/{}".format(base_uri, self.hostname)

    def to_dict(self, base_uri=None):
        """Translate this object into a dict for serialization

        Args:
            base_uri: if included, add an href to this resource

        Returns:
            dict representation of this object
        """
        out = {
            "id": self.id,
            "hostname": self.hostname,
        }

        if base_uri:
            out['href'] = self.href(base_uri)

        return out


class Fate(Model):
    """A Fate is a mapping of EventTypes to inform the system what kind of Events
    automatically create or satisfy Labors.

    Attributes:
        id: the unique database id
        creation_type: the EventType that creates an Labor based on this Fate
        completion_type: the EventType that closes an Labor created by this
            Fate
        intermediate: if True, this Fate only creates a Labor if also
            closing a previous Labor
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
    intermediate = Column(
        Boolean, nullable=False, default=False
    )
    description = Column(String(2048), nullable=True)
    __table_args__ = (
        UniqueConstraint(
            creation_type_id, completion_type_id,
            name='_creation_completion_uc'
        ),
        Index("fate_idx", id, creation_type_id, completion_type_id),
    )

    @classmethod
    def create(
            cls, session,
            creation_event_type, completion_event_type, intermediate=False,
            description=None
    ):
        """Create a Fate

        Args:
            creation_event_type: an EventType that will trigger
                an labor creation
            completion_event_type: an EventType that will trigger
                an labor completion
            intermediate: if True, this is a mid-workflow Fate
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
                intermediate=intermediate,
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
        Labors based on this event.

        Args:
            session: active database session
            event: the Event for which we need to question the Fates
        """
        host = event.host
        event_type = event.event_type

        print "********* {}  {}".format(host.hostname, event_type.description)

        fates = session.query(Fate).all()

        # we need to track created labors in case we need to tie to a
        # quest because this event both closes and creates an labor
        should_create = False
        should_create_if_intermediate = False
        should_close = False
        labors_to_close = []

        # Examine all the Fates.
        for fate in fates:
            # If this type of Event is a creation type for a Fate,
            # flag that we need to create labors.  We also need to track if
            # this is a creation type for an intermediate fate or not.
            if event_type == fate.creation_event_type:
                if fate.intermediate:
                    should_create_if_intermediate = True
                else:
                    should_create = True

            # If this type of Event is a completion type for a Fate,
            # flag that we need to look for open labors to close
            # for this Host.  Add those to a list in case we need to morph this
            # labor because this is also a creation type event
            if event_type == fate.completion_event_type:
                for open_labor in host.get_open_labors().all():
                    if (
                        open_labor.creation_event.event_type
                            == fate.creation_event_type
                    ):
                        labors_to_close.append(open_labor)
                        should_close = True

        # If we need to create a labor because of a non-intermediate fate,
        # create that now
        if should_create:
            new_labor = Labor.create(session, host, event)

        # If we need to close some labors, lets do that now
        if should_close:
            # We will examine each labor that needs to get closed.  If we are
            # also supposed to create a labor because of an intermediate fate,
            # we will do that now and tie the new labor to the quest of the
            # labor we are closing, if it exists
            for labor in labors_to_close:
                if should_create_if_intermediate:
                    new_labor = Labor.create(session, host, event)
                    if labor.quest:
                        new_labor.add_to_quest(labor.quest)
                labor.achieve(event)

    def href(self, base_uri):
        """Create an HREF value for this object

        Args:
            base_uri: the base URI under which this resource will exist

        Returns:
            URI for this resource
        """
        return "{}/fates/{}".format(base_uri, self.id)

    def to_dict(self, base_uri=None):
        """Translate this object into a dict for serialization

        Args:
            base_uri: if included, add an href to this resource

        Returns:
            dict representation of this object
        """
        out = {
            "id": self.id,
            "intermediate": True if self.intermediate else False,
            "creationEventTypeId": self.creation_type_id,
            "completionEventTypeId": self.completion_type_id,
            "description": self.description,
        }

        if base_uri:
            out['href'] = self.href(base_uri)

        return out


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

    __table_args__ = (
        Index("event_idx", id, host_id, event_type_id),
    )

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

    def href(self, base_uri):
        """Create an HREF value for this object

        Args:
            base_uri: the base URI under which this resource will exist

        Returns:
            URI for this resource
        """
        return "{}/events/{}".format(base_uri, self.id)

    def to_dict(self, base_uri=None):
        """Translate this object into a dict for serialization

        Args:
            base_uri: if included, add an href to this resource

        Returns:
            dict representation of this object
        """
        out = {
            "id": self.id,
            "hostId": self.host_id,
            "timestamp": str(self.timestamp),
            "user": self.user,
            "eventTypeId": self.event_type_id,
            "note": self.note if self.note else "",
        }

        if base_uri:
            out['href'] = self.href(base_uri)

        return out


class Quest(Model):
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True)
    embark_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    completion_time = Column(DateTime, nullable=True)
    creator = Column(String(64), nullable=False)
    description = Column(String(4096), nullable=False)

    __table_args__ = (
        Index("quest_idx", id, creator),
    )

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
        Labors to this Quest.  If create is False, we will look for
        existing open Labors for the Hosts that have a Event of EventType
        and claim them for this Quest.

        Args:
            session: an active database session
            creator: the person or system creating the Quest
            hosts: a list of hosts for which to create Events (and Labors)
            creation_event_type: the EventType of which to create Events
            create: if True, Events will be created; if False, reclaim existing Labors
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
            print session
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
                created_labors = (
                    session.query(Labor)
                    .filter(Labor.creation_event == created_event).all()
                )
                for labor in created_labors:
                    labor.add_to_quest(quest)
        else:
            open_labors = (
                session.query(Labor).filter(
                    Labor.completion_event == None
                ).all()
            )

            for open_labor in open_labors:
                if (
                    open_labor.creation_event.event_type
                        == creation_event_type
                        and open_labor.host in found_hosts
                ):
                    open_labor.add_to_quest(quest)

        return quest

    def check_for_victory(self):
        """Test to see if all the Labors are completed.

        Called when an associated Achievment is completed.
        """
        complete = True
        for labor in self.labors:
            if labor.completion_time is None:
                complete = False

        if complete:
            self.update(
                completion_time=datetime.now()
            )

    @classmethod
    def get_open_quests(cls, session):
        """Get a list of open Quests

        Args:
            session: an open database session

        Returns:
            quest to list of Quests that are open
        """
        return (
            session.query(Quest).filter(Quest.completion_time == None)
            .order_by(desc(Quest.embark_time))
            .from_self().order_by(Quest.embark_time)
        )

    def get_open_labors(self):
        """Get the open labors associated with this quest

        Returns:
            list of open labors
        """
        return (
            self.session.query(Labor).filter(
                and_(
                    Labor.quest == self,
                    Labor.completion_time == None
                )
            )
        )

    def href(self, base_uri):
        """Create an HREF value for this object

        Args:
            base_uri: the base URI under which this resource will exist

        Returns:
            URI for this resource
        """
        return "{}/quests/{}".format(base_uri, self.id)

    def to_dict(self, base_uri=None):
        """Translate this object into a dict for serialization

        Args:
            base_uri: if included, add an href to this resource

        Returns:
            dict representation of this object
        """
        out = {
            "id": self.id,
            "embarkTime": str(self.embark_time),
            "completionTime": str(self.completion_time),
            "creator": self.creator,
            "description": self.description,
        }

        if base_uri:
            out['href'] = self.href(base_uri)

        return out


class Labor(Model):
    """An Labor is a task that must be completed to satisfy a Quest.

    Attributes:
        id: the unique database id
        quest: the Quest to this this Labor belongs
        host: the Host to which this Labor pertains
        creation_time: when this Labor was created
        ack_time: when this Labor was acknowledged
        ack_user: the user who acknowledged the Labor
        creation_event: the Event that triggered a Fate to create this Labor
        completion_event: the Event that triggered a Fate to close this Labor
        complete_time: when this Labor was closed

    Notes:
        the user field is for auditing purposes only.  It is not enforced or
        validated in any way.
    """

    __tablename__ = "labors"

    id = Column(Integer, primary_key=True)
    quest_id = Column(
        Integer, ForeignKey("quests.id"), nullable=True, index=True
    )
    quest = relationship(Quest, lazy="joined", backref="labors")
    host_id = Column(
        Integer, ForeignKey("hosts.id"), nullable=False, index=True
    )
    host = relationship(
        Host, lazy="joined", backref="labors"
    )
    creation_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    ack_time = Column(DateTime, nullable=True)
    ack_user = Column(String(64), nullable=True)
    completion_time = Column(DateTime, nullable=True)
    creation_event_id = Column(
        Integer, ForeignKey("events.id"), nullable=False, index=True
    )
    creation_event = relationship(
        Event, lazy="joined", backref="created_labors",
        foreign_keys=[creation_event_id]
    )
    completion_event_id = Column(
        Integer, ForeignKey("events.id"), nullable=True, index=True
    )
    completion_event = relationship(
        Event, lazy="joined", backref="completed_labors",
        foreign_keys=[completion_event_id]
    )

    __table_args__ = (
        Index(
            "labor_idx", id, quest_id, creation_event_id, completion_event_id
        ),
    )

    @classmethod
    def create(
            cls, session,
            host, creation_event
    ):
        """Create an Labor

        Args:
            host: the host to which this event pertains
            creation_event: the Event that lead to the creation of this labor

        Returns:
            a newly created Labor
        """
        if host is None:
            raise exc.ValidationError(
                "Host cannot be null for an labor"
            )
        if creation_event is None:
            raise exc.ValidationError(
                "Creation Event cannot be null for an labor"
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
    def get_open_labors(cls, session):
        """Get all open Labors, regardless of acknowledgement

        Returns:
            questo to list of open Labors
        """
        return session.query(Labor).filter(
            Labor.completion_event == None
        )

    @classmethod
    def get_open_unacknowledged(cls, session):
        """Get all the open unacknowledged Labors

        Returns:
            the list of open and unacknowledged Labors
        """
        open_labors = session.query(Labor).filter(and_(
            Labor.completion_event == None,
            Labor.ack_time == None
        )).all()

        return open_labors

    def acknowledge(self, user):
        """Mark the Labor as acknowledged by the given user at this time.

        Args:
            user: the arbitrary user name acknowledging this Labor
        """
        self.update(ack_time=datetime.now(), ack_user=user)

    def achieve(self, event):
        """Mark an labor as completed.

        Args:
            event: the event that closed this labor
        """
        self.update(
            completion_event=event, completion_time=datetime.now()
        )

        if self.quest:
            self.quest.check_for_victory()

    def add_to_quest(self, quest):
        """Tie this labor to a particular Quest

        Args:
            quest: the quest that should own this Labor
        """
        self.update(quest=quest)

    def href(self, base_uri):
        """Create an HREF value for this object

        Args:
            base_uri: the base URI under which this resource will exist

        Returns:
            URI for this resource
        """
        return "{}/labors/{}".format(base_uri, self.id)

    def to_dict(self, base_uri=None):
        """Translate this object into a dict for serialization

        Args:
            base_uri: if included, add an href to this resource

        Returns:
            dict representation of this object
        """
        out = {
            "id": self.id,
            "questId": self.quest_id,
            "hostId": self.host_id,
            "creationTime": str(self.creation_time),
            "creationEventId": self.creation_event_id,
            "completionEventId": self.completion_event_id,
            "ackUser": self.ack_user,
            "ackTime": str(self.ack_time)
        }

        if base_uri:
            out['href'] = self.href(base_uri)

        return out


