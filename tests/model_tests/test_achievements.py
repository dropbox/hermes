import pytest

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes import models

from .fixtures import db_engine, session, sample_data1


def test_lifecycle(sample_data1):
    """Test the automatic creation and closing of achievements based on Events and Fates"""
    achievements = sample_data1.query(models.Achievement).all()
    assert len(achievements) == 0

    fate = sample_data1.query(models.Fate).first()
    host = sample_data1.query(models.Host).first()

    models.Event.create(sample_data1, host, "system", fate.creation_event_type)

    event = (
        sample_data1.query(models.Event)
        .order_by(desc(models.Event.id)).first()
    )

    assert event.host == host
    assert event.event_type == fate.creation_event_type

    achievements = sample_data1.query(models.Achievement).all()
    assert len(achievements) == 1
    assert achievements[0].completion_time is None
    assert achievements[0].completion_event is None
    assert achievements[0].creation_event == event

    models.Event.create(
        sample_data1, host, "system", fate.completion_event_type
    )

    event = (
        sample_data1.query(models.Event)
        .order_by(desc(models.Event.id)).first()
    )

    assert event.host == host
    assert event.event_type == fate.completion_event_type

    achievements = sample_data1.query(models.Achievement).all()
    assert len(achievements) == 1
    assert achievements[0].completion_time is not None
    assert achievements[0].completion_event == event

def test_lifecycle_complex(sample_data1):
    """Test the automatic creation and closing of achievements based on Events and Fates.
    This version is a bit more complex in that we make sure unaffiliated achievements are left untouched."""
    achievements = sample_data1.query(models.Achievement).all()
    assert len(achievements) == 0

    fates = sample_data1.query(models.Fate).all()
    fate1 = fates[0]
    fate2 = fates[1]

    hosts = sample_data1.query(models.Host).all()
    host1 = hosts[0]
    host2 = hosts[1]

    models.Event.create(sample_data1, host1, "system", fate1.creation_event_type)
    models.Event.create(sample_data1, host2, "system", fate2.creation_event_type)

    event = (
        sample_data1.query(models.Event)
        .order_by(desc(models.Event.id)).first()
    )

    assert event.host == host2
    assert event.event_type == fate2.creation_event_type

    achievements = sample_data1.query(models.Achievement).all()
    assert len(achievements) == 2
    assert achievements[0].completion_time is None
    assert achievements[0].completion_event is None
    assert achievements[1].completion_time is None
    assert achievements[1].completion_event is None

    models.Event.create(
        sample_data1, host1, "system", fate1.completion_event_type
    )

    event = (
        sample_data1.query(models.Event)
        .order_by(desc(models.Event.id)).first()
    )

    assert event.host == host1
    assert event.event_type == fate1.completion_event_type

    achievements = sample_data1.query(models.Achievement).all()
    assert len(achievements) == 2
    assert achievements[0].completion_time is not None
    assert achievements[0].completion_event is not None
    assert achievements[1].completion_time is None
    assert achievements[1].completion_event is None
