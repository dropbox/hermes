import pytest

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes.models import Event, EventType, Fate, Host, Labor

from .fixtures import db_engine, session, sample_data1


def test_lifecycle(sample_data1):
    """Test the automatic creation and closing of labors based on Events and Fates"""
    labors = sample_data1.query(Labor).all()
    assert len(labors) == 0

    fate = sample_data1.query(Fate).first()
    host = sample_data1.query(Host).first()
    assert len(host.labors) == 0

    # Create an event which should create a labor
    Event.create(sample_data1, host, "system", fate.creation_event_type)

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host
    assert event.event_type == fate.creation_event_type

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 1
    assert labors[0].completion_time is None
    assert labors[0].completion_event is None
    assert labors[0].creation_event == event
    assert len(host.labors) == 1
    assert len(event.created_labors) == 1
    assert len(event.completed_labors) == 0

    # Create an event which should close that labor
    Event.create(
        sample_data1, host, "system", fate.completion_event_type
    )

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host
    assert event.event_type == fate.completion_event_type

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 1
    assert labors[0].completion_time is not None
    assert labors[0].completion_event == event
    assert len(event.created_labors) == 0
    assert len(event.completed_labors) == 1

    assert len(host.labors) == 1


def test_lifecycle_complex(sample_data1):
    """Test the automatic creation and closing of labors based on Events and Fates.
    This version is a bit more complex in that we make sure unaffiliated labors are left untouched."""
    labors = sample_data1.query(Labor).all()
    assert len(labors) == 0

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

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 2
    assert labors[0].completion_time is None
    assert labors[0].completion_event is None
    assert labors[1].completion_time is None
    assert labors[1].completion_event is None

    Event.create(
        sample_data1, host1, "system", fate1.completion_event_type
    )

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host1
    assert event.event_type == fate1.completion_event_type

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 2
    assert labors[0].completion_time is not None
    assert labors[0].completion_event is not None
    assert labors[1].completion_time is None
    assert labors[1].completion_event is None

    labors = Labor.get_open_labors(sample_data1).all()
    assert len(labors) == 1

    labors = Labor.get_open_unacknowledged(sample_data1)
    assert len(labors) == 1


def test_acknowledge(sample_data1):
    """Test to ensure that acknowledgement correctly flags Labors as such"""

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 0

    fate = sample_data1.query(Fate).get(1)
    host = sample_data1.query(Host).get(1)

    Event.create(sample_data1, host, "system", fate.creation_event_type)

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host
    assert event.event_type == fate.creation_event_type

    labors = Labor.get_open_unacknowledged(sample_data1)
    assert len(labors) == 1
    assert labors[0].completion_time is None
    assert labors[0].completion_event is None
    assert labors[0].ack_time is None
    assert labors[0].ack_user is None
    assert labors[0].creation_event == event

    labors[0].acknowledge("testman")

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 1
    assert labors[0].completion_time is None
    assert labors[0].completion_event is None
    assert labors[0].ack_time is not None
    assert labors[0].ack_user == "testman"
    assert labors[0].creation_event == event

    labors = Labor.get_open_unacknowledged(sample_data1)
    assert len(labors) == 0


def test_cannot_start_in_midworkflow(sample_data1):
    labors = sample_data1.query(Labor).all()
    assert len(labors) == 0

    fate = sample_data1.query(Fate).get(3)
    host = sample_data1.query(Host).get(1)

    Event.create(sample_data1, host, "system", fate.creation_event_type)

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host
    assert event.event_type == fate.creation_event_type

    labors = Labor.get_open_unacknowledged(sample_data1)
    assert len(labors) == 0


