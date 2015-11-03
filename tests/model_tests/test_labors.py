import pytest

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes.models import Event, EventType, Fate, Host, Labor

from .fixtures import db_engine, session, sample_data1, sample_data2


def test_lifecycle1(sample_data1):
    """Test the automatic creation and closing of labors based on Events and Fates

    Throw event A, and see that it creates Labor A.
    Throw event B, and see that it closes Labor A and creates no new Labors.
    """
    labors = sample_data1.query(Labor).all()
    assert len(labors) == 0

    event_type_a = sample_data1.query(EventType).get(1)
    event_type_b = sample_data1.query(EventType).get(2)
    host = sample_data1.query(Host).first()
    assert len(host.labors) == 0

    # Throw event A
    Event.create(sample_data1, host, "system", event_type_a)

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host
    assert event.event_type == event_type_a

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 1
    assert labors[0].completion_time is None
    assert labors[0].completion_event is None
    assert labors[0].creation_event == event
    assert labors[0].for_creator is False
    assert len(host.labors) == 1
    assert len(event.created_labors) == 1
    assert len(event.completed_labors) == 0

    # Throw event B
    Event.create(
        sample_data1, host, "system", event_type_b
    )

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host
    assert event.event_type == event_type_b

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 1
    assert labors[0].completion_time is not None
    assert labors[0].completion_event == event
    assert labors[0].for_creator is False
    assert len(event.created_labors) == 0
    assert len(event.completed_labors) == 1

    assert len(host.labors) == 1


def test_lifecycle_simple2(sample_data1):
    """Test another simple lifecycle

    Throw event A, and see that it creates Labor A.
    Throw event D, and see that it closes Labor A and creates no new labors.
    """
    labors = sample_data1.query(Labor).all()
    assert len(labors) == 0

    host = sample_data1.query(Host).first()
    assert len(host.labors) == 0

    event_a = sample_data1.query(EventType).get(1)
    event_d = sample_data1.query(EventType).get(4)

    # Throw event A
    Event.create(sample_data1, host, "system", event_a)

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host
    assert event.event_type == event_a

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 1
    assert labors[0].completion_time is None
    assert labors[0].completion_event is None
    assert labors[0].creation_event == event
    assert labors[0].for_creator is False
    assert len(host.labors) == 1
    assert len(event.created_labors) == 1
    assert len(event.completed_labors) == 0


    # Throw event D
    Event.create(
        sample_data1, host, "system", event_d
    )

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host
    assert event.event_type == event_d

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 1
    assert labors[0].completion_time is not None
    assert labors[0].completion_event == event
    assert labors[0].for_creator is False
    assert len(event.created_labors) == 0
    assert len(event.completed_labors) == 1

    assert len(host.labors) == 1


def test_lifecycle_complex2(sample_data1):
    """Test the automatic creation and closing of labors based on Events and Fates.
    This version is a bit more complex in that we make sure unaffiliated labors
    are left untouched.

    Throw event A, creates Labor A.
    Throw event C, creates Labor C.
    Throw event B, closes Labor A, but does nothing to Labor C.
    """
    labors = sample_data1.query(Labor).all()
    assert len(labors) == 0

    fates = sample_data1.query(Fate).all()
    fate1 = fates[0]
    fate2 = fates[1]
    fate4 = fates[3]

    hosts = sample_data1.query(Host).all()
    host1 = hosts[0]
    host2 = hosts[1]

    # Throw event A and C
    Event.create(sample_data1, host1, "system", fate1.creation_event_type)
    Event.create(sample_data1, host2, "system", fate4.creation_event_type)

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host2
    assert event.event_type == fate4.creation_event_type

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 2
    assert labors[0].completion_time is None
    assert labors[0].completion_event is None
    assert labors[0].for_creator is False
    assert labors[1].completion_time is None
    assert labors[1].completion_event is None
    assert labors[1].for_creator is False

    # Throw event B
    Event.create(
        sample_data1, host1, "system", fate2.creation_event_type
    )

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host1
    assert event.event_type == fate2.creation_event_type

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 2
    assert labors[0].completion_time is not None
    assert labors[0].completion_event is not None
    assert labors[0].for_creator is False
    assert labors[1].completion_time is None
    assert labors[1].completion_event is None
    assert labors[1].for_creator is False

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
    assert labors[0].for_creator is False

    labors[0].acknowledge("testman")

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 1
    assert labors[0].completion_time is None
    assert labors[0].completion_event is None
    assert labors[0].ack_time is not None
    assert labors[0].ack_user == "testman"
    assert labors[0].creation_event == event
    assert labors[0].for_creator is False

    labors = Labor.get_open_unacknowledged(sample_data1)
    assert len(labors) == 0


def test_cannot_start_in_midworkflow(sample_data1):
    """Ensures that intermediate fates do not create labors when no labor
    exists.

    Given a Fate C -> D, and intermediate Fate D -> E,
    Throw event D and ensure Labor D is not created since Labor C does not exist.

    """

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 0

    event_type_d = sample_data1.query(EventType).get(4)
    host = sample_data1.query(Host).get(1)

    Event.create(sample_data1, host, "system", event_type_d)

    event = (
        sample_data1.query(Event)
        .order_by(desc(Event.id)).first()
    )

    assert event.host == host
    assert event.event_type == event_type_d

    labors = Labor.get_open_unacknowledged(sample_data1)
    assert len(labors) == 0


def test_longer_chain(sample_data2):
    """Test chained labors A->B->C->D"""
    labors = sample_data2.query(Labor).all()
    assert len(labors) == 0

    # system-maintenance audit
    event_type_a = sample_data2.query(EventType).get(1)
    # system-maintenance needed
    event_type_b = sample_data2.query(EventType).get(2)
    # system-maintenance ready
    event_type_c = sample_data2.query(EventType).get(3)
    # system-maintenance completed
    event_type_d = sample_data2.query(EventType).get(4)

    host = sample_data2.query(Host).get(1)

    event_a = Event.create(sample_data2, host, "system", event_type_a)

    # We will aggressively validate the events created only for event A
    event = (
        sample_data2.query(Event)
        .order_by(desc(Event.id)).first()
    )
    assert event == event_a
    assert event.host == host
    assert event.event_type == event_type_a

    labors = Labor.get_open_unacknowledged(sample_data2)
    assert len(labors) == 1
    assert len(host.labors) == 1
    assert labors[0].starting_labor_id is None
    assert labors[0].for_creator is False
    starting_labor_id = labors[0].id

    event_b = Event.create(sample_data2, host, "system", event_type_b)
    labors = Labor.get_open_unacknowledged(sample_data2)
    assert len(labors) == 1
    assert len(host.labors) == 2
    assert labors[0].starting_labor_id == starting_labor_id
    assert labors[0].for_creator is False

    event_c = Event.create(sample_data2, host, "system", event_type_c)
    labors = Labor.get_open_unacknowledged(sample_data2)
    assert len(labors) == 1
    assert len(host.labors) == 3
    assert labors[0].starting_labor_id == starting_labor_id
    assert labors[0].for_creator is True

    # This last event closes the final labor but does not create a new labor
    event_d = Event.create(sample_data2, host, "system", event_type_d)
    labors = Labor.get_open_unacknowledged(sample_data2)
    assert len(labors) == 0
    assert len(host.labors) == 3





