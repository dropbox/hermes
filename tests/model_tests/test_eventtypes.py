import pytest
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes import models

from .fixtures import session


def test_creation(session):
    models.EventType.create(session, "foo", "bar", "This is a test")
    session.commit()

    event_types = session.query(models.EventType).all()

    assert len(event_types) == 1
    assert event_types[0].id == 1
    assert event_types[0].category == "foo"
    assert event_types[0].state == "bar"
    assert event_types[0].description == "This is a test"


def test_duplicate(session):
    models.EventType.create(session, "foo", "bar", "This is a test")

    with pytest.raises(IntegrityError):
        models.EventType.create(session, "foo", "bar", "Desc ignored")

    models.EventType.create(session, "foo", "bar2", "This is second test")
    models.EventType.create(session, "foo2", "bar", "This is second test")


def test_required(session):
    models.EventType.create(session, "foo", "bar", "This is a test")
    models.EventType.create(session, "foo", "bar2")

    with pytest.raises(exc.ValidationError):
        models.EventType.create(session, "foo", None)

    with pytest.raises(exc.ValidationError):
        models.EventType.create(session, None, "bar")
