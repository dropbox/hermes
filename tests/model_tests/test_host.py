import pytest
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes.models import Host, EventType, Labor, Event

from .fixtures import db_engine, session, sample_data1


def test_creation(session):
    Host.create(session, "abc-123")
    session.commit()

    hosts = session.query(Host).all()

    assert len(hosts) == 1
    assert hosts[0].id == 1
    assert hosts[0].hostname == "abc-123"

    host = Host.get_host(session, "abc-123")
    assert host.id == 1
    assert host.hostname == "abc-123"


def test_duplicate(session):
    Host.create(session, "abc-123")

    with pytest.raises(IntegrityError):
        Host.create(session, "abc-123")

    Host.create(session, "abc-456")


def test_required(session):
    Host.create(session, "abc-123")

    with pytest.raises(exc.ValidationError):
        Host.create(session, None)


def test_get_latest_events(sample_data1):
    host = Host.get_host(sample_data1, "example.dropbox.com")
    assert host.id == 1
    assert host.hostname == "example.dropbox.com"

    events = host.get_latest_events().all()

    assert len(events) == 2
    assert events[0].note == "example.dropbox.com rebooted."


def test_get_labors(sample_data1):
    host = Host.get_host(sample_data1, "example.dropbox.com")
    assert host.id == 1
    assert len(host.labors) == 0

    event_type1 = sample_data1.query(EventType).get(1)
    event_type3 = sample_data1.query(EventType).get(3)
    event_type4 = sample_data1.query(EventType).get(4)

    print "Creating event1"
    Event.create(sample_data1, host, "testman", event_type1)

    print "Creating event2"
    Event.create(sample_data1, host, "testman", event_type3)

    print "Creating event3"
    closing_event = Event.create(sample_data1, host, "testman", event_type4)

    print "Get labor info"
    all_labors = host.get_labors().all()
    open_labors = host.get_open_labors().all()

    assert len(all_labors) == 3
    assert len(host.labors) == 3
    assert len(open_labors) == 1

    assert all_labors[0].completion_time is None
    assert all_labors[0].completion_event is None
    assert all_labors[1].completion_time is not None
    assert all_labors[1].completion_event == closing_event
    assert all_labors[0].creation_event == closing_event


