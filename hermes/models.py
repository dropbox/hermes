from __future__ import unicode_literals, division

from datetime import datetime
import functools
import logging
import textwrap

from sqlalchemy import create_engine, or_, union_all, desc, and_
from sqlalchemy.event import listen
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, object_session, aliased, validates
from sqlalchemy.orm import synonym, sessionmaker, Session as _Session, backref
from sqlalchemy.orm import subqueryload
from sqlalchemy.schema import Column, ForeignKey, Index, UniqueConstraint
from sqlalchemy.types import Integer, String, Boolean, BigInteger
from sqlalchemy.types import DateTime

from .util import slack_message, email_message
from .settings import settings
import exc

log = logging.getLogger(__name__)

_HOOKS = []

def register_hook(hook):
    _HOOKS.append(hook)


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
        flush = kwargs.pop("flush", True)
        commit = kwargs.pop("commit", True)
        try:
            for key, value in kwargs.iteritems():
                setattr(self, key, value)

            if flush:
                session.flush()
            if commit:
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
        db_engine = get_db_engine(database, echo=True)
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

    def to_dict(self, base_uri=None, expand=[]):
        """Translate this object into a dict for serialization

        Args:
            base_uri: if included, add an href to this resource
            expand: list of children to expand

        Returns:
            dict representation of this object
        """

        if "eventtypes" in expand:
            expand.remove("eventtypes")

        out = {
            "id": self.id,
            "category": self.category,
            "state": self.state,
            "description": self.description,
        }

        if "fates" in expand:
            out['autoCreates'] = [
                fate.to_dict(base_uri=base_uri, expand=set(expand))
                for fate in self.auto_creates
            ]
            out['autoCompletes'] = [
                fate.to_dict(base_uri=base_uri, expand=set(expand))
                for fate in self.auto_completes
            ]

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
    hostname = Column(String(128), nullable=False, unique=True)

    __table_args__ = (
        Index("host_idx", id, hostname),
    )

    @classmethod
    def create(cls, session, hostname):
        """Create a new Host record

        Args:
            session: active database session
            hostname: the hostname of the Host to create

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
    def create_many(cls, session, hostnames):
        """Create a bunch of Host records

        Args:
            session: active database session
            hostnames: the hostnames of the Hosts to create
        """
        session.execute(Host.__table__.insert(), [
                {"hostname": hostname} for hostname in hostnames
            ])
        session.flush()

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
                    Labor.host_id == self.id,
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

    def to_dict(self, base_uri=None, expand=[]):
        """Translate this object into a dict for serialization

        Args:
            base_uri: if included, add an href to this resource
            expand: list of children to expand in the dict

        Returns:
            dict representation of this object
        """

        if "hosts" in expand:
            expand.remove("hosts")

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
        follows: indicates that this Fate only comes into affect if fulfilling
            the Fate with this specified id
        precedes: indicates which Fates are chained to come after this Fate
        description: the optional human readable description of this Fate
        _all_fates: cached list of all Fates
        _intermediate_fates = cached list of all intermediate Fates (Fates that follow other Fates)
        _starting_fates = cached list of all non-intermediate Fates
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

    follows_id = Column(
        Integer, ForeignKey("fates.id"), nullable=True, index=True
    )

    follows = relationship(
        "Fate", lazy="joined", backref="precedes", remote_side=[id]
    )

    description = Column(String(2048), nullable=True)
    __table_args__ = (
        UniqueConstraint(
            creation_type_id, completion_type_id, follows_id,
            name='_creation_completion_uc'
        ),
        Index(
            "fate_idx", id, creation_type_id, completion_type_id, follows_id
        ),
    )

    _all_fates = None
    _intermediate_fates = None
    _starting_fates = None

    @classmethod
    def create(
            cls, session,
            creation_event_type, completion_event_type, follows_id=None,
            description=None
    ):
        """Create a Fate

        Args:
            creation_event_type: an EventType that will trigger
                an labor creation
            completion_event_type: an EventType that will trigger
                an labor completion
            follows_id: id of the Fate this new Fate will follow; None if non-intermediate
            description: optional description for display

        Returns:
            a newly created Fate
        """
        if creation_event_type is None or completion_event_type is None:
            raise exc.ValidationError(
                "Creation EventType and completion EventType are required"
            )

        if follows_id:
            preceding_fate = session.query(Fate).get(follows_id)
            if not preceding_fate:
                raise exc.ValidationError(
                    "Fate cannot follow a non-existent Fate {}".format(follows_id)
                )

            if preceding_fate.completion_event_type != creation_event_type:
                raise exc.ValidationError(
                    "Creation EventType for this Fate and the completion "
                    "EventType for the preceding Fate do not match"
                )

        try:
            obj = cls(
                creation_event_type=creation_event_type,
                completion_event_type=completion_event_type,
                follows_id=follows_id,
                description=description
            )
            obj.add(session)
            session.flush()

            Fate._all_fates = None
            Fate._intermediate_fates = None
            Fate._starting_fates = None

        except Exception:
            session.rollback()
            raise

        return obj

    @classmethod
    def _refresh_cache(cls, session):
        """Helper method to refresh the Fates cache from the database

        Args:
            session: an active database session
        """
        fates = session.query(Fate).all()
        Fate._all_fates = []
        Fate._intermediate_fates = []
        Fate._starting_fates = []
        for fate in fates:
            fate_dict = {
                "id": fate.id,
                "completion_type_id": fate.completion_type_id,
                "creation_type_id": fate.creation_type_id,
                "follows_id": fate.follows_id,
                "precedes_ids": [
                    linked_fate.id for linked_fate in fate.precedes
                ]
            }
            Fate._all_fates.append(fate_dict)
            if fate.follows_id:
                Fate._intermediate_fates.append(fate_dict)
            else:
                Fate._starting_fates.append(fate_dict)

    @classmethod
    def get_all_fates(cls, session):
        """Returns the cached list of all Fates, if available.  Otherwise,
        pull from the database first and then return.

        Args:
            session: an active database connection

        Returns:
            list of all Fates
        """
        if not Fate._all_fates:
            Fate._refresh_cache(session)
        return Fate._all_fates

    @classmethod
    def get_intermediate_fates(cls, session):
        """Returns the cached list of all intermediate Fates, if available.
        Otherwise, pull from the database first and then return.

        Args:
            session: an active database connection

        Returns:
            list of all intermediate Fates
        """
        if not Fate._intermediate_fates:
            Fate._refresh_cache(session)
        return Fate._intermediate_fates

    @classmethod
    def get_starting_fates(cls, session):
        """Returns the cached list of all starting Fates, if available.
        Otherwise, pull from the database first and then return.

        Args:
            session: an active database connection

        Returns:
            list of all starting Fates
        """
        if not Fate._starting_fates:
            Fate._refresh_cache(session)
        return Fate._starting_fates

    @classmethod
    def question_the_fates(cls, session, events, quest=None):
        """Look through the Fates and see if we need to create or close
        Labors based on these Events.

        Note: the expectation here is that if this is a list of Events, they
        are most likely of the same type but for different Hosts, generally
        created enmass as part of a Quest creation. This has some consequences,
        among which is the fact that if the list of Events has an Event that
        should open a Labor and another Event that would close that same Labor,
        this will not work because we only create and commit changes after
        processing all the Events.

        Args:
            session: active database session
            events: the Events for which we need to question the Fates
            quest: the optional quest if event was result of quest creation
            flush: should we flush now or is that done elsewhere?
        """

        # To optimize the database work, we will collect all the work to be
        # done into these lists and then do them all at the end after
        # having processed all events.
        all_new_labors = []
        all_achieved_labors = []

        # Get all the fates, in various categories, for easy reference
        all_fates = Fate.get_all_fates(session)
        starting_fates = Fate.get_starting_fates(session)

        # Query the database for open labors for hosts of which we have an event
        open_labors = (
            session.query(Labor).filter(
                and_(
                    Labor.completion_time == None,
                    Labor.host_id.in_([event.host_id for event in events])
                )
            ).all()
        )

        # Let's sort and file the open labors by the host id
        labors_by_hostid = {}
        for labor in open_labors:
            if labor.host_id in labors_by_hostid:
                labors_by_hostid[labor.host_id].append(labor)
            else:
                labors_by_hostid[labor.host_id] = [labor]

        # Now let's process each of the events and see what we need to do
        for event in events:
            host = event.host
            event_type = event.event_type

            # First, lets see if this Event is supposed to create any
            # non-intermediate Labors and add them to the batch
            for fate in starting_fates:
                if fate["creation_type_id"] == event_type.id:
                    new_labor_dict = {
                        "host_id": host.id,
                        "creation_event_id": event.id,
                        "quest_id": quest.id if quest else None
                    }
                    if new_labor_dict not in all_new_labors:
                        all_new_labors.append(new_labor_dict)

            # Now, let's look at all the Fates that this EventType fulfills
            # and pull them into an array for quicker processing
            relevant_fates = []
            for fate in all_fates:
                if (
                    fate["completion_type_id"] == event_type.id
                ):
                    relevant_fates.append(fate)

            # And with that list of relevant Fates, we can look for
            # open Labors where the Labor's creation EventType matches
            # the Fate's creation EventType.  We will collect the matching
            # Labors into and array for batch achievement
            if host.id in labors_by_hostid:
                for labor in labors_by_hostid[host.id]:
                    for fate in relevant_fates:
                        if (
                            labor.creation_event.event_type.id
                            == fate["creation_type_id"]
                        ):
                            all_achieved_labors.append({
                                "labor": labor,
                                "event": event
                            })

                            # Since this Fate closes this Labor, let's see
                            # if this Fate also precedes other Fates.  If so,
                            # we can make the assumption that a new Labor
                            # should be created
                            if fate["precedes_ids"]:
                                new_labor_dict = {
                                    "host_id": host.id,
                                    "starting_labor_id": (
                                        labor.starting_labor_id
                                        if labor.starting_labor_id
                                        else labor.id
                                    ),
                                    "creation_event_id": event.id,
                                    "quest_id": (
                                        labor.quest.id if labor.quest else None
                                    )
                                }
                                if new_labor_dict not in all_new_labors:
                                    all_new_labors.append(new_labor_dict)

        if all_new_labors:
            Labor.create_many(session, all_new_labors)

        if all_achieved_labors:
            Labor.achieve_many(session, all_achieved_labors)
        session.flush()
        session.commit()

    def href(self, base_uri):
        """Create an HREF value for this object

        Args:
            base_uri: the base URI under which this resource will exist

        Returns:
            URI for this resource
        """
        return "{}/fates/{}".format(base_uri, self.id)

    def to_dict(self, base_uri=None, expand=[]):
        """Translate this object into a dict for serialization

        Args:
            base_uri: if included, add an href to this resource
            expand: list of children to expand

        Returns:
            dict representation of this object
        """

        if "fates" in expand:
            expand.remove("fates")

        out = {
            "id": self.id,
            "creationEventTypeId": self.creation_type_id,
            "completionEventTypeId": self.completion_type_id,
            "follows_id": self.follows_id,
            "precedes_ids": [labor.id for labor in self.precedes],
            "description": self.description,
        }

        if "eventtypes" in expand:
            out['creationEventType'] = self.creation_event_type.to_dict(
                base_uri=base_uri, expand=set(expand)
            )
            out['completionEventType'] = self.completion_event_type.to_dict(
                base_uri=base_uri, expand=set(expand)
            )

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
        tx: an internally used transaction id that is useful for retrieval after bulk creation

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
    tx = Column(BigInteger, nullable=True, index=True)

    __table_args__ = (
        Index("event_idx", id, host_id, event_type_id),
    )

    @classmethod
    def create(
            cls, session,
            host, user, event_type, note=None, quest=None
    ):
        """Log an Event

        Args:
            host: the Host to which this event pertains
            user: the user that created this event, if manually created
            event_type: the EventType of this event
            note: the optional note to be made about this event
            quest: the optional quest if event is result of quest creation

        Returns:
            a newly created Event
        """
        log.debug("Event.create()")

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

        # if we have any hooks defined, call the on_event method on each
        for hook in _HOOKS:
            hook.on_event(event)

        # refer to fates to see if this event should close or open any labors
        Fate.question_the_fates(session, [event], quest=quest)

        return event

    @classmethod
    def create_many(cls, session, events, tx, quest=None):
        """Create multiple Events

        Args:
            session: active database session
            events: the list of Event dicts
            tx: transaction id tied to these bulk creations
            quest: optional if events tied to quests
            flush: indicate if we should flush after we are done
        """
        log.debug("Event.create_many()")

        session.execute(
            Event.__table__.insert(), events
        )

        events = session.query(Event).filter(Event.tx == tx).all()
        log.info("Created {} events".format(len(events)))

        for event in events:
            # if we have any hooks defined, call the on_event method on each
            for hook in _HOOKS:
                hook.on_event(event)

        # refer to fates to see if these events should close or open any labors
        Fate.question_the_fates(session, events, quest=quest)

    def href(self, base_uri):
        """Create an HREF value for this object

        Args:
            base_uri: the base URI under which this resource will exist

        Returns:
            URI for this resource
        """
        return "{}/events/{}".format(base_uri, self.id)

    def to_dict(self, base_uri=None, expand=[]):
        """Translate this object into a dict for serialization

        Args:
            base_uri: if included, add an href to this resource
            expand: list of children to expand in the dict

        Returns:
            dict representation of this object
        """

        if "events" in expand:
            expand.remove("events")

        out = {
            "id": self.id,
            "hostId": self.host_id,
            "timestamp": str(self.timestamp),
            "user": self.user,
            "eventTypeId": self.event_type_id,
            "note": self.note if self.note else "",
        }

        if "host" in expand:
            out['host'] = self.host.to_dict(
                base_uri=base_uri, expand=set(expand)
            )

        if "eventtypes" in expand:
            out['eventType'] = self.event_type.to_dict(
                base_uri=base_uri,
                expand=set(expand)
            )

        if base_uri:
            out['href'] = self.href(base_uri)

        return out


class Quest(Model):
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True)
    embark_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    target_time = Column(DateTime, nullable=True)
    completion_time = Column(DateTime, nullable=True)
    creator = Column(String(64), nullable=False)
    description = Column(String(4096), nullable=False)

    __table_args__ = (
        Index("quest_idx", id, creator),
    )

    @classmethod
    def create(
            cls, session, creator, hosts, creation_event_type, target_time=None,
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
            hosts: a list of Hosts for which to create Events (and Labors)
            creation_event_type: the EventType of which to create Events
            target_time: the optional targeted date and time of Quest completion
            create: if True, Events will be created; if False, reclaim existing Labors
            description: a required human readable text to describe this Quest
        """
        if creator is None:
            raise exc.ValidationError("Quest must have a creator")
        if target_time and target_time <= datetime.utcnow():
            raise exc.ValidationError("Quest target date must be in future")
        if hosts is None:
            raise exc.ValidationError("Quest must have a list of hosts")
        if creation_event_type is None:
            raise exc.ValidationError("Quest must have an EventType")

        try:
            quest = cls(
                creator=creator, description=description,
                target_time=target_time
            )
            quest.add(session)
            session.flush()

        except Exception:
            session.rollback()
            raise

        # if we are supposed to create events, we want to do them as a giant batch
        events_to_create = []
        if create:
            for host in hosts:
                events_to_create.append({
                    "host_id": host.id,
                    "user": creator,
                    "event_type_id": creation_event_type.id,
                    "tx": quest.id
                })
            Event.create_many(session, events_to_create, quest.id, quest=quest)
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
                        and open_labor.host in hosts
                ):
                    open_labor.add_to_quest(quest)

        session.flush()
        session.commit()

        slack_message(
            "*Quest {}* created by {}: "
            "{} hosts started with {} {}\n\t\"{}\"".format(
                quest.id,
                quest.creator,
                len(hosts),
                creation_event_type.category,
                creation_event_type.state,
                quest.description
            )
        )

        msg = "QUEST {} STARTED:\n\n\t\"{}\"\n\n".format(
            quest.id,
            textwrap.fill(
                quest.description,
                width=60, subsequent_indent="\t "
            )
        )

        msg += (
            "There are {} labors in the Quest.  "
            "They were started with the event \"{} {}.\""
        ).format(
            len(quest.labors),
            creation_event_type.category,
            creation_event_type.state,
        )

        email_message(
            quest.creator, "Quest {} started".format(quest.id),
            msg
        )
        return quest

    def check_for_victory(self):
        """Test to see if all the Labors are completed.

        Called when an associated Achievment is completed.
        """
        labors = self.session.query(Labor).filter(
            and_(
                Labor.quest_id == self.id,
                Labor.completion_event_id == None
            )
        ).count()

        if labors == 0:
            self.update(
                completion_time=datetime.utcnow()
            )
            slack_message("*Quest {}* completed:\n\t\"{}\"".format(
                self.id,
                self.description
            ))

            msg = "QUEST {} COMPLETED:\n\n\t\"{}\"\n\n".format(
                self.id,
                textwrap.fill(
                    self.description,
                    width=60, subsequent_indent="\t "
                )
            )

            msg += "Quest was embarked on {} and completed on {}.\n".format(
                self.embark_time, self.completion_time
            )

            msg += "There were {} labors in the Quest.".format(
                len(self.labors)
            )

            email_message(
                self.creator, "Quest {} completed".format(self.id),
                msg
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

    @classmethod
    def email_quest_updates(cls, quests_updated):
        for quest in quests_updated.itervalues():
            msg = "QUEST {} UPDATED:\n\n\t\"{}\"\n\n".format(
                quest["quest"].id,
                textwrap.fill(
                    quest["quest"].description,
                    width=60, subsequent_indent="\t "
                )
            )

            labors_completed = 0;
            remaining_types = {}
            for labor in quest["quest"].labors:
                if labor.completion_time is None:
                    type_key = "{} {}".format(
                        labor.creation_event.event_type.category,
                        labor.creation_event.event_type.state
                    )
                    if type_key in remaining_types:
                        remaining_types[type_key] += 1
                    else:
                        remaining_types[type_key] = 1
                else:
                    labors_completed += 1

            total_labors = len(quest["quest"].labors)
            labors_remaining = total_labors - labors_completed
            if labors_remaining:
                msg += "\nOPEN LABORS BY TYPE:\n"
                for type in remaining_types.iterkeys():
                    msg += "\t{}: {}".format(
                        type,
                        remaining_types[type]
                    )
            msg += (
                "\n\nOVERALL STATUS:\n\t{:.2%} complete.  "
                "{} total labors.  {} remain open.\n\n".format(
                    labors_completed / total_labors,
                    total_labors,
                    labors_remaining
                )
            )

            msg += "LABORS UPDATED:\n"
            for labor in quest["labors"]:
                msg += (
                    "\tLabor {} completed.\n\t\t{}: {} {} => {} {}\n\n".format(
                        labor.id, labor.host.hostname,
                        labor.creation_event.event_type.category,
                        labor.creation_event.event_type.state,
                        labor.completion_event.event_type.category,
                        labor.completion_event.event_type.state,
                    )
                )

            email_message(
                quest["quest"].creator,
                "Quest {} updated".format(quest["quest"].id),
                msg
            )


    def href(self, base_uri):
        """Create an HREF value for this object

        Args:
            base_uri: the base URI under which this resource will exist

        Returns:
            URI for this resource
        """
        return "{}/quests/{}".format(base_uri, self.id)

    def to_dict(self, base_uri=None, expand=[], only_open_labors=False):
        """Translate this object into a dict for serialization

        Args:
            base_uri: if included, add an href to this resource
            expand: children to expand
            only_open_labors: if True, only include open labors in the output

        Returns:
            dict representation of this object
        """

        if "quests" in expand:
            expand.remove("quests")

        out = {
            "id": self.id,
            "embarkTime": str(self.embark_time),
            "completionTime": (
                str(self.completion_time) if self.completion_time else None
            ),
            "creator": self.creator,
            "targetTime": str(self.target_time) if self.target_time else None,
            "description": self.description,
        }

        if only_open_labors:
            labors = self.get_open_labors()
        else:
            labors = self.labors

        if "labors" in expand:
            out['labors'] = [
                labor.to_dict(base_uri=base_uri, expand=set(expand))
                for labor in labors
            ]
        else:
            labors_json = []
            for labor in labors:
                labors_json.append({
                    "id": labor.id,
                    "href": labor.href(base_uri)
                })
            out['labors'] = labors_json

        if base_uri:
            out['href'] = self.href(base_uri)

        return out


class Labor(Model):
    """An Labor is a task that must be completed to satisfy a Quest.

    Attributes:
        id: the unique database id
        starting_labor_id: the database id of the labor that started chain of intermediate labors
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
    starting_labor_id = Column(Integer, nullable=True, index=True)
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
    creation_time = Column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
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
    def create_many(cls, session, labors):
        """Create multiple Labors

        Args:
            session: active database session
            labors: the list of Labors dicts
            tx: transaction id tied to these bulk creations
        """
        session.execute(
            Labor.__table__.insert(), labors
        )
        session.flush()
        slack_message("*Labors:* created {} labor{}".format(
            len(labors),
            "s" if len(labors) > 1 else ""
        ))

    @classmethod
    def achieve_many(cls, session, labor_dicts):
        """Achieve many Labors at once

        Args:
            session: an active database session
            labor_dicts: the list of Labors dicts to achieve
                (with keys labor and event)
        """
        # here we will track the quests that need to get checked for victory
        quests_to_check = []

        # here we will organize the labors into quests so we can send an email
        # of the updated quests
        quests_updated = {}

        # here we will create a giant string of the message to send to Slack
        all_messages = ""

        # Let us examine and update the completion of each labor with the given
        # event, as we were passed in the dict
        for labor_dict in labor_dicts:
            labor = labor_dict["labor"]
            event = labor_dict["event"]
            labor.update(
                completion_event=event, completion_time=datetime.utcnow(),
                flush=False, commit=False
            )

            # add to the message we will post to Slack
            all_messages += (
                "*Labor {}* completed.\n\t{}: {} {} => {} {}{}\n\n".format(
                    labor.id, labor.host.hostname,
                    labor.creation_event.event_type.category,
                    labor.creation_event.event_type.state,
                    labor.completion_event.event_type.category,
                    labor.completion_event.event_type.state,
                    "\n\tPart of Quest [{}] \"{}\"".format(
                        labor.quest_id, labor.quest.description
                    ) if labor.quest_id else ""
                )
            )

            if labor.quest:
                # If this labor was part of a quest, let's sort it into the
                # quests_updated dict so we can more easily generate emails
                if labor.quest_id in quests_updated:
                    quests_updated[labor.quest_id]["labors"].append(labor)
                else:
                    quests_updated[labor.quest_id] = {
                        "quest": labor.quest,
                        "labors": [labor]
                    }
                if labor.quest not in quests_to_check:
                    quests_to_check.append(labor.quest)

        session.flush()
        session.commit()

        if len(labor_dicts) < 10:
            slack_message(all_messages)
        else:
            slack_message(
                "*Labors:* completed {} Labors".format(len(labor_dicts))
            )

        Quest.email_quest_updates(quests_updated)

        for quest in quests_to_check:
            quest.check_for_victory()

    @classmethod
    def get_open_labors(cls, session):
        """Get all open Labors, regardless of acknowledgement

        Returns:
            questo to list of open Labors
        """
        return session.query(Labor).filter(
            Labor.completion_event_id == None
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
        self.update(ack_time=datetime.utcnow(), ack_user=user)

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

    def to_dict(self, base_uri=None, expand=[]):
        """Translate this object into a dict for serialization

        Args:
            base_uri: if included, add an href to this resource
            expand: list of children we want expanded in our dict

        Returns:
            dict representation of this object
        """
        out = {
            "id": self.id,
            "startingLaborId": self.starting_labor_id,
            "questId": self.quest_id,
            "hostId": self.host_id,
            "creationTime": str(self.creation_time),
            "creationEventId": self.creation_event_id,
            "completionTime": (
                str(self.completion_time)
                if self.completion_time else None
            ),
            "completionEventId": self.completion_event_id,
            "ackUser": self.ack_user,
            "ackTime": (
                str(self.ack_time)
                if self.ack_time else None
            )
        }

        if "quests" in expand:
            out['quests'] = [
                self.quest.to_dict(base_uri=base_uri, expand=set(expand))
            ]

        if "hosts" in expand:
            out['host'] = self.host.to_dict(
                base_uri=base_uri, expand=set(expand)
            )

        if "events" in expand:
            out['creationEvent'] = self.creation_event.to_dict(
                base_uri=base_uri, expand=set(expand)
            )
            if self.completion_event:
                out['completionEvent'] = self.completion_event.to_dict(
                    base_uri=base_uri, expand=set(expand)
                )
            else:
                out['completionEvent'] = None

        if self.quest:
            out['targetTime'] = (
                str(self.quest.target_time)
                if self.quest.target_time else None
            )

        if base_uri:
            out['href'] = self.href(base_uri)

        return out


