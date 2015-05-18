import pytest

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes.models import Event, EventType, Fate, Host, Achievement

from .fixtures import db_engine, session, sample_data1


def test_lifecycle(sample_data1):
    """Test the automatic creation and closing of achievements based on Events and Fates"""
    achievements = sample_data1.query(Achievement).all()
    assert len(achievements) == 0

    fate = sample_data1.query(Fate).first()
    host = sample_data1.query(Host).first()
    assert len(host.achievements) == 0

    Event.create(sample_data1, host, "system", fate.creation_event_type)

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host
    assert event.event_type == fate.creation_event_type

    achievements = sample_data1.query(Achievement).all()
    assert len(achievements) == 1
    assert achievements[0].completion_time is None
    assert achievements[0].completion_event is None
    assert achievements[0].creation_event == event
    assert len(host.achievements) == 1
    assert len(event.created_achievements) == 1
    assert len(event.completed_achievements) == 0

    Event.create(
        sample_data1, host, "system", fate.completion_event_type
    )

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host
    assert event.event_type == fate.completion_event_type

    achievements = sample_data1.query(Achievement).all()
    assert len(achievements) == 1
    assert achievements[0].completion_time is not None
    assert achievements[0].completion_event == event
    assert len(event.created_achievements) == 0
    assert len(event.completed_achievements) == 1

    assert len(host.achievements) == 1


def test_lifecycle_complex(sample_data1):
    """Test the automatic creation and closing of achievements based on Events and Fates.
    This version is a bit more complex in that we make sure unaffiliated achievements are left untouched."""
    achievements = sample_data1.query(Achievement).all()
    assert len(achievements) == 0

    fates = sample_data1.query(Fate).all()
    fate1 = fates[0]
    fate2 = fates[1]

    hosts = sample_data1.query(Host).all()
    host1 = hosts[0]
    host2 = hosts[1]

    Event.create(sample_data1, host1, "system", fate1.creation_event_type)
    Event.create(sample_data1, host2, "system", fate2.creation_event_type)

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host2
    assert event.event_type == fate2.creation_event_type

    achievements = sample_data1.query(Achievement).all()
    assert len(achievements) == 2
    assert achievements[0].completion_time is None
    assert achievements[0].completion_event is None
    assert achievements[1].completion_time is None
    assert achievements[1].completion_event is None

    Event.create(
        sample_data1, host1, "system", fate1.completion_event_type
    )

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host1
    assert event.event_type == fate1.completion_event_type

    achievements = sample_data1.query(Achievement).all()
    assert len(achievements) == 2
    assert achievements[0].completion_time is not None
    assert achievements[0].completion_event is not None
    assert achievements[1].completion_time is None
    assert achievements[1].completion_event is None

    achievements = Achievement.get_open_achievements(sample_data1)
    assert len(achievements) == 1

    achievements = Achievement.get_open_unacknowledged(sample_data1)
    assert len(achievements) == 1


def test_acknowledge(sample_data1):
    """Test to ensure that acknowledgement correctly flags Achievements as such"""

    achievements = sample_data1.query(Achievement).all()
    assert len(achievements) == 0

    fate = sample_data1.query(Fate).get(1)
    host = sample_data1.query(Host).get(1)

    Event.create(sample_data1, host, "system", fate.creation_event_type)

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host
    assert event.event_type == fate.creation_event_type

    achievements = Achievement.get_open_unacknowledged(sample_data1)
    assert len(achievements) == 1
    assert achievements[0].completion_time is None
    assert achievements[0].completion_event is None
    assert achievements[0].ack_time is None
    assert achievements[0].ack_user is None
    assert achievements[0].creation_event == event

    achievements[0].acknowledge("testman")

    achievements = sample_data1.query(Achievement).all()
    assert len(achievements) == 1
    assert achievements[0].completion_time is None
    assert achievements[0].completion_event is None
    assert achievements[0].ack_time is not None
    assert achievements[0].ack_user == "testman"
    assert achievements[0].creation_event == event

    achievements = Achievement.get_open_unacknowledged(sample_data1)
    assert len(achievements) == 0



