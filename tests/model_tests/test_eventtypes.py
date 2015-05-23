import pytest
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes.models import EventType, Host, Event

from .fixtures import db_engine, session, sample_data1


def test_creation(session):
    EventType.create(session, "foo", "bar", "This is a test")
    session.commit()

    event_types = session.query(EventType).all()

    assert len(event_types) == 1
    assert event_types[0].id == 1
    assert event_types[0].category == "foo"
    assert event_types[0].state == "bar"
    assert event_types[0].description == "This is a test"
    
    event_type = EventType.get_event_type(session, "foo", "bar")
    assert event_type.id == 1
    assert event_type.category == "foo"
    assert event_type.state == "bar"
    assert event_type.description == "This is a test"

    assert event_type.href('/test') == '/test/eventtypes/1'


def test_duplicate(session):
    EventType.create(session, "foo", "bar", "This is a test")

    with pytest.raises(IntegrityError):
        EventType.create(session, "foo", "bar", "Desc ignored")

    EventType.create(session, "foo", "bar2", "This is second test")
    EventType.create(session, "foo2", "bar", "This is second test")


def test_required(session):
    EventType.create(session, "foo", "bar", "This is a test")
    EventType.create(session, "foo", "bar2")

    with pytest.raises(exc.ValidationError):
        EventType.create(session, "foo", None)

    with pytest.raises(exc.ValidationError):
        EventType.create(session, None, "bar")


def test_get_latest_events(session):
    event_type1 = EventType.create(session, "foo", "bar", "test type 1")
    event_type2 = EventType.create(session, "foo", "baz", "test type 2")

    host1 = Host.create(session, "server1")
    host2 = Host.create(session, "server2")

    Event.create(session, host1, "testman", event_type1)
    Event.create(session, host1, "testman", event_type2)
    Event.create(session, host2, "testman", event_type1)
    Event.create(session, host1, "testman", event_type1)
    Event.create(session, host1, "testman", event_type2)
    last_type2 = Event.create(session, host2, "testman", event_type2)
    last_type1 = Event.create(session, host2, "testman", event_type1)

    events1 = event_type1.get_latest_events().all()
    events2 = event_type2.get_latest_events().all()

    assert len(events1) == 4
    assert len(events2) == 3

    assert events1[0] == last_type1
    assert events2[0] == last_type2


def test_get_associated_fates(sample_data1):
    event_type3 = sample_data1.query(EventType).get(3)
    event_type4 = sample_data1.query(EventType).get(4)

    fates_with_et3 = event_type3.get_associated_fates().all()
    fates_with_et4 = event_type4.get_associated_fates().all()

    assert len(fates_with_et3) == 1
    assert len(fates_with_et4) == 2

    assert fates_with_et3[0].description == 'A system that needs maintenance made ready before maintenance can occur.'
    assert fates_with_et4[0].description == 'Maintenance must be performed on a system that is prepped.'
    assert fates_with_et4[1].description == 'A system that needs maintenance made ready before maintenance can occur.'

