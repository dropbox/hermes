import pytest
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes import models

from .fixtures import db_engine, session, sample_data1


def test_creation(sample_data1):
    event_types = sample_data1.query(models.EventType).all()
    assert len(event_types) == 7
    event_type1 = event_types[0]
    assert len(event_type1.events) == 1

    hosts = sample_data1.query(models.Host).all()
    assert len(hosts) == 3
    host = hosts[0]
    assert len(host.events) == 2

    models.Event.create(
        sample_data1, host, "testman", event_type1, note="This is a test event"
    )
    sample_data1.commit()

    events = sample_data1.query(models.Event).all()

    # the total number of events should be 3 now.  We care about the new one
    assert len(events) == 3
    event = events[2]
    assert event.id == 3
    assert event.host == host
    assert event.user == "testman"
    assert event.event_type == event_type1
    assert event.note == "This is a test event"

    assert len(host.events) == 3
    assert len(event_type1.events) == 2


def test_duplicate(sample_data1):
    """Test to ensure duplicate events are fine b/c there can be multiple identical events"""
    event_types = sample_data1.query(models.EventType).all()
    assert len(event_types) == 7
    event_type1 = event_types[0]

    hosts = sample_data1.query(models.Host).all()
    assert len(hosts) == 3
    host = hosts[0]

    models.Event.create(
        sample_data1, host, "testman", event_type1, note="This is a test event"
    )
    sample_data1.commit()

    models.Event.create(
        sample_data1, host, "testman", event_type1, note="This is another test event"
    )
    sample_data1.commit()
